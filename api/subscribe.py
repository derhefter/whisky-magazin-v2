"""Vercel Serverless Function: Newsletter-Anmeldung via Brevo API (Double Opt-In)."""
import json
import os
import re
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler
try:
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
except ImportError:
    pass


BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
BREVO_LIST_ID = int(os.environ.get("BREVO_LIST_ID", "3"))
BREVO_DOI_TEMPLATE_ID = int(os.environ.get("BREVO_DOI_TEMPLATE_ID", "1"))
REDIRECT_URL = os.environ.get("BREVO_REDIRECT_URL", "https://whisky-magazin-new.vercel.app/?subscribed=1")
ALLOWED_ORIGINS = [
    "https://whisky-magazin-new.vercel.app",
    "https://www.whisky-magazin.de",
    "https://whisky-magazin.de",
    "http://localhost:3000",
    "http://localhost:8000",
]

# Simple in-memory rate limiting (resets on cold start)
_rate_store = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 5

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def _cors_headers(origin=""):
    """Returns CORS headers only for allowed origins. Returns None for unknown origins."""
    if origin in ALLOWED_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        }
    # Unknown origin: return restrictive headers (no ACAO = browser blocks response)
    return {
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def _is_rate_limited(client_ip):
    """Basic rate limiting: max N requests per minute per IP."""
    now = time.time()
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if now - t < 60]
    if len(_rate_store[client_ip]) >= RATE_LIMIT_PER_MINUTE:
        return True
    _rate_store[client_ip].append(now)
    return False


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        self.send_response(204)
        for k, v in _cors_headers(origin).items():
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        cors = _cors_headers(origin)

        # Rate limiting
        client_ip = self.client_address[0] if self.client_address else "unknown"
        if _is_rate_limited(client_ip):
            self._respond(429, {"error": "Zu viele Anfragen. Bitte warte einen Moment."}, cors)
            return

        # Reject requests without valid Origin header
        if origin and origin not in ALLOWED_ORIGINS:
            self._respond(403, {"error": "Zugriff verweigert."}, cors)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 1024:  # Max 1KB payload
                self._respond(400, {"error": "Anfrage zu groß."}, cors)
                return
            body = json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, ValueError):
            self._respond(400, {"error": "Ungültige Anfrage."}, cors)
            return

        email = (body.get("email") or "").strip().lower()
        if not email or not EMAIL_REGEX.match(email) or len(email) > 254:
            self._respond(400, {"error": "Bitte gib eine gültige E-Mail-Adresse ein."}, cors)
            return

        if not BREVO_API_KEY:
            self._respond(500, {"error": "Newsletter-Service nicht konfiguriert."}, cors)
            return

        # Double Opt-In: Sends confirmation email, adds to list only after click
        payload = json.dumps({
            "email": email,
            "includeListIds": [BREVO_LIST_ID],
            "templateId": BREVO_DOI_TEMPLATE_ID,
            "redirectionUrl": REDIRECT_URL,
        }).encode("utf-8")

        req = Request(
            "https://api.brevo.com/v3/contacts/doubleOptinConfirmation",
            data=payload,
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            urlopen(req)
            self._respond(200, {
                "message": "Fast geschafft! Bitte checke dein Postfach und bestätige deine Anmeldung."
            }, cors)
        except HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            if e.code == 400 and "already exist" in error_body.lower():
                self._respond(200, {"message": "Du bist bereits angemeldet!"}, cors)
            else:
                self._respond(500, {
                    "error": "Anmeldung fehlgeschlagen. Bitte versuche es später."
                }, cors)

    def _respond(self, status, data, cors):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
