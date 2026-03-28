#!/usr/bin/env python3
"""
=============================================================
  WHISKY MAGAZIN - Newsletter Generator
=============================================================

Erstellt und versendet den monatlichen Newsletter via
OpenAI (Inhalt) und Mailchimp (Versand).

Nutzung:
  python newsletter_generator.py --draft       -> Entwurf erstellen
  python newsletter_generator.py --preview     -> Im Browser anzeigen
  python newsletter_generator.py --approve     -> Freigeben
  python newsletter_generator.py --send        -> Via Mailchimp senden
  python newsletter_generator.py --history     -> Versandverlauf
  python newsletter_generator.py --auto-draft  -> Vollautomatisch (Scheduler)
=============================================================
"""

import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import argparse
import base64
import json
import tempfile
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path

try:
    from notifier import (
        notify_newsletter_draft_ready,
        notify_newsletter_sent,
        notify_monthly_reminder,
    )
    _NOTIFIER_AVAILABLE = True
except ImportError:
    _NOTIFIER_AVAILABLE = False

PROJECT_DIR   = Path(__file__).parent
ARTICLES_DIR  = PROJECT_DIR / "articles"
DATA_DIR      = PROJECT_DIR / "data"
CONFIG_PATH   = PROJECT_DIR / "config.json"
DRAFT_PATH    = DATA_DIR / "newsletter_draft.json"
HISTORY_PATH  = DATA_DIR / "newsletter_history.json"
WOTM_PATH     = DATA_DIR / "wotm.json"


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


def load_config():
    """Laedt und validiert config.json."""
    if not CONFIG_PATH.exists():
        print("  FEHLER: config.json nicht gefunden!")
        print("  Bitte zuerst Setup ausfuehren.")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_json_file(path, default=None):
    """Laedt eine JSON-Datei oder gibt den Standardwert zurueck."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json_file(path, data):
    """Speichert Daten als JSON-Datei."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def mailchimp_request(method, endpoint, api_key, server_prefix, body=None):
    """
    Fuehrt einen Mailchimp API-Request durch (Basic Auth).
    method: 'GET', 'POST', 'PUT'
    endpoint: z.B. '/campaigns'
    """
    url = f"https://{server_prefix}.api.mailchimp.com/3.0{endpoint}"
    credentials = f"anystring:{api_key}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Basic {encoded}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        try:
            err = json.loads(body_text)
            raise RuntimeError(f"Mailchimp API Fehler {e.code}: {err.get('detail', body_text)}")
        except json.JSONDecodeError:
            raise RuntimeError(f"Mailchimp API Fehler {e.code}: {body_text[:200]}")


def openai_request(prompt_system, prompt_user, api_key, model="gpt-4o",
                   temperature=0.7, max_tokens=2500):
    """Sendet einen Chat-Request an die OpenAI API."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user",   "content": prompt_user},
        ],
        "response_format": {"type": "json_object"},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI API Fehler {e.code}: {body[:300]}")


# ============================================================
# Newsletter HTML Template
# ============================================================

def build_html(newsletter_data):
    """
    Baut das HTML-Email aus den Newsletter-Daten.
    Inline CSS fuer maximale E-Mail-Client-Kompatibilitaet.
    Farben: Copper #B8762E, Cream #FAF8F4, Dark #2A2520
    """
    subject      = newsletter_data.get("subject", "Whisky Magazin Newsletter")
    preview_text = newsletter_data.get("preview_text", "")
    greeting     = newsletter_data.get("editor_greeting", "")
    wotm         = newsletter_data.get("wotm_section", {})
    articles     = newsletter_data.get("article_teasers", [])
    reise_tipp   = newsletter_data.get("reise_tipp", "")
    closing      = newsletter_data.get("closing", "Slainte Mhath, Steffen & Elmar")

    # Artikel-Teasers als HTML
    article_blocks = ""
    for i, art in enumerate(articles[:3]):
        border_top = "border-top: 1px solid #E8E4DE;" if i > 0 else ""
        article_blocks += f"""
        <tr>
          <td style="padding: 20px 0; {border_top}">
            <p style="margin: 0 0 6px 0; font-size: 13px; color: #B8762E;
                      text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">
              Aus dem Magazin
            </p>
            <p style="margin: 0 0 8px 0; font-size: 18px; font-weight: bold;
                      color: #2A2520; font-family: Georgia, 'Times New Roman', serif;">
              {art.get('title', '')}
            </p>
            <p style="margin: 0; font-size: 15px; color: #4A4440; line-height: 1.6;">
              {art.get('teaser', '')}
            </p>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <title>{subject}</title>
  <!--[if mso]><style>body {{ font-family: Georgia, serif; }}</style><![endif]-->
</head>
<body style="margin: 0; padding: 0; background-color: #EDE9E3;
             font-family: Georgia, 'Times New Roman', serif;">

  <!-- Preheader (unsichtbar, erscheint in Postfach-Vorschau) -->
  <div style="display: none; max-height: 0; overflow: hidden; font-size: 1px; color: #EDE9E3;">
    {preview_text}&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;&#847;&zwnj;
  </div>

  <!-- Hauptcontainer -->
  <table width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background-color: #EDE9E3; padding: 30px 0;">
    <tr>
      <td align="center">

        <!-- Email-Box (max 640px) -->
        <table width="640" cellpadding="0" cellspacing="0" border="0"
               style="max-width: 640px; width: 100%; background-color: #FAF8F4;">

          <!-- ===== HEADER ===== -->
          <tr>
            <td style="padding: 40px 40px 0 40px; text-align: center;">
              <p style="margin: 0 0 4px 0; font-size: 11px; color: #B8762E;
                        text-transform: uppercase; letter-spacing: 3px;">
                Monatlicher Newsletter
              </p>
              <h1 style="margin: 0; font-size: 32px; font-weight: bold; color: #2A2520;
                         font-family: Georgia, 'Times New Roman', serif;
                         letter-spacing: 2px;">
                WHISKY MAGAZIN
              </h1>
              <!-- Kupfer-Unterstrich -->
              <div style="width: 60px; height: 3px; background-color: #B8762E;
                          margin: 12px auto 0 auto;"></div>
            </td>
          </tr>

          <!-- ===== DATUM ===== -->
          <tr>
            <td style="padding: 12px 40px 30px 40px; text-align: center;">
              <p style="margin: 0; font-size: 12px; color: #8A8480; font-style: italic;">
                {datetime.now().strftime("%B %Y")}
              </p>
            </td>
          </tr>

          <!-- ===== TRENNLINIE ===== -->
          <tr>
            <td style="padding: 0 40px;">
              <div style="border-top: 1px solid #D8D4CE;"></div>
            </td>
          </tr>

          <!-- ===== EDITORIAL GREETING ===== -->
          <tr>
            <td style="padding: 30px 40px;">
              <p style="margin: 0 0 8px 0; font-size: 13px; color: #B8762E;
                        text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">
                Von der Redaktion
              </p>
              <div style="font-size: 16px; color: #2A2520; line-height: 1.75;">
                {greeting.replace(chr(10), '<br>')}
              </div>
            </td>
          </tr>

          <!-- ===== TRENNLINIE ===== -->
          <tr>
            <td style="padding: 0 40px;">
              <div style="border-top: 1px solid #D8D4CE;"></div>
            </td>
          </tr>

          <!-- ===== WHISKY DES MONATS ===== -->
          <tr>
            <td style="padding: 30px 40px; background-color: #F2EDE6;">
              <p style="margin: 0 0 6px 0; font-size: 11px; color: #B8762E;
                        text-transform: uppercase; letter-spacing: 2px; font-weight: bold;">
                Whisky des Monats
              </p>
              <h2 style="margin: 0 0 12px 0; font-size: 24px; color: #2A2520;
                         font-family: Georgia, 'Times New Roman', serif;">
                {wotm.get('headline', '')}
              </h2>
              <p style="margin: 0 0 16px 0; font-size: 15px; color: #4A4440; line-height: 1.7;">
                {wotm.get('tasting_notes', '')}
              </p>
              <p style="margin: 0; font-size: 14px; color: #B8762E; font-style: italic;">
                {wotm.get('cta_text', 'Mehr erfahren auf whisky.reise &rarr;')}
              </p>
            </td>
          </tr>

          <!-- ===== TRENNLINIE ===== -->
          <tr>
            <td style="padding: 0 40px;">
              <div style="border-top: 1px solid #D8D4CE;"></div>
            </td>
          </tr>

          <!-- ===== ARTIKEL-TEASERS ===== -->
          <tr>
            <td style="padding: 30px 40px 10px 40px;">
              <p style="margin: 0 0 20px 0; font-size: 13px; color: #B8762E;
                        text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">
                Aktuelle Artikel
              </p>
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                {article_blocks}
              </table>
            </td>
          </tr>

          <!-- ===== TRENNLINIE ===== -->
          <tr>
            <td style="padding: 0 40px;">
              <div style="border-top: 1px solid #D8D4CE;"></div>
            </td>
          </tr>

          <!-- ===== REISE-TIPP ===== -->
          <tr>
            <td style="padding: 30px 40px;">
              <p style="margin: 0 0 6px 0; font-size: 13px; color: #B8762E;
                        text-transform: uppercase; letter-spacing: 1px; font-weight: bold;">
                Reise-Tipp des Monats
              </p>
              <p style="margin: 0; font-size: 15px; color: #4A4440; line-height: 1.75;">
                {reise_tipp}
              </p>
            </td>
          </tr>

          <!-- ===== TRENNLINIE ===== -->
          <tr>
            <td style="padding: 0 40px;">
              <div style="border-top: 1px solid #D8D4CE;"></div>
            </td>
          </tr>

          <!-- ===== ABSCHLUSS ===== -->
          <tr>
            <td style="padding: 30px 40px 40px 40px;">
              <p style="margin: 0; font-size: 17px; color: #2A2520; font-style: italic;
                        font-family: Georgia, 'Times New Roman', serif;">
                {closing}
              </p>
            </td>
          </tr>

          <!-- ===== FOOTER ===== -->
          <tr>
            <td style="background-color: #2A2520; padding: 24px 40px; text-align: center;">
              <p style="margin: 0 0 8px 0; font-size: 14px; color: #FAF8F4;
                        font-family: Georgia, 'Times New Roman', serif; letter-spacing: 1px;">
                WHISKY MAGAZIN
              </p>
              <p style="margin: 0 0 12px 0; font-size: 12px; color: #9A948E;">
                Dein Guide fuer Whisky, Destillerien &amp; Reisen
              </p>
              <p style="margin: 0; font-size: 11px; color: #7A7470;">
                <a href="*|UNSUB|*" style="color: #B8762E; text-decoration: none;">
                  Abmelden
                </a>
                &nbsp;&bull;&nbsp;
                <a href="https://whisky.reise" style="color: #7A7470; text-decoration: none;">
                  whisky.reise
                </a>
              </p>
            </td>
          </tr>

        </table>
        <!-- Ende Email-Box -->

      </td>
    </tr>
  </table>

</body>
</html>"""

    return html


# ============================================================
# --draft: Newsletter-Entwurf erstellen
# ============================================================

def cmd_draft(config):
    """Generiert einen Newsletter-Entwurf via OpenAI."""
    print("\n  Erstelle Newsletter-Entwurf...\n")

    openai_cfg = config.get("openai", {})
    api_key    = openai_cfg.get("api_key", "")
    model      = openai_cfg.get("model", "gpt-4o")

    if not api_key or api_key.startswith("sk-DEIN"):
        print("  FEHLER: OpenAI API-Key fehlt in config.json!")
        sys.exit(1)

    # 1. Whisky des Monats laden
    wotm = load_json_file(WOTM_PATH, default={})
    wotm_text = ""
    if wotm:
        wotm_text = (
            f"Whisky des Monats: {wotm.get('name', 'unbekannt')}, "
            f"Destillerie: {wotm.get('distillery', '')}, "
            f"Region: {wotm.get('region', '')}, "
            f"Tasting Notes: {wotm.get('tasting_notes', '')}"
        )
    else:
        wotm_text = "Kein WOTM definiert - bitte einen passenden Whisky auswaehlen."

    # 2. Letzte 3 Artikel laden (neuste zuerst)
    article_summaries = ""
    if ARTICLES_DIR.exists():
        article_files = sorted(
            ARTICLES_DIR.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:3]

        for af in article_files:
            try:
                art = load_json_file(af, default={})
                title = art.get("title") or art.get("meta", {}).get("title", af.stem)
                intro = ""
                # Intro aus verschiedenen moeglichen Strukturen lesen
                if "sections" in art and art["sections"]:
                    intro = art["sections"][0].get("content", "")[:300]
                elif "content" in art:
                    intro = str(art["content"])[:300]
                article_summaries += f"- {title}: {intro}...\n"
            except Exception:
                article_summaries += f"- {af.stem}\n"

    if not article_summaries:
        article_summaries = "Noch keine Artikel vorhanden."

    # 3. Versandverlauf laden (zur Vermeidung von Wiederholungen)
    history = load_json_file(HISTORY_PATH, default={"sent": [], "draft": None})
    recent_subjects = [e.get("subject", "") for e in history.get("sent", [])[-5:]]
    history_hint = ""
    if recent_subjects:
        history_hint = (
            "Bitte NICHT aehnliche Themen wie diese letzten Newsletter verwenden:\n"
            + "\n".join(f"- {s}" for s in recent_subjects)
        )

    # 4. OpenAI-Prompt aufbauen
    system_prompt = (
        "Du bist Steffen vom Whisky Magazin. Du schreibst einen monatlichen Newsletter "
        "auf Deutsch fuer Whisky-Enthusiasten und Schottland-Reisende. "
        "Dein Ton: persoenlich, buddy-artig, nicht snobbig, enthusiastisch. "
        "Generiere jetzt eine komplette Newsletter-Ausgabe als JSON mit diesen Feldern:\n"
        "- subject: Betreffzeile (Deutsch, max 60 Zeichen, catchy, mit Emoji ok)\n"
        "- preview_text: Vorschautext (Deutsch, max 90 Zeichen)\n"
        "- editor_greeting: Redaktionsgruss (beginnt mit 'Moin,', dann 3-4 persoenliche "
        "  Saetze ueber die aktuelle Jahreszeit und/oder Schottland, keine Links)\n"
        "- wotm_section: Objekt mit:\n"
        "    headline: Schlagzeile fuer den WOTM (inkl. Whisky-Name)\n"
        "    tasting_notes: 2-3 Saetze Tasting-Notes als Teaser\n"
        "    cta_text: Call-to-Action (z.B. 'Jetzt mehr erfahren auf whisky.reise')\n"
        "- article_teasers: Array mit 3 Objekten, je:\n"
        "    title: Artikel-Titel\n"
        "    teaser: 2 Saetze als Teaser-Text\n"
        "- reise_tipp: 1 Absatz Reise-Tipp (aktuelle Saison relevant, max 100 Woerter)\n"
        "- closing: Abschlussformel (z.B. 'Slainthe Mhath, Steffen & Elmar')\n"
        "Antworte NUR mit dem JSON-Objekt, kein Markdown drum herum."
    )

    user_prompt = (
        f"Aktuelle Daten fuer den Newsletter:\n\n"
        f"{wotm_text}\n\n"
        f"Aktuelle Artikel im Magazin:\n{article_summaries}\n\n"
        f"{history_hint}\n\n"
        f"Datum: {datetime.now().strftime('%B %Y')}\n"
        f"Jahreszeit: {_current_season()}\n\n"
        f"Bitte erstelle jetzt den kompletten Newsletter als JSON."
    )

    print("  Rufe OpenAI API auf...")
    try:
        newsletter_data = openai_request(
            system_prompt, user_prompt,
            api_key=api_key,
            model=model,
            temperature=0.75,
            max_tokens=2500,
        )
    except RuntimeError as e:
        print(f"\n  FEHLER: {e}")
        sys.exit(1)

    print("  Inhalte generiert.")

    # 5. HTML aufbauen
    print("  Baue HTML-Template...")
    html_content = build_html(newsletter_data)

    # 6. Entwurf speichern
    draft = {
        "subject":      newsletter_data.get("subject", "Whisky Magazin Newsletter"),
        "preview_text": newsletter_data.get("preview_text", ""),
        "html_content": html_content,
        "content_data": newsletter_data,
        "created_at":   datetime.now().isoformat(),
        "approved":     False,
    }
    save_json_file(DRAFT_PATH, draft)

    print_box([
        "Entwurf erstellt!",
        "",
        f"Betreff: {draft['subject'][:45]}...",
        "",
        "Naechste Schritte:",
        "  --preview   Vorschau im Browser",
        "  --approve   Freigeben",
        "  --send      Versenden",
    ])

    # Benachrichtigung versenden
    if _NOTIFIER_AVAILABLE:
        notify_newsletter_draft_ready(draft)

    return draft


# ============================================================
# --auto-draft: Vollautomatischer Entwurfs-Modus
# ============================================================

def cmd_auto_draft(config):
    """
    Vollautomatischer Modus fuer den Scheduler:
    - Prueft ob WOTM fuer diesen Monat gesetzt und genehmigt ist
    - Falls nicht: sendet Erinnerung und beendet
    - Falls ja: erstellt Newsletter-Entwurf und benachrichtigt
    """
    print("\n  Pruefe Whisky des Monats fuer diesen Monat...")

    now = datetime.now()
    month_id = now.strftime("%Y-%m")

    wotm_data = load_json_file(WOTM_PATH, default={})
    current   = wotm_data.get("current", {})

    # WOTM-Monat ermitteln (Format: "Maerz 2026" oder ID "2026-03")
    wotm_month  = current.get("month", "")
    wotm_id     = current.get("id", "")
    wotm_approved = current.get("approved", False)

    # Pruefe ob WOTM fuer aktuellen Monat gesetzt und genehmigt
    month_match = (
        month_id in wotm_id
        or now.strftime("%Y") in wotm_month and str(now.month) in wotm_id
    )

    if not current or not wotm_approved or not month_match:
        print("  WOTM fuer diesen Monat noch nicht gesetzt.")
        if _NOTIFIER_AVAILABLE:
            notify_monthly_reminder()
            print("  Erinnerung per E-Mail gesendet.")
        else:
            print("  [Hinweis] Notifier nicht verfuegbar - keine E-Mail gesendet.")
        print()
        print("  Bitte WOTM setzen:")
        print("    python wotm_generator.py --new 'Whisky Name' --region Islay")
        print("    python wotm_generator.py --approve")
        print("    python newsletter_generator.py --auto-draft")
        print()
        sys.exit(0)

    print(f"  WOTM gefunden: {current.get('name', '?')} ({wotm_month})")
    print("  Erstelle Newsletter-Entwurf...\n")

    draft = cmd_draft(config)

    if draft:
        print_box([
            "Auto-Draft abgeschlossen!",
            "",
            "Entwurf erstellt & Benachrichtigung gesendet.",
            "",
            "Naechste Schritte:",
            "  --preview   Vorschau pruefen",
            "  --approve   Freigeben",
            "  --send      Versenden",
        ])
    else:
        print("  Entwurf konnte nicht erstellt werden.")


def _current_season():
    """Gibt die aktuelle Jahreszeit auf Deutsch zurueck."""
    month = datetime.now().month
    if month in (12, 1, 2):
        return "Winter"
    elif month in (3, 4, 5):
        return "Fruehjahr"
    elif month in (6, 7, 8):
        return "Sommer"
    else:
        return "Herbst"


# ============================================================
# --preview: Vorschau im Browser
# ============================================================

def cmd_preview():
    """Oeffnet den aktuellen Entwurf im Browser."""
    draft = load_json_file(DRAFT_PATH)
    if not draft:
        print("\n  FEHLER: Kein Entwurf gefunden.")
        print("  Bitte zuerst 'python newsletter_generator.py --draft' ausfuehren.\n")
        sys.exit(1)

    html = draft.get("html_content", "")
    subject = draft.get("subject", "Newsletter Vorschau")

    # HTML in temporaere Datei schreiben und im Browser oeffnen
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False,
        encoding="utf-8", prefix="whisky_newsletter_preview_"
    ) as tmp:
        tmp.write(html)
        tmp_path = tmp.name

    print(f"\n  Oeffne Vorschau: {tmp_path}")
    print(f"  Betreff: {subject}\n")
    webbrowser.open(f"file:///{tmp_path.replace(os.sep, '/')}")


# ============================================================
# --approve: Newsletter freigeben
# ============================================================

def cmd_approve():
    """Setzt approved = true im Entwurf."""
    draft = load_json_file(DRAFT_PATH)
    if not draft:
        print("\n  FEHLER: Kein Entwurf gefunden.\n")
        sys.exit(1)

    if draft.get("approved"):
        print("\n  Newsletter ist bereits freigegeben.\n")
        return

    draft["approved"] = True
    draft["approved_at"] = datetime.now().isoformat()
    save_json_file(DRAFT_PATH, draft)

    print_box([
        "Newsletter freigegeben!",
        "",
        f"Betreff: {draft['subject'][:45]}",
        "",
        "Jetzt versenden mit:",
        "  python newsletter_generator.py --send",
    ])


# ============================================================
# --send: Via Mailchimp versenden
# ============================================================

def cmd_send(config):
    """Erstellt eine Mailchimp-Kampagne und sendet sie."""

    # 1. Entwurf pruefen
    draft = load_json_file(DRAFT_PATH)
    if not draft:
        print("\n  FEHLER: Kein Entwurf gefunden.")
        print("  Bitte zuerst '--draft' ausfuehren.\n")
        sys.exit(1)

    if not draft.get("approved"):
        print("\n  FEHLER: Newsletter noch nicht freigegeben!")
        print("  Bitte zuerst '--approve' ausfuehren.\n")
        sys.exit(1)

    # 2. Mailchimp-Konfiguration pruefen
    mc = config.get("mailchimp", {})
    if not mc.get("configured"):
        print("\n  FEHLER: Mailchimp nicht konfiguriert!")
        print("  Bitte zuerst 'python mailchimp_setup.py' ausfuehren.\n")
        sys.exit(1)

    api_key       = mc["api_key"]
    server_prefix = mc["server_prefix"]
    audience_id   = mc["audience_id"]
    from_name     = mc.get("from_name", "Steffen & Elmar")
    from_email    = mc["from_email"]
    reply_to      = mc.get("reply_to", from_email)
    subject       = draft["subject"]
    html_content  = draft["html_content"]
    preview_text  = draft.get("preview_text", "")

    print(f"\n  Sende Newsletter via Mailchimp...")
    print(f"  Betreff: {subject}")
    print(f"  Audience: {audience_id}")
    print()

    # 3. Kampagne erstellen
    print("  [1/3] Erstelle Kampagne...")
    campaign_body = {
        "type": "regular",
        "recipients": {
            "list_id": audience_id,
        },
        "settings": {
            "subject_line":   subject,
            "preview_text":   preview_text,
            "title":          f"Newsletter {datetime.now().strftime('%Y-%m')}",
            "from_name":      from_name,
            "reply_to":       reply_to,
        },
    }

    try:
        campaign = mailchimp_request(
            "POST", "/campaigns",
            api_key, server_prefix,
            body=campaign_body
        )
    except RuntimeError as e:
        print(f"\n  FEHLER beim Erstellen der Kampagne: {e}\n")
        sys.exit(1)

    campaign_id = campaign.get("id")
    print(f"  Kampagne erstellt: {campaign_id}")

    # 4. Kampagnen-Inhalt setzen
    print("  [2/3] Setze Inhalt...")
    content_body = {
        "html": html_content,
    }

    try:
        mailchimp_request(
            "PUT", f"/campaigns/{campaign_id}/content",
            api_key, server_prefix,
            body=content_body
        )
    except RuntimeError as e:
        print(f"\n  FEHLER beim Setzen des Inhalts: {e}\n")
        sys.exit(1)

    # 5. Kampagne senden
    print("  [3/3] Sende Newsletter...")
    try:
        mailchimp_request(
            "POST", f"/campaigns/{campaign_id}/actions/send",
            api_key, server_prefix
        )
    except RuntimeError as e:
        print(f"\n  FEHLER beim Senden: {e}\n")
        sys.exit(1)

    # 6. Verlauf aktualisieren
    sent_at = datetime.now().isoformat()
    history = load_json_file(HISTORY_PATH, default={"sent": [], "draft": None})

    history_entry = {
        "campaign_id": campaign_id,
        "subject":     subject,
        "sent_at":     sent_at,
        "audience_id": audience_id,
        "preview_text": preview_text,
    }
    history.setdefault("sent", []).append(history_entry)
    history["draft"] = None
    save_json_file(HISTORY_PATH, history)

    # 7. Entwurf loeschen
    if DRAFT_PATH.exists():
        DRAFT_PATH.unlink()

    print_box([
        "Newsletter erfolgreich gesendet!",
        "",
        f"Kampagne:  {campaign_id}",
        f"Betreff:   {subject[:40]}",
        f"Gesendet:  {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        "",
        "Aufruf-Statistiken in 24h in Mailchimp.",
    ])

    # Versandbestaetigung per E-Mail
    if _NOTIFIER_AVAILABLE:
        notify_newsletter_sent(campaign_id, subject)


# ============================================================
# --history: Versandverlauf anzeigen
# ============================================================

def cmd_history():
    """Zeigt den Newsletter-Versandverlauf an."""
    history = load_json_file(HISTORY_PATH, default={"sent": [], "draft": None})
    sent = history.get("sent", [])

    print()
    print("  +====================================================+")
    print("  |   NEWSLETTER-VERLAUF                               |")
    print("  +====================================================+")
    print()

    if not sent:
        print("  Noch keine Newsletter versendet.")
    else:
        print(f"  Insgesamt gesendet: {len(sent)}\n")
        for entry in reversed(sent):
            sent_at = entry.get("sent_at", "")
            if sent_at:
                try:
                    dt = datetime.fromisoformat(sent_at)
                    sent_at = dt.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    pass
            subject = entry.get("subject", "-")[:50]
            cid = entry.get("campaign_id", "-")
            print(f"  {sent_at}  |  {subject}")
            print(f"  Kampagne-ID: {cid}")
            print()

    # Aktuellen Entwurf anzeigen falls vorhanden
    draft = load_json_file(DRAFT_PATH)
    if draft:
        created = draft.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created)
            created = dt.strftime("%d.%m.%Y %H:%M")
        except Exception:
            pass
        approved = "JA" if draft.get("approved") else "NEIN"
        print(f"  Aktueller Entwurf: {draft.get('subject', '-')[:50]}")
        print(f"  Erstellt: {created}  |  Freigegeben: {approved}")
        print()


# ============================================================
# Eintrittspunkt
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Whisky Magazin - Newsletter Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--draft",      action="store_true", help="Newsletter-Entwurf erstellen")
    parser.add_argument("--preview",    action="store_true", help="Entwurf im Browser anzeigen")
    parser.add_argument("--approve",    action="store_true", help="Entwurf freigeben")
    parser.add_argument("--send",       action="store_true", help="Newsletter via Mailchimp senden")
    parser.add_argument("--history",    action="store_true", help="Versandverlauf anzeigen")
    parser.add_argument("--auto-draft", action="store_true", dest="auto_draft",
                        help="Vollautomatischer Modus fuer Scheduler (WOTM pruefen + Entwurf erstellen)")

    args = parser.parse_args()

    print()
    print("  +==========================================+")
    print("  |   WHISKY MAGAZIN - Newsletter             |")
    print("  +==========================================+")

    # Befehle, die keine Config benoetigen
    if args.preview:
        cmd_preview()
        return
    if args.history:
        cmd_history()
        return
    if args.approve:
        cmd_approve()
        return

    # Befehle, die Config benoetigen
    config = load_config()

    if args.draft:
        cmd_draft(config)
    elif args.send:
        cmd_send(config)
    elif args.auto_draft:
        cmd_auto_draft(config)
    else:
        print()
        print("  Nutzung:")
        print("    python newsletter_generator.py --draft       Entwurf erstellen")
        print("    python newsletter_generator.py --preview     Im Browser anzeigen")
        print("    python newsletter_generator.py --approve     Freigeben")
        print("    python newsletter_generator.py --send        Versenden")
        print("    python newsletter_generator.py --history     Versandverlauf")
        print("    python newsletter_generator.py --auto-draft  Automatisch (Scheduler)")
        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Abgebrochen.")
        sys.exit(0)
