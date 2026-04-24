"""Vercel Serverless Function: Admin Image Management (Unsplash candidates + selection)."""
import base64
import hashlib
import hmac
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

ADMIN_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "").strip()
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", os.environ.get("UNSPLASH_API_KEY", "")).strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main").strip()

TOKEN_TTL = 86400
IMAGES_DIR = "site-v2/images"


def _verify_token(token: str) -> bool:
    if not ADMIN_PASSWORD:
        return False
    if not token or "." not in token:
        return False
    parts = token.split(".", 1)
    if len(parts) != 2:
        return False
    ts_str, _ = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    if time.time() - ts > TOKEN_TTL:
        return False
    key = ADMIN_PASSWORD.encode()
    sig = hmac.new(key, ts_str.encode(), hashlib.sha256).hexdigest()
    expected = f"{ts_str}.{sig}"
    return hmac.compare_digest(token, expected)


ALLOWED_ORIGINS = [
    "https://www.whisky-reise.com",
    "https://whisky-reise.com",
    "http://localhost:8000",
]


def _cors_headers(origin=""):
    allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-admin-token",
    }


def _safe_slug(text):
    text = (text or "").lower()
    for src, dst in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("&", "-"), ("'", "")]:
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9\-]", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:60]


def _github_get(path):
    if path.startswith("contents/"):
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}ref={GITHUB_BRANCH}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{path}"
    req = Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "WhiskyMagazin-Dashboard",
    })
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": str(e), "status": e.code}
    except Exception as e:
        return {"error": str(e)}


def _github_put_file(path, content_bytes, sha, message):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "WhiskyMagazin-Dashboard",
    }, method="PUT")
    try:
        with urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": str(e)}


def _fetch_draft(filename):
    file_data = _github_get(f"contents/articles/drafts/{filename}")
    if "error" in file_data:
        return None, None, file_data["error"]
    try:
        raw = base64.b64decode(file_data.get("content", "").replace("\n", "")).decode("utf-8")
        article = json.loads(raw)
    except Exception as e:
        return None, None, str(e)
    return file_data, article, None


def _unsplash_search(query, per_page=4):
    if not UNSPLASH_ACCESS_KEY:
        return []
    if not query or not query.strip():
        return []
    params = {
        "query": query.strip(),
        "per_page": str(max(1, min(per_page, 12))),
        "orientation": "landscape",
        "content_filter": "high",
    }
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://api.unsplash.com/search/photos?{qs}"
    req = Request(url, headers={
        "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
        "User-Agent": "WhiskyMagazin-Dashboard",
    })
    try:
        with urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return []
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []

    candidates = []
    for p in data.get("results", []):
        photographer = p.get("user", {}).get("name", "")
        photo_link = p.get("links", {}).get("html", "")
        raw = p.get("urls", {}).get("raw", "")
        if not raw:
            continue
        candidates.append({
            "photo_id": p.get("id", ""),
            "url_full": raw + "?w=1200&h=630&fit=crop&crop=entropy&auto=format&q=80",
            "url_small": raw + "?w=400&h=225&fit=crop&crop=entropy&auto=format&q=70",
            "photographer": photographer,
            "description": p.get("alt_description") or p.get("description") or "",
            "attribution": (
                f'Foto von <a href="{photo_link}?utm_source=whisky_magazin'
                f'&utm_medium=referral">{photographer}</a> auf '
                f'<a href="https://unsplash.com/?utm_source=whisky_magazin'
                f'&utm_medium=referral">Unsplash</a>'
            ),
        })
    return candidates


def _download_image_bytes(url):
    req = Request(url, headers={"User-Agent": "WhiskyMagazin-Dashboard"})
    try:
        with urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                return None
            data = resp.read()
            if len(data) < 5000:
                return None
            return data
    except Exception:
        return None


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        """Return 4 Unsplash candidates for a given query (or default article-based query)."""
        cors = _cors_headers(self.headers.get("Origin", ""))
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        qs = parse_qs(urlparse(self.path).query)
        filename = (qs.get("filename", [""])[0] or "").strip()
        query = (qs.get("query", [""])[0] or "").strip()

        default_query = ""
        if filename:
            if not re.match(r'^[\w\-]+\.json$', filename):
                return self._json(400, {"error": "invalid filename"}, cors)
            _, article, err = _fetch_draft(filename)
            if err:
                return self._json(404, {"error": err}, cors)
            default_query = article.get("title", "")

        search_query = query or default_query
        if not search_query:
            return self._json(400, {"error": "query or filename required"}, cors)

        if not UNSPLASH_ACCESS_KEY:
            return self._json(500, {"error": "UNSPLASH_ACCESS_KEY not configured"}, cors)

        candidates = _unsplash_search(search_query, per_page=4)
        return self._json(200, {
            "query": search_query,
            "default_query": default_query,
            "candidates": candidates,
        }, cors)

    def do_PUT(self):
        """Download the chosen Unsplash image, save to site-v2/images/{slug}.jpg, update draft JSON."""
        cors = _cors_headers(self.headers.get("Origin", ""))
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0 or length > 1_048_576:
                return self._json(400, {"error": "invalid body"}, cors)
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as e:
            return self._json(400, {"error": str(e)}, cors)

        filename = (body.get("filename") or "").strip()
        if not filename or not re.match(r'^[\w\-]+\.json$', filename):
            return self._json(400, {"error": "invalid filename"}, cors)

        url_full = (body.get("url_full") or "").strip()
        if not url_full.startswith("https://"):
            return self._json(400, {"error": "url_full missing"}, cors)

        attribution = body.get("attribution", "")
        photo_id = body.get("photo_id", "")
        alt = (body.get("alt") or "").strip()

        file_data, article, err = _fetch_draft(filename)
        if err:
            return self._json(404, {"error": err}, cors)

        meta_slug = article.get("meta", {}).get("slug", "") if isinstance(article.get("meta"), dict) else ""
        slug = _safe_slug(meta_slug) if meta_slug else _safe_slug(article.get("title", "artikel"))
        if not slug:
            return self._json(500, {"error": "could not derive slug"}, cors)

        img_bytes = _download_image_bytes(url_full)
        if not img_bytes:
            return self._json(502, {"error": "image download failed"}, cors)

        image_path = f"{IMAGES_DIR}/{slug}.jpg"
        existing = _github_get(f"contents/{image_path}")
        existing_sha = existing.get("sha") if isinstance(existing, dict) and "error" not in existing else None

        img_result = _github_put_file(
            image_path,
            img_bytes,
            existing_sha,
            f"dashboard: update image for {slug}",
        )
        if "error" in img_result:
            return self._json(500, {"error": f"image upload: {img_result['error']}"}, cors)

        article["image_url"] = f"/images/{slug}.jpg"
        if alt:
            article["image_alt"] = alt
        elif not article.get("image_alt"):
            article["image_alt"] = article.get("title", "")
        article["image_credit"] = attribution
        article["image_photo_id"] = photo_id
        article["image_source"] = "unsplash"

        draft_bytes = json.dumps(article, ensure_ascii=False, indent=2).encode("utf-8")
        draft_result = _github_put_file(
            f"articles/drafts/{filename}",
            draft_bytes,
            file_data.get("sha", ""),
            f"dashboard: update image for draft {filename}",
        )
        if "error" in draft_result:
            return self._json(500, {"error": f"draft update: {draft_result['error']}"}, cors)

        return self._json(200, {
            "success": True,
            "filename": filename,
            "image_url": article["image_url"],
            "image_alt": article["image_alt"],
            "image_credit": article["image_credit"],
            "image_photo_id": article["image_photo_id"],
        }, cors)

    def _json(self, status, data, cors):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass
