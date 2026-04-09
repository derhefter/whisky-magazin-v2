"""Vercel Serverless Function: Admin Dashboard Data API."""
import base64
import hashlib
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

ADMIN_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "").strip()
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_LIST_ID = os.environ.get("BREVO_LIST_ID", "3").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main").strip()

TOKEN_TTL = 86400


def _verify_token(token: str) -> bool:
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
    key = (ADMIN_PASSWORD or "fallback").encode()
    sig = hmac.new(key, ts_str.encode(), hashlib.sha256).hexdigest()
    expected = f"{ts_str}.{sig}"
    return hmac.compare_digest(token, expected)


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-admin-token",
    }


def _github_get(path):
    # Always read from the configured branch so we're never on the wrong default branch
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
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def _get_newsletter_data():
    """Fetch subscriber data from Brevo."""
    headers = {
        "api-key": BREVO_API_KEY,
        "Accept": "application/json",
    }

    # Get list stats
    list_info = {}
    try:
        req = Request(
            f"https://api.brevo.com/v3/contacts/lists/{BREVO_LIST_ID}",
            headers=headers,
        )
        with urlopen(req, timeout=10) as resp:
            list_info = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        list_info = {"error": str(e)}

    # Get recent contacts
    recent_contacts = []
    try:
        req = Request(
            f"https://api.brevo.com/v3/contacts?listId={BREVO_LIST_ID}&limit=20&sort=desc",
            headers=headers,
        )
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            recent_contacts = data.get("contacts", [])
    except Exception as e:
        recent_contacts = []

    total = list_info.get("totalSubscribers", 0) if not list_info.get("error") else 0
    return {
        # JS liest: data.count, data.total, data.total_subscribers
        "count":             total,
        "total":             total,
        "total_subscribers": total,
        # JS liest: data.subscribers, data.abonnenten
        "subscribers":       recent_contacts,
        "abonnenten":        recent_contacts,
        "recent_contacts":   recent_contacts,
        "list_name":         list_info.get("name", ""),
        "list_error":        list_info.get("error", None),
    }


def _get_articles_data():
    """Fetch draft and published articles from GitHub."""
    # --- Drafts ---
    drafts = []
    drafts_dir = _github_get("contents/articles/drafts")
    if isinstance(drafts_dir, list):
        for item in drafts_dir:
            name = item.get("name", "")
            if not name.endswith(".json") or name == ".gitkeep":
                continue
            file_data = _github_get(f"contents/articles/drafts/{name}")
            if "error" in file_data:
                continue
            try:
                raw = base64.b64decode(file_data.get("content", "").replace("\n", "")).decode("utf-8")
                article = json.loads(raw)
            except Exception:
                continue
            meta = article.get("meta", {})
            drafts.append({
                "filename": name,
                "sha": file_data.get("sha", ""),
                "title": article.get("title", ""),
                "category": article.get("category", ""),
                "teaser": meta.get("teaser", ""),
                "status": article.get("_status", "pending"),
                "generated_at": article.get("_generated_at", ""),
                "date": article.get("date", ""),
                "html_content": (article.get("html_content", "") or "")[:500],
            })

    # Sort drafts: oldest first (by generated_at or date)
    drafts.sort(key=lambda d: d.get("generated_at") or d.get("date") or "")

    # --- Published ---
    published = []
    articles_dir = _github_get("contents/articles")
    if isinstance(articles_dir, list):
        for item in articles_dir:
            name = item.get("name", "")
            if item.get("type") != "file" or not name.endswith(".json"):
                continue
            # Parse date from YYYY-MM-DD prefix
            date_str = ""
            if len(name) >= 10 and name[4] == "-" and name[7] == "-":
                date_str = name[:10]
            published.append({
                "filename": name,
                "sha": item.get("sha", ""),
                "date": date_str,
            })

    # Sort by date desc, return last 30
    published.sort(key=lambda p: p.get("date", ""), reverse=True)
    published = published[:30]

    return {
        "drafts": drafts,
        "drafts_count": len(drafts),
        "published": published,
        "published_count": len(published),
    }


def _get_topics_data():
    """Fetch topics queue from GitHub."""
    file_data = _github_get("contents/data/topics_queue.json")
    if "error" in file_data:
        return {"error": file_data["error"]}

    try:
        raw = base64.b64decode(file_data.get("content", "").replace("\n", "")).decode("utf-8")
        topics = json.loads(raw)
    except Exception as e:
        return {"error": str(e)}

    if isinstance(topics, dict):
        topics_list = topics.get("topics", topics.get("queue", []))
    else:
        topics_list = topics

    pending = sum(1 for t in topics_list if t.get("status") == "pending")
    in_progress = sum(1 for t in topics_list if t.get("status") == "in_progress")
    done = sum(1 for t in topics_list if t.get("status") == "done")

    return {
        "sha": file_data.get("sha", ""),
        "topics": topics_list,
        "total": len(topics_list),
        "stats": {
            "pending": pending,
            "in_progress": in_progress,
            "done": done,
        },
    }


def _get_stats_data():
    """Summary — flat structure matching the dashboard JS field names."""
    newsletter = _get_newsletter_data()
    articles   = _get_articles_data()
    topics     = _get_topics_data()

    drafts_list   = articles.get("drafts", []) if isinstance(articles, dict) else []
    topics_stats  = topics.get("stats", {}) if isinstance(topics, dict) else {}

    return {
        # Übersicht-Karten (JS liest: s.subscribers, s.drafts, s.topics_open, s.topics_done)
        "subscribers":  newsletter.get("total_subscribers", 0) if isinstance(newsletter, dict) else 0,
        "drafts":       len(drafts_list),
        "topics_open":  topics_stats.get("pending", 0),
        "topics_done":  topics_stats.get("done", 0),
        # Zusätzliche Details
        "published_count": articles.get("published_count", 0) if isinstance(articles, dict) else 0,
        "topics_in_progress": topics_stats.get("in_progress", 0),
    }


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        cors = _cors_headers()
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        section = params.get("section", ["stats"])[0]

        try:
            if section == "newsletter":
                data = _get_newsletter_data()
            elif section == "articles":
                data = _get_articles_data()
            elif section == "topics":
                data = _get_topics_data()
            elif section == "stats":
                data = _get_stats_data()
            else:
                return self._json(400, {"error": f"Unknown section: {section}"}, cors)

            return self._json(200, data, cors)
        except Exception as e:
            return self._json(500, {"error": str(e)}, cors)

    def _json(self, status, data, cors):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass
