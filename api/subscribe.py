"""Vercel Serverless Function: Newsletter-Anmeldung via Brevo API (Double Opt-In).

Ansatz: Da die Brevo DOI-API auf Free-Accounts Probleme macht,
verwenden wir einen eigenen DOI-Flow:
1. Kontakt erstellen (nicht in Liste, nur in Brevo)
2. Transactional E-Mail mit Bestaetigungslink senden
3. Bestaetigungslink fuehrt zu /api/confirm?token=...
4. confirm-Endpoint fuegt Kontakt zur Liste hinzu

Vereinfachte Version: Direkte Kontakterstellung in der Liste
(Brevo hat bereits ein aktives Formular mit DOI konfiguriert).
"""
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


BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_LIST_ID = int(os.environ.get("BREVO_LIST_ID", "3"))
BREVO_DOI_TEMPLATE_ID = int(os.environ.get("BREVO_DOI_TEMPLATE_ID", "2"))
REDIRECT_URL = os.environ.get("BREVO_REDIRECT_URL", "https://whisky-magazin-new.vercel.app/?subscribed=1")
BASE_URL = os.environ.get("BASE_URL", "https://whisky-magazin-new.vercel.app")
# Secret for HMAC token generation (fallback to API key hash if not set)
DOI_SECRET = os.environ.get("DOI_SECRET", "")

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


def _get_secret():
    """Get the HMAC secret for DOI tokens."""
    if DOI_SECRET:
        return DOI_SECRET
    # Derive from API key if no separate secret configured
    return hashlib.sha256(BREVO_API_KEY.encode()).hexdigest()[:32]


def _make_doi_token(email):
    """Create an HMAC token for email confirmation."""
    secret = _get_secret()
    return hmac.new(secret.encode(), email.lower().encode(), hashlib.sha256).hexdigest()


def _cors_headers(origin=""):
    base = {
        "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    if origin in ALLOWED_ORIGINS:
        base["Access-Control-Allow-Origin"] = origin
    return base


def _is_rate_limited(client_ip):
    now = time.time()
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if now - t < 60]
    if len(_rate_store[client_ip]) >= RATE_LIMIT_PER_MINUTE:
        return True
    _rate_store[client_ip].append(now)
    return False


def _brevo_request(method, endpoint, data=None):
    """Make a Brevo API request."""
    url = "https://api.brevo.com/v3/" + endpoint
    payload = json.dumps(data).encode("utf-8") if data else None
    req = Request(url, data=payload, headers={
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }, method=method)
    return urlopen(req)


def _send_doi_email(email, token):
    """Send a DOI confirmation email via Brevo transactional API."""
    confirm_url = "{}/api/subscribe?action=confirm&email={}&token={}".format(
        BASE_URL, email, token
    )

    html = """<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="font-family:Inter,Helvetica,Arial,sans-serif;background:#FAFAF7;margin:0;padding:40px 20px;">
<div style="max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
<div style="background:#2C2C2C;padding:32px 24px;text-align:center;">
<span style="font-family:Georgia,serif;font-size:24px;color:#fff;font-weight:700;">whisky</span><span style="color:#C8963E;font-size:24px;">.</span><span style="font-size:14px;letter-spacing:3px;text-transform:uppercase;color:rgba(255,255,255,0.7);margin-left:4px;">MAGAZIN</span>
</div>
<div style="padding:40px 32px;text-align:center;">
<h1 style="font-family:Georgia,serif;font-size:22px;color:#2C2C2C;margin:0 0 16px;">Fast geschafft!</h1>
<p style="font-size:15px;color:#5C5C5C;line-height:1.7;margin:0 0 28px;">Du hast dich f&uuml;r unseren Newsletter angemeldet. Best&auml;tige jetzt deine E-Mail-Adresse, um dabei zu sein.</p>
<a href="{confirm_url}" style="display:inline-block;background:#C8963E;color:#fff;text-decoration:none;padding:14px 36px;border-radius:6px;font-size:15px;font-weight:600;">Anmeldung best&auml;tigen</a>
<p style="font-size:13px;color:#8A8A8A;margin:28px 0 0;line-height:1.6;">Einmal im Monat die besten Whisky-Geschichten und Reise-Tipps.<br>Kein Spam. Jederzeit abbestellbar.</p>
</div>
<div style="border-top:1px solid #E8E4DF;padding:20px 32px;text-align:center;">
<p style="font-size:12px;color:#8A8A8A;margin:0;">&copy; 2007&ndash;2026 Whisky Magazin</p>
</div></div></body></html>""".replace("{confirm_url}", confirm_url)

    _brevo_request("POST", "smtp/email", {
        "sender": {"name": "Steffen & Elmar", "email": "whisky-news@whisky-reise.com"},
        "to": [{"email": email}],
        "subject": "Bitte best\u00e4tige deine Anmeldung zum Whisky Magazin Newsletter",
        "htmlContent": html,
    })


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        self.send_response(204)
        for k, v in _cors_headers(origin).items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        """Handle DOI confirmation clicks."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        action = params.get("action", [""])[0]
        email = params.get("email", [""])[0].strip().lower()
        token = params.get("token", [""])[0]

        if action == "confirm" and email and token:
            expected = _make_doi_token(email)
            if hmac.compare_digest(token, expected):
                # Token valid - add contact to list
                try:
                    _brevo_request("POST", "contacts", {
                        "email": email,
                        "listIds": [BREVO_LIST_ID],
                        "updateEnabled": True,
                    })
                except HTTPError:
                    pass  # Contact might already exist, that's fine

                # Redirect to success page
                self.send_response(302)
                self.send_header("Location", REDIRECT_URL)
                self.end_headers()
                return
            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<html><body><h2>Ungueltiger Link</h2><p>Dieser Bestaetigungslink ist ungueltig oder abgelaufen.</p></body></html>")
                return

        self.send_response(405)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Method not allowed")

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        cors = _cors_headers(origin)

        try:
            client_ip = self.headers.get("X-Forwarded-For", "unknown")
            if "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()
        except Exception:
            client_ip = "unknown"

        if _is_rate_limited(client_ip):
            self._respond(429, {"error": "Zu viele Anfragen. Bitte warte einen Moment."}, cors)
            return

        if origin and origin not in ALLOWED_ORIGINS:
            self._respond(403, {"error": "Zugriff verweigert."}, cors)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 1024:
                self._respond(400, {"error": "Anfrage zu gross."}, cors)
                return
            body = json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, ValueError):
            self._respond(400, {"error": "Ungueltige Anfrage."}, cors)
            return

        email = (body.get("email") or "").strip().lower()
        if not email or not EMAIL_REGEX.match(email) or len(email) > 254:
            self._respond(400, {"error": "Bitte gib eine gueltige E-Mail-Adresse ein."}, cors)
            return

        if not BREVO_API_KEY:
            self._respond(500, {"error": "Newsletter-Service nicht konfiguriert."}, cors)
            return

        # Check if contact already exists in the list
        try:
            resp = _brevo_request("GET", "contacts/{}".format(email))
            contact = json.loads(resp.read().decode())
            list_ids = contact.get("listIds", [])
            if BREVO_LIST_ID in list_ids:
                self._respond(200, {"message": "Du bist bereits angemeldet!"}, cors)
                return
        except HTTPError:
            pass  # Contact doesn't exist yet, that's fine

        # Send DOI confirmation email
        try:
            token = _make_doi_token(email)
            _send_doi_email(email, token)
            self._respond(200, {
                "message": "Fast geschafft! Bitte checke dein Postfach und bestaetige deine Anmeldung."
            }, cors)
        except HTTPError as e:
            try:
                error_body = e.read().decode("utf-8", errors="replace")
            except Exception:
                error_body = ""
            self._respond(500, {
                "error": "Anmeldung fehlgeschlagen. Bitte versuche es spaeter."
            }, cors)
        except Exception:
            self._respond(500, {
                "error": "Anmeldung fehlgeschlagen. Bitte versuche es spaeter."
            }, cors)

    def _respond(self, status, data, cors):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        pass
