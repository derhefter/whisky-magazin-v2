#!/usr/bin/env python3
"""
=============================================================
  WHISKY MAGAZIN - E-Mail Benachrichtigungen
=============================================================

Sendet automatische E-Mail-Benachrichtigungen an
whisky-news@whisky-reise.com bei wichtigen Redaktionsereignissen:

  - Newsletter-Entwurf bereit zur Freigabe
  - Whisky des Monats Entwurf bereit
  - Newsletter wurde versendet
  - Monatliche Erinnerung (kein WOTM gesetzt)

Konfiguration in config.json:
  "notifications": {
    "email": "whisky-news@whisky-reise.com",
    "smtp_sender": "sender@gmail.com",
    "smtp_app_password": "xxxx xxxx xxxx xxxx",
    "enabled": true
  }
=============================================================
"""

import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime

PROJECT_DIR = Path(__file__).parent
CONFIG_PATH = PROJECT_DIR / "config.json"

# ============================================================
# Hilfsfunktionen
# ============================================================

def print_box(lines, width=52):
    """Gibt Text in einer ASCII-Box aus."""
    print()
    print("  +" + "=" * width + "+")
    for line in lines:
        padded = line.ljust(width - 2)
        print(f"  |  {padded}  |")
    print("  +" + "=" * width + "+")
    print()


def load_notif_config():
    """
    Laedt config.json und gibt den 'notifications'-Block zurueck.
    Gibt None zurueck wenn nicht konfiguriert oder deaktiviert.
    """
    if not CONFIG_PATH.exists():
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        notif = config.get("notifications", {})
        if not notif.get("enabled", False):
            return None
        if not notif.get("smtp_sender") or not notif.get("smtp_app_password"):
            return None
        return notif
    except Exception:
        return None


def _base_html(title, content_html):
    """Baut das HTML-Grundgeruest fuer alle Benachrichtigungen."""
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#EDE9E3;
             font-family:Georgia,'Times New Roman',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#EDE9E3;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;width:100%;background-color:#FAF8F4;">

        <!-- HEADER -->
        <tr>
          <td style="background-color:#2A2520;padding:24px 40px;text-align:center;">
            <p style="margin:0 0 4px 0;font-size:11px;color:#B8762E;
                      text-transform:uppercase;letter-spacing:3px;">
              Redaktionssystem
            </p>
            <h1 style="margin:0;font-size:22px;font-weight:bold;color:#FAF8F4;
                       letter-spacing:2px;">
              WHISKY MAGAZIN
            </h1>
          </td>
        </tr>

        <!-- INHALT -->
        <tr>
          <td style="padding:32px 40px;">
            {content_html}
          </td>
        </tr>

        <!-- FOOTER -->
        <tr>
          <td style="background-color:#F2EDE6;padding:16px 40px;text-align:center;
                     border-top:3px solid #B8762E;">
            <p style="margin:0;font-size:11px;color:#8A8480;">
              Whisky Magazin Redaktionssystem &bull; {now_str}
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _section(label, value):
    """Hilfsfunktion fuer Info-Zeilen im E-Mail-Body."""
    return (
        f'<p style="margin:0 0 8px 0;font-size:14px;color:#4A4440;">'
        f'<strong style="color:#2A2520;">{label}:</strong> {value}</p>'
    )


def _cmd_box(command):
    """Zeigt einen Python-Befehl als hervorgehobenen Block."""
    return (
        f'<div style="margin:20px 0;padding:14px 18px;background-color:#2A2520;'
        f'border-radius:4px;">'
        f'<code style="font-family:monospace;font-size:13px;color:#B8762E;">'
        f'{command}</code></div>'
    )


# ============================================================
# Kern-Sendefunktion
# ============================================================

def send_notification(subject, html_body, text_body=None):
    """
    Sendet eine E-Mail via Gmail SMTP (smtp.gmail.com:587, STARTTLS).
    Gibt True bei Erfolg, False bei Fehler zurueck.
    """
    notif = load_notif_config()
    if not notif:
        print("  [Notifier] Benachrichtigungen nicht konfiguriert - uebersprungen.")
        return False

    sender   = notif["smtp_sender"]
    password = notif["smtp_app_password"]
    recipient = notif.get("email", "whisky-news@whisky-reise.com")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Whisky Magazin <{sender}>"
    msg["To"]      = recipient

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, [recipient], msg.as_bytes())
        print(f"  [Notifier] E-Mail gesendet an {recipient}: {subject[:50]}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("  [Notifier] FEHLER: SMTP-Authentifizierung fehlgeschlagen.")
        print("             Bitte App-Passwort in config.json pruefen.")
        return False
    except Exception as exc:
        print(f"  [Notifier] FEHLER beim E-Mail-Versand: {exc}")
        return False


# ============================================================
# Spezifische Benachrichtigungen
# ============================================================

def notify_newsletter_draft_ready(draft_data):
    """
    Benachrichtigt wenn ein Newsletter-Entwurf erstellt wurde.
    draft_data: das newsletter_draft.json Dict
    """
    subject_line = draft_data.get("subject", "Newsletter")
    preview      = draft_data.get("preview_text", "-")
    created      = draft_data.get("created_at", "")
    content      = draft_data.get("content_data", {})
    wotm         = content.get("wotm_section", {})
    wotm_name    = wotm.get("headline", "-")
    art_count    = len(content.get("article_teasers", []))

    try:
        dt = datetime.fromisoformat(created)
        created = dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        pass

    content_html = f"""
      <p style="margin:0 0 6px 0;font-size:12px;color:#B8762E;
                text-transform:uppercase;letter-spacing:1px;">
        Newsletter-Entwurf bereit
      </p>
      <h2 style="margin:0 0 20px 0;font-size:22px;color:#2A2520;">
        {subject_line}
      </h2>
      <div style="border-top:1px solid #D8D4CE;margin:0 0 20px 0;"></div>
      {_section("Vorschautext", preview)}
      {_section("Whisky des Monats", wotm_name)}
      {_section("Artikel", f"{art_count} Teasers enthalten")}
      {_section("Erstellt", created)}
      <div style="border-top:1px solid #D8D4CE;margin:20px 0;"></div>
      <p style="margin:0 0 8px 0;font-size:14px;color:#4A4440;">
        <strong>Naechste Schritte:</strong>
      </p>
      {_cmd_box("python newsletter_generator.py --preview")}
      <p style="margin:4px 0 0 0;font-size:13px;color:#8A8480;">
        Dann nach Pruefung freigeben und versenden:
      </p>
      {_cmd_box("python newsletter_generator.py --approve  &amp;&amp;  python newsletter_generator.py --send")}
    """

    text_body = (
        f"Newsletter-Entwurf bereit: {subject_line}\n\n"
        f"Vorschau: {preview}\n"
        f"WOTM: {wotm_name}\n"
        f"Erstellt: {created}\n\n"
        f"Zum Freigeben:\n"
        f"  python newsletter_generator.py --preview\n"
        f"  python newsletter_generator.py --approve\n"
        f"  python newsletter_generator.py --send\n"
    )

    return send_notification(
        f"\u270d\ufe0f Newsletter-Entwurf bereit: {subject_line}",
        _base_html(f"Newsletter-Entwurf: {subject_line}", content_html),
        text_body,
    )


def notify_wotm_draft_ready(wotm_data):
    """
    Benachrichtigt wenn ein WOTM-Draft erstellt wurde.
    wotm_data: der draft-Eintrag aus wotm.json
    """
    name       = wotm_data.get("name", "Unbekannt")
    distillery = wotm_data.get("distillery", "-")
    region     = wotm_data.get("region", "-")
    month      = wotm_data.get("month", "-")
    tasting    = wotm_data.get("tasting", {})
    aroma      = tasting.get("aroma", "-")
    geschmack  = tasting.get("geschmack", "-")
    wertung    = tasting.get("wertung", "-")
    teaser     = wotm_data.get("newsletter_teaser", "-")

    content_html = f"""
      <p style="margin:0 0 6px 0;font-size:12px;color:#B8762E;
                text-transform:uppercase;letter-spacing:1px;">
        Whisky des Monats - Entwurf
      </p>
      <h2 style="margin:0 0 20px 0;font-size:22px;color:#2A2520;">
        {name}
      </h2>
      <div style="background-color:#F2EDE6;padding:16px 20px;margin:0 0 20px 0;">
        {_section("Monat", month)}
        {_section("Destillerie", distillery)}
        {_section("Region", region)}
        {_section("Wertung", f"{wertung}/100")}
      </div>
      <p style="margin:0 0 6px 0;font-size:13px;color:#B8762E;font-weight:bold;">
        Aroma:
      </p>
      <p style="margin:0 0 14px 0;font-size:14px;color:#4A4440;">{aroma}</p>
      <p style="margin:0 0 6px 0;font-size:13px;color:#B8762E;font-weight:bold;">
        Geschmack:
      </p>
      <p style="margin:0 0 14px 0;font-size:14px;color:#4A4440;">{geschmack}</p>
      <p style="margin:0 0 6px 0;font-size:13px;color:#B8762E;font-weight:bold;">
        Newsletter-Teaser:
      </p>
      <p style="margin:0 0 20px 0;font-size:14px;color:#4A4440;font-style:italic;">
        "{teaser}"
      </p>
      <div style="border-top:1px solid #D8D4CE;margin:20px 0;"></div>
      <p style="margin:0 0 8px 0;font-size:14px;color:#4A4440;">
        <strong>Zum Freigeben:</strong>
      </p>
      {_cmd_box("python wotm_generator.py --approve")}
      <p style="margin:4px 0 0 0;font-size:13px;color:#8A8480;">
        Oder verwerfen mit: python wotm_generator.py --reject
      </p>
    """

    text_body = (
        f"WOTM-Entwurf: {name}\n\n"
        f"Monat: {month} | Region: {region} | Wertung: {wertung}/100\n\n"
        f"Aroma: {aroma}\n"
        f"Geschmack: {geschmack}\n\n"
        f"Zum Freigeben:\n"
        f"  python wotm_generator.py --approve\n"
        f"  python wotm_generator.py --reject\n"
    )

    return send_notification(
        f"\U0001f943 Whisky des Monats Entwurf: {name}",
        _base_html(f"WOTM Entwurf: {name}", content_html),
        text_body,
    )


def notify_newsletter_sent(campaign_id, subject, recipient_count=None):
    """
    Bestaetigung nach erfolgreichem Newsletter-Versand.
    """
    sent_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    rcpt_text = f"{recipient_count} Empfaenger" if recipient_count else "Alle Abonnenten"

    content_html = f"""
      <p style="margin:0 0 6px 0;font-size:12px;color:#B8762E;
                text-transform:uppercase;letter-spacing:1px;">
        Newsletter erfolgreich versendet
      </p>
      <h2 style="margin:0 0 20px 0;font-size:22px;color:#2A2520;">
        {subject}
      </h2>
      <div style="background-color:#F2EDE6;padding:16px 20px;margin:0 0 20px 0;">
        {_section("Kampagne", campaign_id)}
        {_section("Empfaenger", rcpt_text)}
        {_section("Versendet", sent_at)}
      </div>
      <p style="margin:0;font-size:14px;color:#4A4440;">
        Die Aufruf-Statistiken sind in ca. 24 Stunden im Mailchimp-Dashboard verfuegbar.
      </p>
    """

    text_body = (
        f"Newsletter versendet: {subject}\n\n"
        f"Kampagne: {campaign_id}\n"
        f"Empfaenger: {rcpt_text}\n"
        f"Versendet: {sent_at}\n"
    )

    return send_notification(
        f"\u2705 Newsletter versendet: {subject}",
        _base_html(f"Newsletter versendet: {subject}", content_html),
        text_body,
    )


def notify_monthly_reminder():
    """
    Monatliche Erinnerung wenn kein WOTM fuer diesen Monat gesetzt ist.
    """
    monate = {
        1: "Januar", 2: "Februar", 3: "Maerz", 4: "April",
        5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
        9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
    }
    now = datetime.now()
    month_label = f"{monate[now.month]} {now.year}"

    content_html = f"""
      <p style="margin:0 0 6px 0;font-size:12px;color:#B8762E;
                text-transform:uppercase;letter-spacing:1px;">
        Monatliche Erinnerung
      </p>
      <h2 style="margin:0 0 16px 0;font-size:22px;color:#2A2520;">
        Whisky des Monats fuer {month_label} noch nicht gesetzt
      </h2>
      <p style="margin:0 0 20px 0;font-size:15px;color:#4A4440;line-height:1.7;">
        Das automatische Newsletter-System hat festgestellt, dass fuer
        <strong>{month_label}</strong> noch kein Whisky des Monats
        ausgewaehlt und freigegeben wurde.
      </p>
      <p style="margin:0 0 8px 0;font-size:14px;color:#4A4440;">
        <strong>Neuen WOTM erstellen:</strong>
      </p>
      {_cmd_box('python wotm_generator.py --new "Whisky Name" --region Islay')}
      <p style="margin:8px 0;font-size:13px;color:#8A8480;">
        Dann freigeben:
      </p>
      {_cmd_box("python wotm_generator.py --approve")}
      <p style="margin:12px 0 0 0;font-size:13px;color:#8A8480;">
        Danach den Newsletter erstellen:
      </p>
      {_cmd_box("python newsletter_generator.py --auto-draft")}
    """

    text_body = (
        f"Erinnerung: Whisky des Monats fuer {month_label} noch nicht gesetzt.\n\n"
        f"Bitte WOTM erstellen:\n"
        f"  python wotm_generator.py --new 'Whisky Name' --region Islay\n"
        f"  python wotm_generator.py --approve\n"
        f"  python newsletter_generator.py --auto-draft\n"
    )

    return send_notification(
        f"\u23f0 Erinnerung: Whisky des Monats fuer {month_label} noch nicht gesetzt",
        _base_html(f"Erinnerung: WOTM {month_label}", content_html),
        text_body,
    )


# ============================================================
# Neue Entwürfe Benachrichtigung (Brevo Transactional API)
# ============================================================

def notify_new_drafts(articles_data):
    """
    Sendet eine E-Mail-Benachrichtigung wenn neue Artikel-Entwürfe generiert wurden.
    Nutzt die Brevo Transactional API (nicht SMTP).
    Empfänger: rosenhefter@gmail.com
    """
    import os
    import urllib.request as _urllib
    import json as _json_mod
    from datetime import date as _date, timedelta

    brevo_key = os.environ.get("BREVO_API_KEY", "")
    if not brevo_key:
        # Aus .env laden
        env_path = PROJECT_DIR / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("BREVO_API_KEY="):
                        brevo_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break

    if not brevo_key:
        print("  [Notifier] BREVO_API_KEY nicht gefunden – E-Mail übersprungen.")
        return False

    recipient = "rosenhefter@gmail.com"
    dashboard_url = "https://www.whisky-reise.com/admin"
    count = len(articles_data)

    # Nächste Mittwoch + Samstag berechnen
    today = _date.today()
    days_to_wed = (2 - today.weekday()) % 7
    days_to_sat = (5 - today.weekday()) % 7
    if days_to_wed == 0:
        days_to_wed = 7
    if days_to_sat == 0:
        days_to_sat = 7
    next_wed = (today + timedelta(days=days_to_wed)).strftime("%d.%m.%Y")
    next_sat = (today + timedelta(days=days_to_sat)).strftime("%d.%m.%Y")

    # Artikel-Blöcke für E-Mail
    article_blocks_html = ""
    article_blocks_text = ""
    for i, art in enumerate(articles_data, 1):
        title = art.get("title", "Ohne Titel")
        category = art.get("category", "–")
        teaser = art.get("meta", {}).get("teaser", "")
        html_content = art.get("html_content", "")
        words = len(html_content.split()) if html_content else 0

        article_blocks_html += f"""
        <div style="background:#F2EDE6;padding:16px 20px;margin:0 0 16px 0;border-left:4px solid #C8963E;">
          <p style="margin:0 0 4px 0;font-size:12px;color:#B8762E;text-transform:uppercase;letter-spacing:1px;">
            Entwurf {i} &bull; {category} &bull; ~{words} Wörter
          </p>
          <p style="margin:0 0 8px 0;font-size:17px;font-weight:bold;color:#2A2520;">{title}</p>
          <p style="margin:0;font-size:14px;color:#4A4440;font-style:italic;">{teaser}</p>
        </div>"""
        article_blocks_text += f"\n{i}. {title}\n   Kategorie: {category} | ~{words} Wörter\n   {teaser}\n"

    html_body = f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"><title>Neue Artikel-Entwürfe</title></head>
<body style="margin:0;padding:0;background-color:#EDE9E3;font-family:Georgia,'Times New Roman',serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color:#EDE9E3;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" border="0"
             style="max-width:600px;width:100%;background-color:#FAF8F4;">

        <tr>
          <td style="background-color:#2A2520;padding:24px 40px;text-align:center;">
            <p style="margin:0 0 4px 0;font-size:11px;color:#C8963E;text-transform:uppercase;letter-spacing:3px;">
              Redaktionssystem
            </p>
            <h1 style="margin:0;font-size:22px;font-weight:bold;color:#FAF8F4;letter-spacing:2px;">
              WHISKY MAGAZIN
            </h1>
          </td>
        </tr>

        <tr>
          <td style="padding:32px 40px;">
            <p style="margin:0 0 8px 0;font-size:12px;color:#B8762E;text-transform:uppercase;letter-spacing:1px;">
              Neue Entwürfe bereit
            </p>
            <h2 style="margin:0 0 20px 0;font-size:22px;color:#2A2520;">
              {count} neue Artikel warten auf deine Freigabe
            </h2>
            <p style="margin:0 0 24px 0;font-size:15px;color:#4A4440;line-height:1.7;">
              Hallo Steffen und Elmar,<br><br>
              diese Woche wurden automatisch <strong>{count} neue Artikel</strong> erstellt.
              Bitte prüft die Entwürfe im Dashboard und gebt sie frei:
            </p>

            {article_blocks_html}

            <div style="margin:24px 0;padding:20px;background:#2A2520;text-align:center;border-radius:4px;">
              <a href="{dashboard_url}"
                 style="color:#C8963E;font-size:16px;font-weight:bold;text-decoration:none;letter-spacing:1px;">
                &#9654; Zum Dashboard — Vorschau, Bearbeiten & Freigeben
              </a>
              <p style="margin:8px 0 0 0;font-size:12px;color:#8A8480;">
                {dashboard_url}
              </p>
            </div>

            <div style="border-top:1px solid #D8D4CE;margin:24px 0;padding-top:20px;">
              <p style="margin:0 0 6px 0;font-size:14px;color:#4A4440;">
                <strong>Geplante Veröffentlichungen:</strong>
              </p>
              <p style="margin:0 0 4px 0;font-size:14px;color:#4A4440;">
                &bull; Mittwoch, {next_wed} um 10:00 Uhr
              </p>
              <p style="margin:0;font-size:14px;color:#4A4440;">
                &bull; Samstag, {next_sat} um 10:00 Uhr
              </p>
            </div>
          </td>
        </tr>

        <tr>
          <td style="background-color:#F2EDE6;padding:16px 40px;text-align:center;border-top:3px solid #C8963E;">
            <p style="margin:0;font-size:11px;color:#8A8480;">
              Whisky Magazin Redaktionssystem &bull; {datetime.now().strftime("%d.%m.%Y %H:%M")}
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

    text_body = (
        f"Hallo Steffen und Elmar,\n\n"
        f"{count} neue Artikel-Entwürfe wurden erstellt und warten auf Freigabe:\n"
        f"{article_blocks_text}\n"
        f"Dashboard: {dashboard_url}\n\n"
        f"Geplante Veröffentlichungen:\n"
        f"  Mittwoch, {next_wed} um 10:00 Uhr\n"
        f"  Samstag, {next_sat} um 10:00 Uhr\n"
    )

    payload = {
        "sender": {"name": "Whisky Magazin", "email": "whisky-news@whisky-reise.com"},
        "to": [{"email": recipient, "name": "Steffen"}],
        "subject": f"📝 {count} neue Whisky-Artikel warten auf Freigabe",
        "htmlContent": html_body,
        "textContent": text_body,
    }

    try:
        body = _json_mod.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = _urllib.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=body,
            headers={
                "api-key": brevo_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with _urllib.urlopen(req, timeout=15) as resp:
            status = resp.status
        if status in (200, 201):
            print(f"  [Notifier] E-Mail gesendet an {recipient}")
            return True
        else:
            print(f"  [Notifier] Fehler HTTP {status}")
            return False
    except Exception as exc:
        print(f"  [Notifier] Anfrage-Fehler: {exc}")
        return False


# ============================================================
# Test-Funktion
# ============================================================

def test_notifications():
    """Sendet eine Test-E-Mail zur Ueberpruefung der Konfiguration."""
    print_box([
        "NOTIFIER - Test",
        "",
        "Sendet Test-E-Mail an whisky-news@whisky-reise.com",
    ])

    notif = load_notif_config()
    if not notif:
        print("  FEHLER: Benachrichtigungen nicht konfiguriert oder deaktiviert.")
        print()
        print("  Bitte in config.json eintragen:")
        print('  "notifications": {')
        print('    "email": "whisky-news@whisky-reise.com",')
        print('    "smtp_sender": "dein-sender@gmail.com",')
        print('    "smtp_app_password": "xxxx xxxx xxxx xxxx",')
        print('    "enabled": true')
        print("  }")
        print()
        return False

    content_html = """
      <p style="margin:0 0 6px 0;font-size:12px;color:#B8762E;
                text-transform:uppercase;letter-spacing:1px;">
        Systemtest
      </p>
      <h2 style="margin:0 0 16px 0;font-size:22px;color:#2A2520;">
        E-Mail Benachrichtigungen funktionieren!
      </h2>
      <p style="margin:0;font-size:15px;color:#4A4440;line-height:1.7;">
        Das Whisky Magazin Redaktionssystem ist korrekt konfiguriert
        und kann automatisch Benachrichtigungen versenden.
      </p>
    """

    result = send_notification(
        "\U0001f943 Whisky Magazin - Test Benachrichtigung",
        _base_html("Test-Benachrichtigung", content_html),
        "Whisky Magazin Redaktionssystem - Testmail erfolgreich!",
    )

    if result:
        print_box(["Test-E-Mail erfolgreich gesendet!"])
    else:
        print_box(["Test-E-Mail fehlgeschlagen - Bitte config.json pruefen."])

    return result


# ============================================================
# Direktaufruf: Test
# ============================================================

if __name__ == "__main__":
    test_notifications()
