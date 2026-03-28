"""Vercel Serverless Function: Newsletter-Anmeldung via Brevo API (Double Opt-In)."""
import json
import os
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


def _cors_headers(origin=""):
    allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


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

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
        except (json.JSONDecodeError, ValueError):
            self._respond(400, {"error": "Ungueltige Anfrage."}, cors)
            return

        email = (body.get("email") or "").strip().lower()
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            self._respond(400, {"error": "Bitte gib eine gueltige E-Mail-Adresse ein."}, cors)
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
                "message": "Fast geschafft! Bitte checke dein Postfach und bestaetige deine Anmeldung."
            }, cors)
        except HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            if e.code == 400 and "already exist" in error_body.lower():
                self._respond(200, {"message": "Du bist bereits angemeldet!"}, cors)
            else:
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
