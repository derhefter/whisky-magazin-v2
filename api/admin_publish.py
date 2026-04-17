"""Vercel Serverless Function: Admin Publish Cron – publishes the oldest approved draft.

Vercel cron schedule (vercel.json):
  { "path": "/api/admin_publish", "schedule": "0 8 * * 3,6" }
  → Runs every Wednesday and Saturday at 08:00 UTC.
"""
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
CRON_SECRET = os.environ.get("CRON_SECRET", "").strip()
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_LIST_ID = os.environ.get("BREVO_LIST_ID", "3").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main").strip()

TOKEN_TTL = 86400

TOPICS_PATH = "contents/data/topics_queue.json"
TOPICS_WRITE_PATH = "data/topics_queue.json"


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
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-admin-token",
    }


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
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


def _github_update_file(path, content_bytes, sha, message):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = json.dumps({
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "sha": sha,
        "branch": GITHUB_BRANCH,
    }).encode("utf-8")
    req = Request(url, data=payload, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "WhiskyMagazin-Dashboard",
    }, method="PUT")
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": str(e)}


def _github_create_file(path, content_bytes, message):
    """Create a new file in GitHub (no sha needed for creation)."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = json.dumps({
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }).encode("utf-8")
    req = Request(url, data=payload, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "WhiskyMagazin-Dashboard",
    }, method="PUT")
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": str(e)}


def _github_delete_file(path, sha, message):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = json.dumps({"message": message, "sha": sha, "branch": GITHUB_BRANCH}).encode("utf-8")
    req = Request(url, data=payload, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "WhiskyMagazin-Dashboard",
    }, method="DELETE")
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"error": str(e)}


def _mark_topic_done(topic_id, article_slug):
    """Update topics_queue.json to mark a topic as done with article_slug."""
    file_data = _github_get(TOPICS_PATH)
    if "error" in file_data:
        return {"error": file_data["error"]}
    try:
        raw = base64.b64decode(file_data.get("content", "").replace("\n", "")).decode("utf-8")
        data = json.loads(raw)
    except Exception as e:
        return {"error": str(e)}

    sha = file_data.get("sha", "")
    if isinstance(data, dict):
        topics_list = data.get("topics", data.get("queue", []))
    else:
        topics_list = data
        data = {"topics": topics_list}

    updated = False
    for t in topics_list:
        if t.get("id") == topic_id:
            t["status"] = "done"
            t["article_slug"] = article_slug
            t["done_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            updated = True
            break

    if not updated:
        return {"warning": f"Topic {topic_id} not found in queue"}

    if isinstance(data, dict):
        data["topics"] = topics_list
    else:
        data = {"topics": topics_list}

    content_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return _github_update_file(
        TOPICS_WRITE_PATH,
        content_bytes,
        sha,
        f"publish: mark topic {topic_id} done (slug: {article_slug})",
    )


def _run_publish(target_filename=None):
    """Core publish logic: find oldest approved draft (or a specific one) and publish it.

    Args:
        target_filename: If provided, publish this specific file (must be approved).
                         If None, publish the oldest approved draft.
    """
    # 1. List draft directory
    drafts_dir = _github_get("contents/articles/drafts")
    if "error" in drafts_dir:
        return False, f"Could not list drafts: {drafts_dir['error']}", None

    if not isinstance(drafts_dir, list):
        return False, "Unexpected response from GitHub for drafts directory", None

    # 2. Collect all approved drafts with their metadata
    approved = []
    for item in drafts_dir:
        name = item.get("name", "")
        if not name.endswith(".json") or name == ".gitkeep":
            continue
        # If a specific file is requested, skip others
        if target_filename and name != target_filename:
            continue

        file_data = _github_get(f"contents/articles/drafts/{name}")
        if "error" in file_data:
            continue

        try:
            raw = base64.b64decode(file_data.get("content", "").replace("\n", "")).decode("utf-8")
            article = json.loads(raw)
        except Exception:
            continue

        if article.get("_status") != "approved":
            if target_filename:
                return False, f"Draft '{target_filename}' is not approved (status: {article.get('_status', 'unknown')})", None
            continue

        # Respect scheduled publish date: skip if _publish_at is in the future
        publish_at = (article.get("_publish_at") or "").strip()
        if publish_at:
            today = time.strftime("%Y-%m-%d", time.gmtime())
            if publish_at > today:
                if target_filename:
                    return False, f"Draft '{target_filename}' is scheduled for {publish_at} (today: {today})", None
                continue

        approved.append({
            "filename": name,
            "sha": file_data.get("sha", ""),
            "article": article,
            "sort_key": article.get("_generated_at") or article.get("date") or name,
        })

    if not approved:
        msg = f"Draft '{target_filename}' not found" if target_filename else "No approved drafts found"
        return False, msg, None

    # 3. Pick the target or oldest approved draft
    approved.sort(key=lambda d: d["sort_key"])
    candidate = approved[0]
    filename = candidate["filename"]
    sha = candidate["sha"]
    article = candidate["article"]
    topic_id = article.get("_topic_id", "")

    # 4. Strip internal metadata fields
    for field in ("_status", "_generated_at", "_topic_id", "_publish_at"):
        article.pop(field, None)

    # 5. Publish: create file in articles/
    content_bytes = json.dumps(article, ensure_ascii=False, indent=2).encode("utf-8")
    pub_result = _github_create_file(
        f"articles/{filename}",
        content_bytes,
        f"publish: {filename}",
    )
    if "error" in pub_result:
        return False, f"Failed to publish article: {pub_result['error']}", None

    # 6. Delete the draft
    del_result = _github_delete_file(
        f"articles/drafts/{filename}",
        sha,
        f"publish: remove draft {filename}",
    )
    if "error" in del_result:
        # Article was published but draft deletion failed — log the warning but don't fail
        pass

    # 7. If topic_id present, mark topic as done
    topic_update = None
    if topic_id:
        # Derive article slug from filename (strip date prefix and .json)
        slug = filename
        if slug.endswith(".json"):
            slug = slug[:-5]
        # Remove YYYY-MM-DD_ prefix if present
        if len(slug) > 11 and slug[4] == "-" and slug[7] == "-" and slug[10] == "_":
            slug = slug[11:]
        topic_update = _mark_topic_done(topic_id, slug)

    return True, f"Published {filename}", {
        "filename": filename,
        "topic_id": topic_id or None,
        "topic_update": topic_update,
        "draft_deleted": "error" not in (del_result or {}),
    }


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        """Publish endpoint — called by Vercel cron or authenticated admins.

        Auth logic:
        - If x-admin-token is present and valid → allow (manual trigger from dashboard)
        - If Authorization header matches Bearer <CRON_SECRET> → allow (Vercel cron)
        - Otherwise → 401
        """
        cors = _cors_headers(self.headers.get("Origin", ""))

        token = self.headers.get("x-admin-token", "")
        auth_header = self.headers.get("Authorization", "")
        is_cron = (CRON_SECRET
                   and auth_header == f"Bearer {CRON_SECRET}")
        is_authed = _verify_token(token)

        if not is_authed and not is_cron:
            return self._json(401, {"error": "Unauthorized"}, cors)

        # Optional: ?filename=2026-04-12_some-slug.json to publish a specific draft
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        target_filename = (params.get("filename", [None])[0] or "").strip() or None

        try:
            success, message, details = _run_publish(target_filename=target_filename)
        except Exception as e:
            return self._json(500, {"error": str(e)}, cors)

        status = 200 if success else 404
        return self._json(status, {"success": success, "message": message, "details": details}, cors)

    def _json(self, status, data, cors):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass
