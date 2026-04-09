"""Vercel Serverless Function: Admin Draft Article Management (edit / approve / reject)."""
import base64
import hashlib
import hmac
import json
import os
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
    payload = json.dumps({"message": message, "sha": sha}).encode("utf-8")
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


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers().items():
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
        cors = _cors_headers()
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err}, cors)

        filename = (body.get("filename") or "").strip()
        if not filename or not filename.endswith(".json"):
            return self._json(400, {"error": "filename is required and must be a .json file"}, cors)

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
        """Approve a draft article (set _status to 'approved')."""
        cors = _cors_headers()
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err}, cors)

        filename = (body.get("filename") or "").strip()
        if not filename or not filename.endswith(".json"):
            return self._json(400, {"error": "filename is required and must be a .json file"}, cors)

        file_data, article, err = _fetch_draft(filename)
        if err:
            return self._json(404, {"error": err}, cors)

        article["_status"] = "approved"
        sha = file_data.get("sha", "")
        content_bytes = json.dumps(article, ensure_ascii=False, indent=2).encode("utf-8")
        result = _github_update_file(
            f"articles/drafts/{filename}",
            content_bytes,
            sha,
            f"dashboard: approve draft {filename}",
        )
        if "error" in result:
            return self._json(500, {"error": result["error"]}, cors)
        return self._json(200, {"success": True, "filename": filename, "status": "approved"}, cors)

    def do_DELETE(self):
        """Reject (delete) a draft article from GitHub."""
        cors = _cors_headers()
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err}, cors)

        filename = (body.get("filename") or "").strip()
        if not filename or not filename.endswith(".json"):
            return self._json(400, {"error": "filename is required and must be a .json file"}, cors)

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

    def _json(self, status, data, cors):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass
