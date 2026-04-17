"""Vercel Serverless Function: Newsletter-Erinnerungen.

Cron-Zeitplan (vercel.json):
  15. des Monats 08:00 UTC → Erinnerung: Whisky-Daten eintragen
  20. des Monats 08:00 UTC → Vorstellung: Newsletter generieren
  30. des Monats 08:00 UTC → Fertigstellung: Newsletter freigeben & speichern
  Erster Montag des Monats 07:00 UTC → Versand-Erinnerung (manuell via Admin oder auto)
"""
import json
import os
import time
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BREVO_API_KEY  = os.environ.get("BREVO_API_KEY", "").strip()
CRON_SECRET    = os.environ.get("CRON_SECRET", "").strip()
REMINDER_EMAIL = "rosenhefter@gmail.com"
SENDER_EMAIL   = "newsletter@whiskyreise.de"
SENDER_NAME    = "Whisky Magazin"
SITE_URL       = os.environ.get("SITE_URL", "https://www.whisky-reise.com").strip()

MONATE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def _send_transactional_email(to_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    if not BREVO_API_KEY:
        return False, "BREVO_API_KEY fehlt"
    payload = json.dumps({
        "sender":  {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "to":      [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }).encode("utf-8")
    req = Request(
        "https://api.brevo.com/v3/smtp/email",
        data=payload,
        headers={
            "api-key":      BREVO_API_KEY,
            "Content-Type": "application/json",
            "Accept":       "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=15) as r:
            return True, ""
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"{e.code}: {body[:200]}"
    except Exception as e:
        return False, str(e)


def _reminder_html(title: str, body_html: str, month_label: str) -> str:
    admin_url = f"{SITE_URL}/admin/"
    return f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8">
<title>{title}</title></head>
<body style="font-family:Arial,sans-serif;background:#FAF8F4;padding:32px 16px;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:8px;padding:32px;
              box-shadow:0 2px 8px rgba(0,0,0,.1);">
    <p style="margin:0 0 4px;font-size:0.75rem;color:#C8963E;text-transform:uppercase;
              letter-spacing:2px;font-weight:700;">Whisky Magazin · Automatische Erinnerung</p>
    <h2 style="margin:0 0 20px;font-size:1.3rem;color:#2A2520;">{title}</h2>
    <p style="color:#6B6460;font-size:0.9rem;">Newsletter-Monat: <strong>{month_label}</strong></p>
    {body_html}
    <p style="margin:24px 0 0;">
      <a href="{admin_url}" style="display:inline-block;background:#C8963E;color:#fff;
         padding:10px 22px;border-radius:6px;text-decoration:none;font-weight:600;">
        Admin-Dashboard öffnen →
      </a>
    </p>
    <p style="margin:20px 0 0;font-size:0.75rem;color:#9E9690;">
      Diese E-Mail wurde automatisch vom Whisky-Magazin-System gesendet.
    </p>
  </div>
</body></html>"""


def _get_newsletter_month() -> tuple[str, str]:
    """Return the newsletter month: current month (send goes out 1st Monday of NEXT month,
    so data entry happens in the CURRENT month for the NEXT month's newsletter)."""
    t = time.gmtime()
    # Newsletter content is for the NEXT month
    next_month = t.tm_mon % 12 + 1
    next_year  = t.tm_year + (1 if t.tm_mon == 12 else 0)
    month_key   = f"{next_year}-{next_month:02d}"
    month_label = f"{MONATE[next_month]} {next_year}"
    return month_key, month_label


def _handle_reminder(day: int) -> tuple[int, dict]:
    month_key, month_label = _get_newsletter_month()

    if day == 15:
        subject = f"📅 Newsletter {month_label}: Deadline in 5 Tagen – Daten eintragen!"
        body_html = """
        <p style="color:#2A2520;line-height:1.7;">
          <strong>Erinnerung:</strong> Bitte bis zum <strong>20. des Monats</strong> den
          Whisky des Monats und alle Newsletter-Daten im Admin-Dashboard eintragen.
        </p>
        <ul style="color:#6B6460;line-height:2;">
          <li>Whisky-Name, Destillerie, Region</li>
          <li>Kommentar &amp; Verkostungsnotizen</li>
          <li>Optionale Fotos hochladen</li>
          <li>Specials / Sonderthemen eintragen</li>
        </ul>"""
    elif day == 20:
        subject = f"✏️ Newsletter {month_label}: Bitte heute Newsletter generieren"
        body_html = """
        <p style="color:#2A2520;line-height:1.7;">
          Heute ist der <strong>20. des Monats</strong> – Zeit, den Newsletter zu generieren
          und die Vorschau zu prüfen.
        </p>
        <ol style="color:#6B6460;line-height:2;">
          <li>Admin → WotM &amp; Newsletter Tab öffnen</li>
          <li>Whisky-Daten prüfen und ggf. ergänzen</li>
          <li>„Newsletter generieren" klicken</li>
          <li>Vorschau prüfen, Texte bei Bedarf anpassen</li>
          <li>„Newsletter speichern" klicken</li>
        </ol>"""
    elif day == 30:
        subject = f"✅ Newsletter {month_label}: Fertigstellung – bitte freigeben!"
        body_html = """
        <p style="color:#2A2520;line-height:1.7;">
          Der Newsletter sollte heute <strong>fertiggestellt und freigegeben</strong> werden.
          Der Versand erfolgt am ersten Montag des Folgemonats automatisch.
        </p>
        <ol style="color:#6B6460;line-height:2;">
          <li>Newsletter-Vorschau ein letztes Mal prüfen</li>
          <li>Falls nötig: Felder anpassen und neu generieren</li>
          <li>„Newsletter speichern" klicken (finales HTML sichern)</li>
          <li>Am ersten Montag: „Newsletter jetzt senden" im Admin-Dashboard</li>
        </ol>"""
    else:
        return 400, {"error": f"Unbekannter Tag: {day}"}

    html = _reminder_html(subject, body_html, month_label)
    ok, err = _send_transactional_email(REMINDER_EMAIL, subject, html)
    if not ok:
        return 500, {"error": err}
    return 200, {"ok": True, "month": month_key, "subject": subject}


class handler(BaseHTTPRequestHandler):

    def _check_cron_auth(self) -> bool:
        if not CRON_SECRET:
            return False
        return self.headers.get("Authorization", "") == f"Bearer {CRON_SECRET}"

    def _json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self._check_cron_auth():
            return self._json(401, {"error": "Unauthorized"})

        # Determine which reminder to send based on today's day-of-month
        day = int(time.strftime("%d", time.gmtime()))
        # Allow override via query param: ?day=15
        from urllib.parse import parse_qs, urlparse
        qs = parse_qs(urlparse(self.path).query)
        if "day" in qs:
            try:
                day = int(qs["day"][0])
            except Exception:
                pass

        status, result = _handle_reminder(day)
        self._json(status, result)

    def log_message(self, fmt, *args):
        pass
