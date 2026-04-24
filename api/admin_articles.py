"""Vercel Serverless Function: Admin Draft Article Management (edit / approve / reject)."""
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

ADMIN_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "").strip()
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_LIST_ID = os.environ.get("BREVO_LIST_ID", "3").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main").strip()

TOKEN_TTL = 86400


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


def _fetch_draft(filename):
    """Fetch a draft file from GitHub and return (file_data, article_dict) or raise."""
    file_data = _github_get(f"contents/articles/drafts/{filename}")
    if "error" in file_data:
        return None, None, file_data["error"]
    try:
        raw = base64.b64decode(file_data.get("content", "").replace("\n", "")).decode("utf-8")
        article = json.loads(raw)
    except Exception as e:
        return None, None, str(e)
    return file_data, article, None


def _fetch_published(filename):
    """Fetch a published article file from articles/{filename} (not drafts)."""
    file_data = _github_get(f"contents/articles/{filename}")
    if "error" in file_data:
        return None, None, file_data["error"]
    try:
        raw = base64.b64decode(file_data.get("content", "").replace("\n", "")).decode("utf-8")
        article = json.loads(raw)
    except Exception as e:
        return None, None, str(e)
    return file_data, article, None


def _github_create_file(path, content_bytes, message):
    """Create a new file via GitHub API (no sha needed)."""
    import urllib.request
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


def _mark_topic_open(topic_id):
    """Revert topic status to 'open' when an article gets unpublished."""
    if not topic_id:
        return None
    topics_path = "data/topics_queue.json"
    file_data = _github_get(f"contents/{topics_path}")
    if "error" in file_data:
        return {"error": file_data["error"]}
    try:
        raw = base64.b64decode(file_data.get("content", "").replace("\n", "")).decode("utf-8")
        data = json.loads(raw)
    except Exception as e:
        return {"error": str(e)}

    sha = file_data.get("sha", "")
    topics_list = data.get("topics") if isinstance(data, dict) else data
    if not isinstance(topics_list, list):
        return {"warning": "topics list not found"}

    for t in topics_list:
        if t.get("id") == topic_id:
            t["status"] = "open"
            t.pop("article_slug", None)
            t.pop("done_at", None)
            break
    else:
        return {"warning": f"Topic {topic_id} not found"}

    if isinstance(data, dict):
        data["topics"] = topics_list
    content_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return _github_update_file(
        topics_path, content_bytes, sha,
        f"unpublish: reopen topic {topic_id}",
    )


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.end_headers()

    def _read_body(self):
        """Read and parse JSON request body."""
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}, None
            if length > 1_048_576:  # 1 MB limit
                return None, "Request body too large"
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8")), None
        except Exception as e:
            return None, str(e)

    def do_PUT(self):
        """Update a draft article (edit fields)."""
        cors = _cors_headers(self.headers.get("Origin", ""))
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err}, cors)

        filename = (body.get("filename") or "").strip()
        if not filename or not re.match(r'^[\w\-]+\.json$', filename):
            return self._json(400, {"error": "filename is required and must be a safe .json filename"}, cors)

        file_data, article, err = _fetch_draft(filename)
        if err:
            return self._json(404, {"error": err}, cors)

        # Update provided fields
        if "title" in body:
            article["title"] = body["title"]
        if "teaser" in body:
            if "meta" not in article or not isinstance(article.get("meta"), dict):
                article["meta"] = {}
            article["meta"]["teaser"] = body["teaser"]
        if "html_content" in body:
            article["html_content"] = body["html_content"]
        if "status" in body:
            article["_status"] = body["status"]

        sha = file_data.get("sha", "")
        content_bytes = json.dumps(article, ensure_ascii=False, indent=2).encode("utf-8")
        result = _github_update_file(
            f"articles/drafts/{filename}",
            content_bytes,
            sha,
            f"dashboard: edit draft {filename}",
        )
        if "error" in result:
            return self._json(500, {"error": result["error"]}, cors)
        return self._json(200, {"success": True, "filename": filename}, cors)

    def do_POST(self):
        """Approve a draft (default) OR unpublish a published article (action='unpublish')."""
        cors = _cors_headers(self.headers.get("Origin", ""))
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err}, cors)

        filename = (body.get("filename") or "").strip()
        if not filename or not re.match(r'^[\w\-]+\.json$', filename):
            return self._json(400, {"error": "filename is required and must be a safe .json filename"}, cors)

        action = (body.get("action") or "").strip().lower()
        if action == "unpublish":
            return self._handle_unpublish(filename, cors)

        file_data, article, err = _fetch_draft(filename)
        if err:
            return self._json(404, {"error": err}, cors)

        article["_status"] = "approved"

        # Optional scheduled publish date (YYYY-MM-DD)
        publish_at = (body.get("publish_at") or "").strip()
        if publish_at:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', publish_at):
                return self._json(400, {"error": "publish_at muss im Format YYYY-MM-DD sein"}, cors)
            article["_publish_at"] = publish_at
        else:
            article.pop("_publish_at", None)

        sha = file_data.get("sha", "")
        content_bytes = json.dumps(article, ensure_ascii=False, indent=2).encode("utf-8")
        result = _github_update_file(
            f"articles/drafts/{filename}",
            content_bytes,
            sha,
            f"dashboard: approve draft {filename}" + (f" (publish at {publish_at})" if publish_at else ""),
        )
        if "error" in result:
            return self._json(500, {"error": result["error"]}, cors)
        return self._json(200, {
            "success": True, "filename": filename, "status": "approved",
            "publish_at": publish_at or None,
        }, cors)

    def do_DELETE(self):
        """Reject (delete) a draft article from GitHub."""
        cors = _cors_headers(self.headers.get("Origin", ""))
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err}, cors)

        filename = (body.get("filename") or "").strip()
        if not filename or not re.match(r'^[\w\-]+\.json$', filename):
            return self._json(400, {"error": "filename is required and must be a safe .json filename"}, cors)

        file_data = _github_get(f"contents/articles/drafts/{filename}")
        if "error" in file_data:
            return self._json(404, {"error": file_data["error"]}, cors)

        sha = file_data.get("sha", "")
        result = _github_delete_file(
            f"articles/drafts/{filename}",
            sha,
            f"dashboard: reject draft {filename}",
        )
        if "error" in result:
            return self._json(500, {"error": result["error"]}, cors)
        return self._json(200, {"success": True, "filename": filename, "action": "rejected"}, cors)

    def _handle_unpublish(self, filename, cors):
        """Move a published article articles/{filename} back to articles/drafts/{filename}."""
        file_data, article, err = _fetch_published(filename)
        if err:
            return self._json(404, {"error": f"published article not found: {err}"}, cors)

        topic_id = article.get("_topic_id", "")
        article["_status"] = "pending"

        draft_bytes = json.dumps(article, ensure_ascii=False, indent=2).encode("utf-8")
        existing_draft = _github_get(f"contents/articles/drafts/{filename}")
        if isinstance(existing_draft, dict) and "error" not in existing_draft:
            # Draft with same name already exists — overwrite it
            draft_result = _github_update_file(
                f"articles/drafts/{filename}",
                draft_bytes,
                existing_draft.get("sha", ""),
                f"dashboard: unpublish {filename} (overwrite existing draft)",
            )
        else:
            draft_result = _github_create_file(
                f"articles/drafts/{filename}",
                draft_bytes,
                f"dashboard: unpublish {filename} (restore as draft)",
            )
        if "error" in draft_result:
            return self._json(500, {"error": f"draft restore failed: {draft_result['error']}"}, cors)

        del_result = _github_delete_file(
            f"articles/{filename}",
            file_data.get("sha", ""),
            f"dashboard: unpublish {filename}",
        )
        if "error" in del_result:
            return self._json(500, {"error": f"published deletion failed: {del_result['error']}"}, cors)

        topic_update = _mark_topic_open(topic_id) if topic_id else None

        return self._json(200, {
            "success": True,
            "filename": filename,
            "action": "unpublished",
            "topic_id": topic_id or None,
            "topic_update": topic_update,
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
