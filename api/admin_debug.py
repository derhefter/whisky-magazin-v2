"""Temporaerer Debug-Endpoint - zeigt API-Status ohne sensitive Daten."""
import os, json, hmac, hashlib, time
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ADMIN_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "").strip()
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO    = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
BREVO_API_KEY  = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_LIST_ID  = os.environ.get("BREVO_LIST_ID", "3").strip()
TOKEN_TTL      = 86400

ALLOWED_ORIGINS = [
    "https://www.whisky-reise.com",
    "https://whisky-reise.com",
    "http://localhost:8000",
]

def _verify_token(token):
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

class handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        token = self.headers.get("x-admin-token", "")
        if not _verify_token(token):
            self._send(401, {"error": "Nicht autorisiert"})
            return

        results = {}

        # ENV VARS vorhanden?
        results["env"] = {
            "DASHBOARD_PASSWORD": "gesetzt" if ADMIN_PASSWORD else "FEHLT",
            "GITHUB_TOKEN": "gesetzt" if GITHUB_TOKEN else "FEHLT",
            "GITHUB_REPO": GITHUB_REPO or "FEHLT",
            "BREVO_API_KEY": "gesetzt" if BREVO_API_KEY else "FEHLT",
            "BREVO_LIST_ID": BREVO_LIST_ID or "FEHLT",
        }

        # GitHub API testen
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/data/topics_queue.json"
            req = Request(url, headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "WhiskyMagazin-Debug",
            })
            with urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results["github_topics"] = {
                    "status": "OK",
                    "file_size": data.get("size", 0),
                    "sha": data.get("sha", "")[:10],
                }
        except HTTPError as e:
            results["github_topics"] = {"status": f"HTTP {e.code}", "error": str(e)}
        except Exception as e:
            results["github_topics"] = {"status": "FEHLER", "error": str(e)}

        # GitHub drafts testen
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/articles/drafts"
            req = Request(url, headers={
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "WhiskyMagazin-Debug",
            })
            with urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                files = [f["name"] for f in data if isinstance(f, dict)] if isinstance(data, list) else []
                results["github_drafts"] = {"status": "OK", "files": files}
        except HTTPError as e:
            results["github_drafts"] = {"status": f"HTTP {e.code}", "error": str(e)}
        except Exception as e:
            results["github_drafts"] = {"status": "FEHLER", "error": str(e)}

        # Brevo testen
        try:
            req = Request(
                f"https://api.brevo.com/v3/contacts/lists/{BREVO_LIST_ID}",
                headers={"api-key": BREVO_API_KEY, "Accept": "application/json"},
            )
            with urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results["brevo"] = {
                    "status": "OK",
                    "totalSubscribers": data.get("totalSubscribers", 0),
                    "name": data.get("name", ""),
                }
        except HTTPError as e:
            results["brevo"] = {"status": f"HTTP {e.code}", "error": str(e)}
        except Exception as e:
            results["brevo"] = {"status": "FEHLER", "error": str(e)}

        self._send(200, results)

    def _send(self, code, data):
        origin = self.headers.get("Origin", "")
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
        self.send_header("Access-Control-Allow-Origin", allowed)
        self.send_header("Access-Control-Allow-Headers", "x-admin-token")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", allowed)
        self.send_header("Access-Control-Allow-Headers", "x-admin-token")
        self.end_headers()
