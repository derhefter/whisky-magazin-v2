"""Vercel Serverless Function: Admin Topics Queue Management."""
import base64
import hashlib
import hmac
import json
import os
import time
import uuid
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
TOPICS_PATH = "contents/data/topics_queue.json"
TOPICS_WRITE_PATH = "data/topics_queue.json"


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


def _load_topics():
    """Load topics_queue.json from GitHub. Returns (topics_list, raw_data, sha, error)."""
    file_data = _github_get(TOPICS_PATH)
    if "error" in file_data:
        return None, None, None, file_data["error"]
    try:
        raw = base64.b64decode(file_data.get("content", "").replace("\n", "")).decode("utf-8")
        data = json.loads(raw)
    except Exception as e:
        return None, None, None, str(e)

    sha = file_data.get("sha", "")
    if isinstance(data, dict):
        topics_list = data.get("topics", data.get("queue", []))
    else:
        topics_list = data
        data = {"topics": topics_list}
    return topics_list, data, sha, None


def _save_topics(data, sha, message):
    """Save topics data back to GitHub."""
    content_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return _github_update_file(TOPICS_WRITE_PATH, content_bytes, sha, message)


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}, None
            if length > 1_048_576:
                return None, "Request body too large"
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8")), None
        except Exception as e:
            return None, str(e)

    def do_GET(self):
        """List all topics."""
        cors = _cors_headers()
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        topics_list, data, sha, err = _load_topics()
        if err:
            return self._json(500, {"error": err}, cors)

        pending = sum(1 for t in topics_list if t.get("status") == "pending")
        in_progress = sum(1 for t in topics_list if t.get("status") == "in_progress")
        done = sum(1 for t in topics_list if t.get("status") == "done")

        return self._json(200, {
            "sha": sha,
            "topics": topics_list,
            "total": len(topics_list),
            "stats": {
                "pending": pending,
                "in_progress": in_progress,
                "done": done,
            },
        }, cors)

    def do_POST(self):
        """Add a new topic. Accepts both German (titel/typ/kategorie/saison/anlass/prioritaet/notizen)
        and English (title/type/category/season/occasion/priority/notes) field names."""
        cors = _cors_headers()
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err}, cors)

        # Accept German and English field names
        title = (body.get("titel") or body.get("title") or "").strip()
        if not title:
            return self._json(400, {"error": "Titel ist erforderlich"}, cors)

        topics_list, data, sha, err = _load_topics()
        if err:
            return self._json(500, {"error": err}, cors)

        prio_raw = body.get("prioritaet") or body.get("priority") or 5
        try:
            priority = int(prio_raw)
        except (ValueError, TypeError):
            priority = 5

        new_topic = {
            "id": str(uuid.uuid4()),
            "title": title,
            "type": body.get("typ") or body.get("type") or "article",
            "category": body.get("kategorie") or body.get("category") or "",
            "season": body.get("saison") or body.get("season") or "",
            "occasion": body.get("anlass") or body.get("occasion") or "",
            "priority": priority,
            "notes": body.get("notizen") or body.get("notes") or "",
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        topics_list.append(new_topic)

        if isinstance(data, dict):
            data["topics"] = topics_list
        else:
            data = {"topics": topics_list}

        result = _save_topics(data, sha, f"dashboard: add topic '{title}'")
        if "error" in result:
            return self._json(500, {"error": result["error"]}, cors)
        return self._json(201, {"success": True, "topic": new_topic}, cors)

    def do_PUT(self):
        """Update an existing topic (status, priority, title, notes, article_slug)."""
        cors = _cors_headers()
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err}, cors)

        topic_id = (body.get("id") or "").strip()
        if not topic_id:
            return self._json(400, {"error": "id is required"}, cors)

        topics_list, data, sha, err = _load_topics()
        if err:
            return self._json(500, {"error": err}, cors)

        # Find the topic
        target = None
        for t in topics_list:
            if t.get("id") == topic_id:
                target = t
                break
        if target is None:
            return self._json(404, {"error": f"Topic {topic_id} not found"}, cors)

        # Update only provided fields
        updatable = ["status", "priority", "title", "notes", "article_slug"]
        for field in updatable:
            if field in body:
                target[field] = body[field]
        target["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        if isinstance(data, dict):
            data["topics"] = topics_list
        else:
            data = {"topics": topics_list}

        result = _save_topics(data, sha, f"dashboard: update topic {topic_id}")
        if "error" in result:
            return self._json(500, {"error": result["error"]}, cors)
        return self._json(200, {"success": True, "topic": target}, cors)

    def do_DELETE(self):
        """Delete a topic by id."""
        cors = _cors_headers()
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err}, cors)

        topic_id = (body.get("id") or "").strip()
        if not topic_id:
            return self._json(400, {"error": "id is required"}, cors)

        topics_list, data, sha, err = _load_topics()
        if err:
            return self._json(500, {"error": err}, cors)

        original_count = len(topics_list)
        topics_list = [t for t in topics_list if t.get("id") != topic_id]
        if len(topics_list) == original_count:
            return self._json(404, {"error": f"Topic {topic_id} not found"}, cors)

        if isinstance(data, dict):
            data["topics"] = topics_list
        else:
            data = {"topics": topics_list}

        result = _save_topics(data, sha, f"dashboard: delete topic {topic_id}")
        if "error" in result:
            return self._json(500, {"error": result["error"]}, cors)
        return self._json(200, {"success": True, "deleted_id": topic_id}, cors)

    def _json(self, status, data, cors):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass
