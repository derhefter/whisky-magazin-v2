"""
Vercel Serverless Function: Dashboard Authentication (HMAC-Token)
POST /api/admin_auth  -> {password} -> {token, expires}
GET  /api/admin_auth  -> Header: x-admin-token -> {valid: true/false}
"""
import os, json, hmac, hashlib, time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from collections import defaultdict

ADMIN_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "").strip()
TOKEN_TTL = 86400  # 24h in Sekunden

_rate_store = defaultdict(list)
RATE_LIMIT = 5   # max 5 Versuche pro 15 Min


def _make_token(timestamp_str: str) -> str:
    if not ADMIN_PASSWORD:
        return ""
    key = ADMIN_PASSWORD.encode()
    sig = hmac.new(key, timestamp_str.encode(), hashlib.sha256).hexdigest()
    return f"{timestamp_str}.{sig}"


def _verify_token(token: str) -> bool:
    if not ADMIN_PASSWORD:
        return False
    if not token or "." not in token:
        return False
    parts = token.split(".", 1)
    if len(parts) != 2:
        return False
    ts_str, sig = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    if time.time() - ts > TOKEN_TTL:
        return False
    expected = _make_token(ts_str)
    return hmac.compare_digest(token, expected)


def _rate_limited(ip: str) -> bool:
    now = time.time()
    window = 900  # 15 Minuten
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < window]
    if len(_rate_store[ip]) >= RATE_LIMIT:
        return True
    _rate_store[ip].append(now)
    return False


ALLOWED_ORIGINS = [
    "https://www.whisky-reise.com",
    "https://whisky-reise.com",
    "http://localhost:8000",
]


def _cors_headers(origin=""):
    allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-admin-token",
    }


class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _origin(self):
        return self.headers.get("Origin", "")

    def _send(self, code, data, headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in (_cors_headers(self._origin()) | (headers or {})).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers(self._origin()).items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        token = self.headers.get("x-admin-token", "")
        if _verify_token(token):
            self._send(200, {"valid": True})
        else:
            self._send(401, {"valid": False, "error": "Ungültiger oder abgelaufener Token"})

    def do_POST(self):
        ip = self.client_address[0]
        if _rate_limited(ip):
            self._send(429, {"error": "Zu viele Versuche. Bitte 15 Minuten warten."})
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except Exception:
            self._send(400, {"error": "Ungültiges JSON"})
            return

        password = body.get("password", "")
        if not ADMIN_PASSWORD:
            self._send(500, {"error": "DASHBOARD_PASSWORD nicht konfiguriert"})
            return

        if hmac.compare_digest(password.encode(), ADMIN_PASSWORD.encode()):
            ts = str(int(time.time()))
            token = _make_token(ts)
            expires = int(time.time()) + TOKEN_TTL
            self._send(200, {"token": token, "expires": expires})
        else:
            self._send(401, {"error": "Falsches Passwort"})
