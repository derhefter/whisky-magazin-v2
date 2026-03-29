"""Vercel Serverless Function: Newsletter Double Opt-In via Brevo Transactional API."""
import json
import os
import re
import time
import hashlib
import hmac
from collections import defaultdict
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlparse, parse_qs


BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_LIST_ID = int(os.environ.get("BREVO_LIST_ID", "3"))
REDIRECT_URL = os.environ.get("BREVO_REDIRECT_URL", "https://whisky-magazin-new.vercel.app/danke.html")
BASE_URL = os.environ.get("BASE_URL", "https://whisky-magazin-new.vercel.app")

ALLOWED_ORIGINS = [
    "https://whisky-magazin-new.vercel.app",
    "https://www.whisky-magazin.de",
    "https://whisky-magazin.de",
    "http://localhost:3000",
    "http://localhost:8000",
]

_rate_store = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 5
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

# DOI confirmation email HTML (uses HTML entities for umlauts to avoid encoding issues)
DOI_HTML = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
    '<body style="font-family:Inter,Helvetica,Arial,sans-serif;background:#FAFAF7;margin:0;padding:40px 20px;">'
    '<div style="max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">'
    '<div style="background:#2C2C2C;padding:32px 24px;text-align:center;">'
    '<span style="font-family:Georgia,serif;font-size:24px;color:#fff;font-weight:700;">whisky</span>'
    '<span style="color:#C8963E;font-size:24px;">.</span>'
    '<span style="font-size:14px;letter-spacing:3px;text-transform:uppercase;color:rgba(255,255,255,0.7);margin-left:4px;">MAGAZIN</span>'
    '</div>'
    '<div style="padding:40px 32px;text-align:center;">'
    '<h1 style="font-family:Georgia,serif;font-size:22px;color:#2C2C2C;margin:0 0 16px;">Fast geschafft!</h1>'
    '<p style="font-size:15px;color:#5C5C5C;line-height:1.7;margin:0 0 28px;">'
    'Du hast dich f&uuml;r unseren Newsletter angemeldet. '
    'Best&auml;tige jetzt deine E-Mail-Adresse, um dabei zu sein.</p>'
    '<a href="CONFIRM_URL_PLACEHOLDER" style="display:inline-block;background:#C8963E;color:#fff;'
    'text-decoration:none;padding:14px 36px;border-radius:6px;font-size:15px;font-weight:600;">'
    'Anmeldung best&auml;tigen</a>'
    '<p style="font-size:13px;color:#8A8A8A;margin:28px 0 0;line-height:1.6;">'
    'Einmal im Monat die besten Whisky-Geschichten und Reise-Tipps.<br>'
    'Kein Spam. Jederzeit abbestellbar.</p>'
    '</div>'
    '<div style="border-top:1px solid #E8E4DF;padding:20px 32px;text-align:center;">'
    '<p style="font-size:12px;color:#8A8A8A;margin:0;">&copy; 2007&ndash;2026 Whisky Magazin</p>'
    '</div></div></body></html>'
)


def _get_secret():
    if not BREVO_API_KEY:
        return "fallback-secret"
    return hashlib.sha256(BREVO_API_KEY.encode()).hexdigest()[:32]


def _make_token(email):
    secret = _get_secret()
    return hmac.new(secret.encode(), email.lower().strip().encode(), hashlib.sha256).hexdigest()


def _cors_headers(origin=""):
    base = {"Access-Control-Allow-Methods": "POST, GET, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"}
    if origin in ALLOWED_ORIGINS:
        base["Access-Control-Allow-Origin"] = origin
    return base


def _is_rate_limited(ip):
    now = time.time()
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < 60]
    if len(_rate_store[ip]) >= RATE_LIMIT_PER_MINUTE:
        return True
    _rate_store[ip].append(now)
    return False


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        self.send_response(204)
        for k, v in _cors_headers(origin).items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        """Handle DOI confirmation link clicks."""
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            action = params.get("action", [""])[0]
            email = params.get("email", [""])[0].strip().lower()
            token = params.get("token", [""])[0]

            if action == "confirm" and email and token:
                expected = _make_token(email)
                if hmac.compare_digest(token, expected):
                    # Valid token - add to Brevo list
                    try:
                        payload = json.dumps({"email": email, "listIds": [BREVO_LIST_ID], "updateEnabled": True}).encode("utf-8")
                        req = Request("https://api.brevo.com/v3/contacts", data=payload, headers={
                            "api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json",
                        }, method="POST")
                        urlopen(req)
                    except Exception:
                        pass

                    self.send_response(302)
                    self.send_header("Location", REDIRECT_URL)
                    self.end_headers()
                    return

            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><p>Ungueltiger oder abgelaufener Link.</p></body></html>")
        except Exception:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Server error")

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        cors = _cors_headers(origin)

        try:
            client_ip = self.headers.get("X-Forwarded-For", "unknown")
            if client_ip and "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()
        except Exception:
            client_ip = "unknown"

        if _is_rate_limited(client_ip):
            return self._json(429, {"error": "Zu viele Anfragen. Bitte warte einen Moment."}, cors)

        if origin and origin not in ALLOWED_ORIGINS:
            return self._json(403, {"error": "Zugriff verweigert."}, cors)

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 1024:
                return self._json(400, {"error": "Anfrage zu gross."}, cors)
            body = json.loads(self.rfile.read(length)) if length else {}
        except Exception:
            return self._json(400, {"error": "Ungueltige Anfrage."}, cors)

        email = (body.get("email") or "").strip().lower()
        if not email or not EMAIL_REGEX.match(email) or len(email) > 254:
            return self._json(400, {"error": "Bitte gib eine gueltige E-Mail-Adresse ein."}, cors)

        if not BREVO_API_KEY:
            return self._json(500, {"error": "Newsletter-Service nicht konfiguriert."}, cors)

        # Check if already subscribed
        try:
            req = Request("https://api.brevo.com/v3/contacts/" + email, headers={
                "api-key": BREVO_API_KEY, "Accept": "application/json",
            }, method="GET")
            resp = urlopen(req)
            contact = json.loads(resp.read().decode())
            if BREVO_LIST_ID in contact.get("listIds", []):
                return self._json(200, {"message": "Du bist bereits angemeldet!"}, cors)
        except Exception:
            pass

        # Send DOI email via Brevo transactional API
        try:
            token = _make_token(email)
            confirm_url = BASE_URL + "/api/subscribe?action=confirm&email=" + email + "&token=" + token
            html = DOI_HTML.replace("CONFIRM_URL_PLACEHOLDER", confirm_url)

            payload = json.dumps({
                "sender": {"name": "Steffen & Elmar", "email": "whisky-news@whisky-reise.com"},
                "to": [{"email": email}],
                "subject": "Bitte best\u00e4tige deine Anmeldung zum Whisky Magazin Newsletter",
                "htmlContent": html,
            }).encode("utf-8")

            req = Request("https://api.brevo.com/v3/smtp/email", data=payload, headers={
                "api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json",
            }, method="POST")
            urlopen(req)

            return self._json(200, {
                "message": "Fast geschafft! Bitte checke dein Postfach und best\u00e4tige deine Anmeldung."
            }, cors)
        except Exception:
            return self._json(500, {
                "error": "Anmeldung fehlgeschlagen. Bitte versuche es sp\u00e4ter."
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
