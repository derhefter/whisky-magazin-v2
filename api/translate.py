"""Vercel Serverless Function: On-demand article translation with server-side caching.

GET /api/translate?slug={slug}&lang={lang}
  - Checks GitHub cache at articles/translations/{lang}/{slug}.json
  - On miss: translates via DeepL API (fallback: Azure Translator)
  - Saves result to GitHub, returns JSON
  - Rate limit: 10 uncached requests per IP per hour
"""
import base64
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main").strip()

DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "").strip()
AZURE_TRANSLATOR_KEY = os.environ.get("AZURE_TRANSLATOR_KEY", "").strip()
AZURE_TRANSLATOR_REGION = os.environ.get("AZURE_TRANSLATOR_REGION", "westeurope").strip()

ALLOWED_ORIGINS = [
    "https://www.whisky-reise.com",
    "https://whisky-reise.com",
    "http://localhost:8000",
]

SUPPORTED_LANGS = {"en", "fr", "nl", "es", "ja"}

_rate_store = defaultdict(list)
RATE_LIMIT_PER_HOUR = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cors_headers(origin=""):
    allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def _is_rate_limited(ip):
    now = time.time()
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < 3600]
    if len(_rate_store[ip]) >= RATE_LIMIT_PER_HOUR:
        return True
    _rate_store[ip].append(now)
    return False


def _gh_get(path):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    req = Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "WhiskyMagazin-Translate",
    })
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        raise


def _gh_put(path, content_bytes, sha, message):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = {"message": message, "content": base64.b64encode(content_bytes).decode(), "branch": GITHUB_BRANCH}
    if sha:
        payload["sha"] = sha
    req = Request(url, data=json.dumps(payload).encode(), headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "WhiskyMagazin-Translate",
    }, method="PUT")
    with urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _read_cached(lang, slug):
    result = _gh_get(f"articles/translations/{lang}/{slug}.json")
    if not result:
        return None, None
    try:
        data = json.loads(base64.b64decode(result["content"]).decode("utf-8"))
        return data, result.get("sha", "")
    except Exception:
        return None, None


def _write_cached(lang, slug, data):
    path = f"articles/translations/{lang}/{slug}.json"
    existing = _gh_get(path)
    sha = existing.get("sha", "") if existing else ""
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    _gh_put(path, content, sha, f"translate: {lang} {slug}")


def _load_article(slug):
    """Find and return article JSON by slug from articles/ directory."""
    listing = _gh_get("articles")
    if not listing or not isinstance(listing, list):
        return None
    target = next(
        (f for f in listing if f["name"].endswith(f"_{slug}.json") or f["name"] == f"{slug}.json"),
        None
    )
    if not target:
        return None
    result = _gh_get(f"articles/{target['name']}")
    if not result:
        return None
    try:
        return json.loads(base64.b64decode(result["content"]).decode("utf-8"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Translation services
# ---------------------------------------------------------------------------

_DEEPL_LANG_MAP = {"en": "EN-GB", "fr": "FR", "nl": "NL", "es": "ES", "ja": "JA"}


def _translate_deepl(texts, target_lang):
    if not DEEPL_API_KEY:
        raise RuntimeError("DEEPL_API_KEY not configured")
    is_free = DEEPL_API_KEY.endswith(":fx")
    host = "api-free.deepl.com" if is_free else "api.deepl.com"
    dl_lang = _DEEPL_LANG_MAP.get(target_lang, target_lang.upper())
    parts = [f"auth_key={quote(DEEPL_API_KEY)}", f"target_lang={dl_lang}", "tag_handling=html", "source_lang=DE"]
    parts += [f"text={quote(t)}" for t in texts]
    payload = "&".join(parts).encode("utf-8")
    req = Request(
        f"https://{host}/v2/translate",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return [t["text"] for t in result["translations"]]


def _translate_azure(texts, target_lang):
    if not AZURE_TRANSLATOR_KEY:
        raise RuntimeError("AZURE_TRANSLATOR_KEY not configured")
    url = f"https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=de&to={target_lang}"
    body = json.dumps([{"text": t} for t in texts]).encode("utf-8")
    req = Request(url, data=body, headers={
        "Ocp-Apim-Subscription-Key": AZURE_TRANSLATOR_KEY,
        "Ocp-Apim-Subscription-Region": AZURE_TRANSLATOR_REGION,
        "Content-Type": "application/json; charset=UTF-8",
    }, method="POST")
    with urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return [r["translations"][0]["text"] for r in result]


def _translate(texts, target_lang):
    """Try DeepL first, fall back to Azure on any DeepL failure if Azure is configured."""
    deepl_err = None
    if DEEPL_API_KEY:
        try:
            return _translate_deepl(texts, target_lang), "deepl"
        except HTTPError as e:
            deepl_err = f"DeepL HTTP {e.code}"
            if not AZURE_TRANSLATOR_KEY:
                raise
        except Exception as e:
            deepl_err = f"DeepL error: {e}"
            if not AZURE_TRANSLATOR_KEY:
                raise
    if AZURE_TRANSLATOR_KEY:
        return _translate_azure(texts, target_lang), "azure"
    raise RuntimeError(deepl_err or "No translation service configured")


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def _send(self, status, body, origin=""):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        for k, v in _cors_headers(origin).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        origin = self.headers.get("Origin", "")
        params = parse_qs(urlparse(self.path).query)
        slug = params.get("slug", [""])[0].strip()
        lang = params.get("lang", [""])[0].strip().lower()

        if not slug or not lang:
            return self._send(400, {"error": "slug and lang are required"}, origin)
        if lang not in SUPPORTED_LANGS:
            return self._send(400, {"error": f"Unsupported language: {lang}"}, origin)

        # Serve from cache without rate limiting
        cached, _ = _read_cached(lang, slug)
        if cached:
            return self._send(200, cached, origin)

        # New translation: apply rate limit
        ip = self.headers.get("X-Forwarded-For", "unknown").split(",")[0].strip()
        if _is_rate_limited(ip):
            return self._send(429, {"error": "Too many requests. Please try again later."}, origin)

        article = _load_article(slug)
        if not article:
            return self._send(404, {"error": f"Article not found: {slug}"}, origin)

        meta = article.get("meta", {})
        fields = [
            article.get("title", ""),
            article.get("html_content", ""),
            meta.get("teaser", article.get("teaser", "")),
            meta.get("meta_description", ""),
        ]

        try:
            translated, service = _translate(fields, lang)
        except Exception as e:
            return self._send(502, {"error": f"Translation failed: {str(e)}"}, origin)

        result = {
            "lang": lang,
            "source_lang": "de",
            "slug": slug,
            "translated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "service": service,
            "title": translated[0],
            "html_content": translated[1],
            "teaser": translated[2],
            "meta_description": translated[3],
        }

        try:
            _write_cached(lang, slug, result)
        except Exception:
            pass

        return self._send(200, result, origin)

    def log_message(self, fmt, *args):
        pass
