"""Vercel Serverless Function: Dankes-E-Mail nach Fragebogen-Einreichung."""
import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen

BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BASE_URL = os.environ.get("BASE_URL", "https://www.whisky-reise.com")

ALLOWED_ORIGINS = [
    "https://www.whisky-reise.com",
    "https://www.whisky-magazin.de",
    "https://whisky-magazin.de",
    "http://localhost:3000",
    "http://localhost:8000",
]


def _cors_headers(origin=""):
    base = {
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    if origin in ALLOWED_ORIGINS:
        base["Access-Control-Allow-Origin"] = origin
    return base


def _send_thank_you(email, name):
    first_name = name.split()[0] if name else "du"
    B = BASE_URL
    html = (
        '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<title>Danke f&uuml;r dein Feedback</title></head>'
        '<body style="margin:0;padding:0;background:#FAFAF7;font-family:Inter,Helvetica,Arial,sans-serif;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#FAFAF7;">'
        '<tr><td align="center" style="padding:32px 16px;">'
        '<table width="560" cellpadding="0" cellspacing="0" border="0" '
        'style="max-width:560px;width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.06);">'
        # HEADER
        '<tr><td style="background:#2C2C2C;padding:32px 32px 28px;text-align:center;">'
        '<span style="font-family:Georgia,serif;font-size:26px;color:#fff;font-weight:700;">whisky</span>'
        '<span style="color:#C8963E;font-size:26px;">.</span>'
        '<span style="font-size:13px;letter-spacing:3px;text-transform:uppercase;color:#999;margin-left:4px;">MAGAZIN</span>'
        '</td></tr>'
        # HERO
        '<tr><td style="padding:40px 32px 28px;text-align:center;">'
        '<div style="font-size:52px;margin-bottom:20px;">&#127811;</div>'
        '<h1 style="font-family:Georgia,serif;font-size:26px;color:#2C2C2C;margin:0 0 14px;">'
        'Vielen Dank, ' + first_name + '!</h1>'
        '<p style="font-size:15px;color:#5C5C5C;line-height:1.7;margin:0;">'
        'Dein Feedback ist bei uns angekommen. Wir lesen jede Antwort pers&ouml;nlich &ndash; '
        'du hilfst uns wirklich, whisky&#8209;reise.com besser zu machen.</p>'
        '</td></tr>'
        '<tr><td style="padding:0 32px;"><div style="border-top:2px solid #C8963E;width:48px;margin:0 auto;"></div></td></tr>'
        # RAFFLE
        '<tr><td style="padding:28px 32px;">'
        '<div style="background:#1A1A1A;border-radius:10px;padding:28px;">'
        '<p style="font-size:11px;color:#C8963E;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin:0 0 14px;text-align:center;">'
        '&#127881; Deine Verlosungs-Teilnahme</p>'
        '<h2 style="font-family:Georgia,serif;font-size:20px;color:#fff;margin:0 0 14px;text-align:center;">'
        'Du bist dabei &ndash; Tasting mit Steffen &amp; Elmar</h2>'
        '<p style="font-size:14px;color:#c8c8c8;line-height:1.7;margin:0 0 20px;text-align:center;">'
        'Wir verlosen <strong style="color:#E8B86D;">3 Pl&auml;tze</strong> f&uuml;r ein pers&ouml;nliches Whisky-Tasting &ndash; '
        '5 ausgew&auml;hlte Whiskys, gemeinsam mit uns. '
        'Die drei besten Feedbacks gewinnen. Wir melden uns bei dir!</p>'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0">'
        '<tr>'
        '<td style="text-align:center;padding:8px;font-size:13px;color:#c8c8c8;">&#127811; 5 kuratierte Whiskys</td>'
        '<td style="text-align:center;padding:8px;font-size:13px;color:#c8c8c8;">&#128101; Pers&ouml;nlich &amp; entspannt</td>'
        '<td style="text-align:center;padding:8px;font-size:13px;color:#c8c8c8;">&#128279; Auch per Video-Call</td>'
        '</tr></table>'
        '</div></td></tr>'
        # CTA
        '<tr><td style="padding:8px 32px 32px;text-align:center;">'
        '<a href="' + B + '" style="display:inline-block;background:#C8963E;color:#fff;text-decoration:none;'
        'padding:13px 28px;border-radius:6px;font-size:15px;font-weight:600;">'
        'Magazin entdecken &rarr;</a>'
        '</td></tr>'
        # FOOTER
        '<tr><td style="padding:24px 32px;border-top:1px solid #E8E4DF;text-align:center;">'
        '<span style="font-family:Georgia,serif;font-size:16px;color:#2C2C2C;font-weight:700;">whisky</span>'
        '<span style="color:#C8963E;font-size:16px;">.</span>'
        '<span style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#8A8A8A;margin-left:3px;">MAGAZIN</span>'
        '<p style="font-size:12px;color:#8A8A8A;line-height:1.6;margin:12px 0 0;">'
        'Du erh&auml;ltst diese E-Mail, weil du an unserem Beta-Tester-Feedback teilgenommen hast.</p>'
        '<p style="font-size:12px;margin:12px 0 0;">'
        '<a href="' + B + '" style="color:#C8963E;text-decoration:none;">Website</a>'
        ' &middot; <a href="' + B + '/karte.html" style="color:#C8963E;text-decoration:none;">Whisky-Karte</a>'
        ' &middot; <a href="' + B + '/ueber-uns.html" style="color:#C8963E;text-decoration:none;">&Uuml;ber uns</a></p>'
        '<p style="font-size:11px;color:#B0B0B0;margin:12px 0 0;">'
        '&copy; 2007&ndash;2026 Whisky Magazin &middot; Steffen &amp; Elmar</p>'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )

    payload = json.dumps({
        "sender": {"name": "Steffen & Elmar", "email": "whisky-news@whisky-reise.com"},
        "to": [{"email": email, "name": name}],
        "subject": "Danke f\u00fcr dein Feedback \u2013 du bist dabei! \U0001f943",
        "htmlContent": html,
    }).encode("utf-8")

    req = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "api-key": BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    urlopen(req)


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
        except Exception:
            return self._json(400, {"error": "Ungueltige Anfrage."}, cors)

        email = (body.get("email") or "").strip()
        name = (body.get("name") or "").strip()

        if not email:
            return self._json(400, {"error": "E-Mail fehlt."}, cors)

        if not BREVO_API_KEY:
            return self._json(500, {"error": "E-Mail-Service nicht konfiguriert."}, cors)

        try:
            _send_thank_you(email, name)
            return self._json(200, {"ok": True}, cors)
        except Exception as exc:
            return self._json(500, {"error": str(exc)}, cors)

    def _json(self, status, data, cors):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass
