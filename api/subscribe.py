"""Vercel Serverless Function: Newsletter-Anmeldung via Brevo API (Double Opt-In)."""
import json
import os
import re
import time
from collections import defaultdict
from urllib.request import Request, urlopen
from urllib.error import HTTPError


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
_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 5

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def _cors_headers(origin=""):
    """Returns CORS headers for allowed origins."""
    base = {
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    if origin in ALLOWED_ORIGINS:
        base["Access-Control-Allow-Origin"] = origin
    return base


def _is_rate_limited(client_ip):
    """Basic rate limiting: max N requests per minute per IP."""
    now = time.time()
    _rate_store[client_ip] = [t for t in _rate_store[client_ip] if now - t < 60]
    if len(_rate_store[client_ip]) >= RATE_LIMIT_PER_MINUTE:
        return True
    _rate_store[client_ip].append(now)
    return False


def _response(status_code, body, cors_headers):
    """Build a Vercel-compatible response dict."""
    headers = {"Content-Type": "application/json; charset=utf-8"}
    headers.update(cors_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body, ensure_ascii=False),
    }


def handler(request):
    """Vercel Python Serverless Function handler."""
    method = request.method if hasattr(request, 'method') else "GET"
    origin = ""

    # Extract origin from headers
    if hasattr(request, 'headers'):
        if isinstance(request.headers, dict):
            origin = request.headers.get("origin", request.headers.get("Origin", ""))
        else:
            origin = request.headers.get("Origin", "")

    cors = _cors_headers(origin)

    # Handle OPTIONS (CORS preflight)
    if method == "OPTIONS":
        return _response(204, {}, cors)

    # Only allow POST
    if method != "POST":
        return _response(405, {"error": "Method not allowed."}, cors)

    # Rate limiting
    client_ip = "unknown"
    if hasattr(request, 'headers'):
        if isinstance(request.headers, dict):
            client_ip = request.headers.get("x-forwarded-for", request.headers.get("x-real-ip", "unknown"))
        else:
            client_ip = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-Ip", "unknown"))
    if isinstance(client_ip, str) and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    if _is_rate_limited(client_ip):
        return _response(429, {"error": "Zu viele Anfragen. Bitte warte einen Moment."}, cors)

    # Reject unknown origins
    if origin and origin not in ALLOWED_ORIGINS:
        return _response(403, {"error": "Zugriff verweigert."}, cors)

    # Parse body
    try:
        raw_body = ""
        if hasattr(request, 'body'):
            raw_body = request.body if isinstance(request.body, str) else request.body.decode("utf-8")
        elif hasattr(request, 'data'):
            raw_body = request.data if isinstance(request.data, str) else request.data.decode("utf-8")

        if len(raw_body) > 1024:
            return _response(400, {"error": "Anfrage zu groß."}, cors)

        body = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, ValueError):
        return _response(400, {"error": "Ungültige Anfrage."}, cors)

    email = (body.get("email") or "").strip().lower()
    if not email or not EMAIL_REGEX.match(email) or len(email) > 254:
        return _response(400, {"error": "Bitte gib eine gültige E-Mail-Adresse ein."}, cors)

    if not BREVO_API_KEY:
        return _response(500, {"error": "Newsletter-Service nicht konfiguriert."}, cors)

    # Double Opt-In via Brevo API
    payload = json.dumps({
        "email": email,
        "includeListIds": [BREVO_LIST_ID],
        "templateId": BREVO_DOI_TEMPLATE_ID,
        "redirectionUrl": REDIRECT_URL,
    }).encode("utf-8")

    api_req = Request(
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
        urlopen(api_req)
        return _response(200, {
            "message": "Fast geschafft! Bitte checke dein Postfach und bestätige deine Anmeldung."
        }, cors)
    except HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        if e.code == 400 and "already exist" in error_body.lower():
            return _response(200, {"message": "Du bist bereits angemeldet!"}, cors)
        return _response(500, {
            "error": "Anmeldung fehlgeschlagen. Bitte versuche es später."
        }, cors)
    except Exception:
        return _response(500, {
            "error": "Anmeldung fehlgeschlagen. Bitte versuche es später."
        }, cors)
