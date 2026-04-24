"""Vercel Serverless Function: Admin Draft Article Management (edit / approve / reject / image)."""
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
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_LIST_ID = os.environ.get("BREVO_LIST_ID", "3").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main").strip()
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", os.environ.get("UNSPLASH_API_KEY", "")).strip()

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
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-admin-token",
    }


def _safe_slug(text):
    text = (text or "").lower()
    for src, dst in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("&", "-"), ("'", "")]:
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9\-]", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:60]


def _unsplash_search(query, per_page=4):
    if not UNSPLASH_ACCESS_KEY or not query or not query.strip():
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
        with urlopen(req, timeout=25) as resp:
            if resp.status != 200:
                return None, f"unsplash status {resp.status}"
            data = resp.read()
            if len(data) < 5000:
                return None, f"payload too small ({len(data)}B)"
            return data, None
    except Exception as e:
        return None, f"download exception: {e}"


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
        with urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        return {"error": f"{e} {body}".strip()}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


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
        with urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        return {"error": f"{e} {body}".strip()}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


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

    def do_GET(self):
        """GET ?action=image_candidates&filename=X[&query=Y] → 4 Unsplash candidates."""
        cors = _cors_headers(self.headers.get("Origin", ""))
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            return self._json(401, {"error": "Unauthorized"}, cors)

        qs = parse_qs(urlparse(self.path).query)
        action = (qs.get("action", [""])[0] or "").strip().lower()
        if action != "image_candidates":
            return self._json(400, {"error": "unknown action"}, cors)

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
        """Update a draft article (edit fields) OR set its image (action='set_image')."""
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
        if action == "set_image":
            return self._handle_set_image(filename, body, cors)

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

    def _handle_set_image(self, filename, body, cors):
        """Download Unsplash image, save to site-v2/images/{slug}.jpg, update draft JSON."""
        url_full = (body.get("url_full") or "").strip()
        if not url_full.startswith("https://"):
            return self._json(400, {"error": "url_full missing"}, cors)
        attribution = body.get("attribution", "")
        photo_id = body.get("photo_id", "")
        alt = (body.get("alt") or "").strip()

        if not GITHUB_TOKEN:
            return self._json(500, {"error": "stage=config: GITHUB_TOKEN missing"}, cors)

        file_data, article, err = _fetch_draft(filename)
        if err:
            return self._json(404, {"error": f"stage=fetch_draft: {err}"}, cors)

        meta_slug = article.get("meta", {}).get("slug", "") if isinstance(article.get("meta"), dict) else ""
        slug = _safe_slug(meta_slug) if meta_slug else _safe_slug(article.get("title", "artikel"))
        if not slug:
            return self._json(500, {"error": "stage=slug: could not derive slug"}, cors)

        img_bytes, dl_err = _download_image_bytes(url_full)
        if not img_bytes:
            return self._json(502, {"error": f"stage=download: {dl_err or 'unknown'}"}, cors)

        image_path = f"{IMAGES_DIR}/{slug}.jpg"
        existing = _github_get(f"contents/{image_path}")
        existing_sha = existing.get("sha") if isinstance(existing, dict) and "error" not in existing else None

        if existing_sha:
            img_result = _github_update_file(image_path, img_bytes, existing_sha,
                                             f"dashboard: update image for {slug}")
        else:
            img_result = _github_create_file(image_path, img_bytes,
                                             f"dashboard: add image for {slug}")
        if "error" in img_result:
            return self._json(500, {
                "error": f"stage=upload_image ({image_path}, {len(img_bytes)}B): {img_result['error']}"
            }, cors)

        article["image_url"] = f"/images/{slug}.jpg"
        if alt:
            article["image_alt"] = alt
        elif not article.get("image_alt"):
            article["image_alt"] = article.get("title", "")
        article["image_credit"] = attribution
        article["image_photo_id"] = photo_id
        article["image_source"] = "unsplash"

        draft_bytes = json.dumps(article, ensure_ascii=False, indent=2).encode("utf-8")
        draft_result = _github_update_file(
            f"articles/drafts/{filename}", draft_bytes, file_data.get("sha", ""),
            f"dashboard: update image for draft {filename}",
        )
        if "error" in draft_result:
            return self._json(500, {"error": f"stage=update_draft: {draft_result['error']}"}, cors)

        return self._json(200, {
            "success": True, "filename": filename,
            "image_url": article["image_url"],
            "image_alt": article["image_alt"],
            "image_credit": article["image_credit"],
            "image_photo_id": article["image_photo_id"],
            "image_bytes": len(img_bytes),
        }, cors)

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
