"""Vercel Serverless Function: Generate article draft from a topic using OpenAI."""
import base64
import hashlib
import hmac
import json
import os
import re
import time
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ADMIN_PASSWORD    = os.environ.get("DASHBOARD_PASSWORD", "").strip()
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO       = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
GITHUB_BRANCH     = os.environ.get("GITHUB_BRANCH", "main").strip()
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL      = os.environ.get("OPENAI_MODEL", "gpt-4o").strip()
UNSPLASH_API_KEY  = os.environ.get("UNSPLASH_API_KEY", "").strip()
AMAZON_TAG        = "whiskyreise74-21"
TOKEN_TTL         = 86400


# ── Auth ──────────────────────────────────────────────────────────────────────

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
    return hmac.compare_digest(token, f"{ts_str}.{sig}")


ALLOWED_ORIGINS = [
    "https://www.whisky-reise.com",
    "https://whisky-reise.com",
    "http://localhost:8000",
]


def _cors_headers(origin=""):
    allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-admin-token",
    }


# ── OpenAI ────────────────────────────────────────────────────────────────────

def _call_openai(messages, max_tokens=4000, temperature=0.7):
    if not OPENAI_API_KEY:
        raise Exception("OPENAI_API_KEY nicht gesetzt")
    payload = json.dumps({
        "model": OPENAI_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")
    req = Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise Exception(f"OpenAI {e.code}: {body[:300]}")


# ── GitHub ────────────────────────────────────────────────────────────────────

def _github_put(path, content_bytes, sha_or_none, message):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if sha_or_none:
        payload["sha"] = sha_or_none
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "WhiskyMagazin-Dashboard",
    }, method="PUT")
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"{e.code}: {body[:200]}"}


def _github_get(path):
    sep = "&" if "?" in path else "?"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}{sep}ref={GITHUB_BRANCH}"
    req = Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "WhiskyMagazin-Dashboard",
    })
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {"error": "not_found"}


# ── Unsplash image fetch ─────────────────────────────────────────────────────

# Brand → landschaftliche Suchanfragen für Unsplash
_BRAND_QUERIES = {
    "lagavulin": "lagavulin bay islay coast scotland",
    "laphroaig": "islay south coast rocky shore scotland",
    "ardbeg": "islay dramatic coastline atlantic waves",
    "bowmore": "bowmore village islay harbour scotland",
    "bruichladdich": "islay west coast white buildings atlantic",
    "talisker": "isle of skye coast cliffs carbost bay",
    "macallan": "speyside estate mansion river scotland",
    "glenfiddich": "dufftown speyside valley river scotland",
    "glenlivet": "glenlivet glen river valley green hills",
    "glenfarclas": "speyside ben rinnes mountain heather",
    "springbank": "campbeltown harbour kintyre coast",
    "highland park": "orkney kirkwall harbour cathedral scotland",
    "glenmorangie": "tain ross shire highland coast scotland",
    "dalmore": "cromarty firth highland scotland coast",
    "benromach": "speyside river valley forres scotland",
    "glengoyne": "campsie fells waterfall highland scotland",
    "aberfeldy": "perthshire river tay autumn scotland",
    "oban": "oban harbour bay boats scotland sunset",
}

_TOPIC_QUERIES = {
    "tasting": "whisky glass amber dram dark elegant closeup",
    "verkostung": "whisky glass amber dram closeup bokeh",
    "review": "whisky glass amber dram closeup bokeh",
    "bewertung": "whisky glass amber dram dark elegant",
    "etikett": "whisky bottle label detail elegant dark",
    "geschenk": "whisky bottle gift box elegant dark amber",
    "zubehör": "whisky accessories glass decanter dark wood",
    "gläser": "whisky glasses crystal dark elegant table",
    "winter": "scotland winter snow glen frost mountains",
    "herbst": "autumn trees scotland loch reflection",
    "frühling": "spring heather scotland hills blossom",
    "sommer": "scotland summer loch sun mountains",
    "regen": "scotland rainy day cozy pub interior warm",
    "april": "scotland april spring loch misty morning",
    "cocktail": "cocktail bar evening warm atmosphere",
    "reise": "scotland landscape road highlands misty",
    "roadtrip": "scotland highland road trip single track",
    "destillerie": "distillery copper pot still interior",
    "wandern": "hiking scotland highland trail misty",
    "karte": "scotland map whisky regions illustrated",
}

_CATEGORY_FALLBACK = {
    "whisky": "whisky glass amber dram dark elegant",
    "reise": "scotland landscape road highlands misty",
    "natur": "scotland wilderness nature mountains loch",
    "lifestyle": "cozy evening interior warm atmosphere table",
}


def _build_unsplash_queries(title: str, category: str) -> list:
    """Baut priorisierte Suchanfragen-Liste für Unsplash."""
    title_lower = title.lower()
    queries = []
    # 1. Brand-Name im Titel
    for brand, q in _BRAND_QUERIES.items():
        if brand in title_lower:
            queries.append(q)
            break
    # 2. Themen-Keywords
    for keyword, q in _TOPIC_QUERIES.items():
        if keyword in title_lower and q not in queries:
            queries.append(q)
    # 3. Kategorie-Fallback
    fallback = _CATEGORY_FALLBACK.get(category.lower(), "scotland whisky landscape highland")
    if fallback not in queries:
        queries.append(fallback)
    return queries


def _fetch_unsplash_image(title: str, category: str) -> dict:
    """Holt ein passendes Bild von Unsplash. Gibt Dict mit url/alt/credit oder {} zurück."""
    if not UNSPLASH_API_KEY:
        return {}
    queries = _build_unsplash_queries(title, category)
    from urllib.parse import urlencode
    for query in queries:
        try:
            params = urlencode({
                "query": query,
                "per_page": 10,
                "orientation": "landscape",
                "content_filter": "high",
            })
            req = Request(
                f"https://api.unsplash.com/search/photos?{params}",
                headers={"Authorization": f"Client-ID {UNSPLASH_API_KEY}"},
            )
            with urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                best = sorted(results, key=lambda p: p.get("downloads", 0), reverse=True)[0]
                img_url = (
                    best["urls"]["raw"]
                    + "?w=1200&h=630&fit=crop&crop=entropy&auto=format&q=80"
                )
                photographer = best["user"]["name"]
                photo_link = best["links"]["html"]
                return {
                    "url": img_url,
                    "alt": title,
                    "credit": (
                        f'Foto von <a href="{photo_link}?utm_source=whisky_magazin'
                        f'&utm_medium=referral">{photographer}</a> auf '
                        f'<a href="https://unsplash.com/?utm_source=whisky_magazin'
                        f'&utm_medium=referral">Unsplash</a>'
                    ),
                }
        except Exception:
            continue
    return {}


# ── Article generation ────────────────────────────────────────────────────────

def _make_slug(title):
    """Convert title to URL slug."""
    slug = title.lower()
    # German umlauts
    for a, b in [("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss")]:
        slug = slug.replace(a, b)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:60]


def _generate_article_html(title, category, notes):
    """Call OpenAI to generate the full article HTML."""
    notes_line = f"\nZusätzliche Hinweise: {notes}" if notes else ""
    prompt = f"""Du schreibst für einen deutschen Whisky- und Reiseblog, der von Steffen und Ellas betrieben wird.
Steffen und Ellas sind leidenschaftliche Whisky-Enthusiasten und Schottland-Reisende, die seit Jahren gemeinsam Destillerien besuchen.
Schreibe auf Deutsch, in einem warmen, persönlichen, fachkundigen Ton.
Schreibe in der Wir-Form ("wir haben", "wir empfehlen", "unser Tipp") für persönliche Erfahrungen.
Spreche die Leser mit "du" an.

AUFGABE: Schreibe einen vollständigen Blog-Artikel zum Thema: "{title}"
Kategorie: {category or "Whisky"}{notes_line}

PFLICHT-REGELN:
1. Mindestens 1500 Wörter, maximal 2500 Wörter.
2. Nur HTML-Format: <h2>, <h3>, <p>, <ul>, <li>, <ol>, <strong>, <em>, <blockquote>
3. Kein <h1> am Anfang (wird separat gesetzt).
4. Mindestens 5 <h2>-Zwischenüberschriften.
5. 3–5 Amazon-Affiliate-Links wo sie thematisch passen:
   <a href="https://www.amazon.de/s?k=PRODUKT&tag={AMAZON_TAG}" target="_blank" rel="noopener noreferrer" class="affiliate-link">Linktext</a>
   Ersetze PRODUKT durch den echten Produktnamen (URL-kodiert mit +).
6. Ein persönliches <blockquote> mit Erfahrung oder Tipp von Steffen und Ellas.
7. Ein "Fazit"-Abschnitt am Ende.
8. IMMER korrekte deutsche Umlaute: ä, ö, ü, ß (NIEMALS ae, oe, ue, ss als Ersatz!).
9. Scotch/Japanischer/Deutscher Whisky = ohne 'e'. Irish/American = mit 'e'.
10. Zum Schluss diese Box (NUR Text, keine Links darin):
    <div class="related-box"><h3>Das könnte dich auch interessieren</h3><ul><li>Verwandtes Thema 1</li><li>Verwandtes Thema 2</li><li>Verwandtes Thema 3</li></ul></div>

ANTWORTE NUR MIT DEM HTML-INHALT. Kein erklärender Text davor oder danach."""

    return _call_openai([
        {"role": "system", "content": "Du bist ein professioneller Blog-Autor für Whisky und Schottland-Reisen. Schreibe auf Deutsch mit korrekten Umlauten (ä, ö, ü, ß). Antworte nur mit HTML-Inhalt."},
        {"role": "user", "content": prompt},
    ], max_tokens=4000)


def _generate_meta(title):
    """Call OpenAI to generate SEO meta data."""
    meta_prompt = f"""Erstelle für einen deutschen Whisky-Blog-Artikel mit dem Titel "{title}" folgende SEO-Daten:

1. SEO Meta-Description (max. 155 Zeichen, Deutsch, mit korrekten Umlauten ä/ö/ü/ß)
2. Kurzer Teaser (max. 200 Zeichen, neugierig machend, mit Umlauten)
3. URL-Slug (lowercase, Bindestriche, keine Umlaute, keine Sonderzeichen, max 60 Zeichen)
4. 3–5 Focus-Keywords (kommagetrennt)

Antworte NUR in diesem JSON-Format:
{{"description": "...", "teaser": "...", "slug": "...", "keywords": "..."}}"""

    result = _call_openai([
        {"role": "system", "content": "Du bist ein SEO-Experte. Antworte nur mit validem JSON. Verwende korrekte deutsche Umlaute (ä, ö, ü, ß)."},
        {"role": "user", "content": meta_prompt},
    ], max_tokens=400, temperature=0.3)

    # Strip code fences if present
    result = re.sub(r"^```(?:json)?\s*\n?", "", result)
    result = re.sub(r"\n?```\s*$", "", result)
    try:
        return json.loads(result)
    except Exception:
        slug = _make_slug(title)
        return {"description": title, "teaser": title, "slug": slug, "keywords": ""}


# ── Handler ───────────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.end_headers()

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}, None
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8")), None
        except Exception as e:
            return None, str(e)

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in _cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not _verify_token(self.headers.get("x-admin-token", "")):
            return self._json(401, {"error": "Unauthorized"})

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err})

        title    = (body.get("title") or body.get("titel") or "").strip()
        category = (body.get("category") or body.get("kategorie") or "Whisky").strip()
        notes    = (body.get("notes") or body.get("notizen") or "").strip()

        if not title:
            return self._json(400, {"error": "title ist erforderlich"})

        if not OPENAI_API_KEY:
            return self._json(503, {"error": "OPENAI_API_KEY nicht in Vercel konfiguriert"})

        try:
            # Step 1: Generate article HTML
            html_content = _generate_article_html(title, category, notes)
            if html_content.startswith("```"):
                html_content = re.sub(r"^```(?:html)?\s*\n?", "", html_content)
                html_content = re.sub(r"\n?```\s*$", "", html_content)

            # Step 2: Generate meta data
            meta = _generate_meta(title)
            slug = meta.get("slug") or _make_slug(title)

            # Step 3: Fetch Unsplash image
            image_data = _fetch_unsplash_image(title, category)

            # Step 4: Build article JSON
            today = time.strftime("%Y-%m-%d")
            article = {
                "title":       title,
                "slug":        slug,
                "category":    category,
                "date":        today,
                "image_url":   image_data.get("url", ""),
                "image_alt":   image_data.get("alt", title),
                "image_credit": image_data.get("credit", ""),
                "meta": {
                    "teaser":          meta.get("teaser", ""),
                    "description":     meta.get("description", ""),
                    "meta_description": meta.get("description", ""),
                    "slug":            slug,
                    "keywords":        meta.get("keywords", ""),
                },
                "_status":       "pending",
                "_generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "html_content":  html_content,
            }

            # Step 5: Save to GitHub as draft
            draft_path = f"articles/drafts/{today}_{slug}.json"
            existing   = _github_get(draft_path)
            sha        = existing.get("sha") if "error" not in existing else None
            content_bytes = json.dumps(article, ensure_ascii=False, indent=2).encode("utf-8")
            result = _github_put(draft_path, content_bytes, sha, f"Artikel-Entwurf: {title}")

            if "error" in result:
                return self._json(500, {"error": result["error"]})

            return self._json(200, {
                "ok":    True,
                "slug":  slug,
                "path":  draft_path,
                "title": title,
            })

        except Exception as e:
            return self._json(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        pass
