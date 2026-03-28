#!/usr/bin/env python3
"""
=============================================================
  WHISKY DES MONATS - Generator & Manager
=============================================================

Verwaltet den Whisky des Monats (WOTM): Erstellt Drafts via
OpenAI GPT-4o, zeigt sie an, genehmigt oder verwirft sie
und triggert anschliessend den Site-Build.

Nutzung:
  python wotm_generator.py --show               -> Aktuellen WOTM anzeigen
  python wotm_generator.py --new "Ardbeg 10"   -> Neuen Draft via KI erstellen
  python wotm_generator.py --approve            -> Draft genehmigen & Site bauen
  python wotm_generator.py --reject             -> Draft verwerfen
  python wotm_generator.py --archiv             -> Alle archivierten WOTMs listen
  python wotm_generator.py --edit               -> wotm.json im Editor oeffnen
"""

import sys
import os

# Windows UTF-8 Fix - muss ganz am Anfang stehen
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import argparse
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from notifier import notify_wotm_draft_ready, notify_newsletter_sent
    _NOTIFIER_AVAILABLE = True
except ImportError:
    _NOTIFIER_AVAILABLE = False


# ============================================================
# Pfade & Konstanten
# ============================================================

PROJECT_DIR = Path(__file__).parent
WOTM_PATH   = PROJECT_DIR / "data" / "wotm.json"


# ============================================================
# Hilfsfunktionen: Ausgabe
# ============================================================

def p(text=""):
    """Gibt Text UTF-8-sicher auf der Konsole aus."""
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def box(title, lines, width=60):
    """Zeichnet eine ASCII-Box mit Titel und Inhalt."""
    border = "+" + "=" * (width - 2) + "+"
    p()
    p(border)
    p("|  " + title.ljust(width - 4) + "|")
    p("+" + "-" * (width - 2) + "+")
    for line in lines:
        # Lange Zeilen umbrechen
        while len(line) > width - 4:
            p("|  " + line[: width - 4] + "|")
            line = "   " + line[width - 4 :]
        p("|  " + line.ljust(width - 4) + "|")
    p(border)
    p()


def stars(wertung):
    """Gibt eine Sternchen-Leiste fuer die Wertung zurueck (0-100 -> 0-5 Sterne)."""
    filled = round(wertung / 20)
    return "[" + "*" * filled + "-" * (5 - filled) + "]"


# ============================================================
# Konfiguration laden
# ============================================================

def load_config():
    """Laedt config.json aus dem Projektverzeichnis."""
    config_path = PROJECT_DIR / "config.json"
    if not config_path.exists():
        # Fallback: eine Ebene hoeher suchen
        config_path = PROJECT_DIR.parent / "whisky-magazin" / "config.json"
    if not config_path.exists():
        p("  FEHLER: config.json nicht gefunden.")
        p("  Erwartet: " + str(PROJECT_DIR / "config.json"))
        sys.exit(1)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# WOTM-Datei laden & speichern
# ============================================================

def load_wotm():
    """Laedt wotm.json und gibt das Dict zurueck."""
    if not WOTM_PATH.exists():
        p(f"  FEHLER: {WOTM_PATH} nicht gefunden.")
        sys.exit(1)
    with open(WOTM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_wotm(data):
    """Speichert das WOTM-Dict zurueck in wotm.json."""
    with open(WOTM_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ============================================================
# --show: Aktuellen WOTM anzeigen
# ============================================================

def cmd_show():
    """Zeigt den aktuellen Whisky des Monats formatiert an."""
    data    = load_wotm()
    current = data.get("current")
    draft   = data.get("draft")

    if not current:
        p("  Kein aktueller WOTM gesetzt. Nutze --new um einen Draft zu erstellen.")
        return

    t = current.get("tasting", {})
    lines = [
        f"Monat:       {current.get('month', '?')}",
        f"Whisky:      {current.get('name', '?')}",
        f"Destillerie: {current.get('distillery', '?')}  |  Region: {current.get('region', '?')}",
        f"Alter:       {current.get('age', '?')} Jahre  |  ABV: {current.get('abv', '?')}%",
        f"Preis:       ca. {current.get('price_eur', '?')} EUR",
        "",
        f"Wertung: {t.get('wertung', '?')}/100  {stars(t.get('wertung', 0))}",
        "",
        "AROMA:",
        "  " + t.get("aroma", "-"),
        "",
        "GESCHMACK:",
        "  " + t.get("geschmack", "-"),
        "",
        "ABGANG:",
        "  " + t.get("abgang", "-"),
        "",
        "TEASER:",
        "  " + current.get("newsletter_teaser", "-"),
    ]
    box(f"WHISKY DES MONATS  --  {current.get('month', '')}", lines)

    if draft:
        p(f"  [!] Es gibt einen offenen Draft: {draft.get('name', '?')} -- nutze --approve oder --reject")


# ============================================================
# OpenAI: Tasting-Notizen generieren
# ============================================================

def generate_wotm_content(name, distillery, region, age, abv, config):
    """
    Ruft OpenAI GPT-4o auf und gibt ein Dict mit den generierten
    Tasting-Notizen, Beschreibung und Newsletter-Teaser zurueck.
    """
    try:
        from openai import OpenAI
    except ImportError:
        p("  FEHLER: openai-Paket nicht installiert. Bitte: pip install openai")
        sys.exit(1)

    client      = OpenAI(api_key=config["openai"]["api_key"])
    model       = config["openai"].get("model", "gpt-4o")
    temperature = config["openai"].get("temperature", 0.75)

    system_prompt = (
        "Du bist Steffen, ein Whisky-Enthusiast und Reiseblogger, der seit 14 Jahren "
        "Schottland bereist. Dein Ton ist: Buddy, Reiseguide, kompetent, un-snobbig, "
        "auf Deutsch. Du schreibst fuer das Whisky Magazin (whisky-magazin.de). "
        f"Generiere jetzt fuer den Whisky '{name}' aus {region} "
        f"({distillery}, {age} Jahre, {abv}% ABV) folgende Inhalte als valides JSON..."
    )

    user_prompt = f"""Erstelle fuer den Whisky "{name}" ({distillery}, {region}, {age} Jahre, {abv}% ABV) folgende Inhalte.

Ton: persoenlich, wie ein Kumpel der Whisky liebt, nicht snobbig, auf Deutsch.
Schreibe so, als waerst du Steffen vom Whisky Magazin (whisky-magazin.de).
Verwende korrekte deutsche Umlaute: ae->ae, oe->oe, ue->ue, ss->ss bzw. ae/oe/ue.

Antworte AUSSCHLIESSLICH mit diesem JSON-Format (kein anderer Text, kein Markdown-Wrapper):

{{
  "tasting": {{
    "aroma": "2-3 Saetze: Hauptaromen, was faellt zuerst auf, was kommt nach.",
    "geschmack": "2-3 Saetze: Gaumenein druck, Textur, Entwicklung im Mund.",
    "abgang": "1-2 Saetze: Laenge und Charakter des Abgangs.",
    "wertung": 88
  }},
  "beschreibung": "Absatz 1 (2-4 Saetze): Geschichte/Charakter der Destillerie und des Whiskys.\\n\\nAbsatz 2 (2-3 Saetze): Persoenliche Note, Reiseerinnerung oder Tipp von Steffen & Elmar.",
  "newsletter_teaser": "Maximal 2 Saetze. Knackig, neugierig machend, kein Marketing-Blabla."
}}"""

    p("  [KI] Sende Anfrage an OpenAI GPT-4o...")

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=900,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            break
        except Exception as e:
            p(f"  API-Fehler (Versuch {attempt + 1}/3): {e}")
            if attempt == 2:
                raise

    raw = response.choices[0].message.content.strip()

    # Markdown-Wrapper entfernen, falls GPT ihn trotzdem setzt
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw)
        raw = re.sub(r"\n?```\s*$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        p(f"  FEHLER: GPT-Antwort ist kein gueltiges JSON: {exc}")
        p("  Rohantwort:")
        p(raw[:500])
        sys.exit(1)


# ============================================================
# --new: Neuen WOTM-Draft erstellen
# ============================================================

def cmd_new(args):
    """Erstellt einen neuen WOTM-Draft via OpenAI und speichert ihn als draft."""
    config = load_config()
    data   = load_wotm()

    if data.get("draft"):
        p("  [!] Es gibt bereits einen offenen Draft:")
        p(f"      {data['draft'].get('name', '?')}")
        p("  Bitte erst --approve oder --reject ausfuehren.")
        return

    name       = args.name
    distillery = args.distillery or name.split()[0]
    region     = args.region     or "Schottland"
    age        = args.age        or 0
    abv        = args.abv        or 43.0
    price      = args.price      or 0
    affiliate  = args.affiliate  or (
        f"https://www.amazon.de/s?k={name.replace(' ', '+')}"
        f"&tag={config['affiliate_links'].get('amazon_tag', 'whiskyreise74-21')}"
    )

    p(f"  Erstelle Draft fuer: {name}")

    # KI-Inhalt generieren
    ai = generate_wotm_content(name, distillery, region, age, abv, config)

    # Monats-ID bauen
    now      = datetime.now()
    month_id = now.strftime("%Y-%m")
    slug     = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    entry_id = f"{slug}-{month_id}"

    monate = {
        1: "Januar", 2: "Februar", 3: "März", 4: "April",
        5: "Mai",    6: "Juni",    7: "Juli", 8: "August",
        9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
    }
    month_label = f"{monate[now.month]} {now.year}"

    draft = {
        "id":           entry_id,
        "month":        month_label,
        "name":         name,
        "distillery":   distillery,
        "region":       region,
        "age":          age,
        "abv":          abv,
        "price_eur":    price,
        "price_range":  "",
        "image_url":    "",
        "affiliate_url": affiliate,
        "tasting":      ai["tasting"],
        "beschreibung":  ai["beschreibung"],
        "newsletter_teaser": ai["newsletter_teaser"],
        "created_at":   now.strftime("%Y-%m-%d"),
        "created_by":   "wotm_generator",
        "approved":     False,
        "approved_at":  None,
    }

    data["draft"] = draft
    save_wotm(data)

    # Draft anzeigen
    t = draft["tasting"]
    lines = [
        f"[DRAFT] {draft['name']}",
        f"Destillerie: {draft['distillery']}  |  Region: {draft['region']}",
        f"Alter: {draft['age']} Jahre  |  ABV: {draft['abv']}%",
        "",
        f"Wertung: {t.get('wertung', '?')}/100  {stars(t.get('wertung', 0))}",
        "",
        "AROMA:",
        "  " + t.get("aroma", "-"),
        "",
        "GESCHMACK:",
        "  " + t.get("geschmack", "-"),
        "",
        "ABGANG:",
        "  " + t.get("abgang", "-"),
        "",
        "TEASER:",
        "  " + draft.get("newsletter_teaser", "-"),
    ]
    box(f"NEUER DRAFT -- {draft['month']}", lines)

    p("  Draft gespeichert in data/wotm.json")
    p("  Jetzt: python wotm_generator.py --approve  |  --reject")

    # Benachrichtigung versenden
    if _NOTIFIER_AVAILABLE:
        notify_wotm_draft_ready(draft)


# ============================================================
# --approve: Draft genehmigen
# ============================================================

def cmd_approve():
    """Genehmigt den aktuellen Draft, archiviert den alten current und baut die Site."""
    data  = load_wotm()
    draft = data.get("draft")

    if not draft:
        p("  Kein Draft vorhanden. Erstelle zuerst einen mit --new.")
        return

    now = datetime.now().strftime("%Y-%m-%d")

    # Alten current ins Archiv
    old_current = data.get("current")
    if old_current:
        archiv_entry = {
            "id":           old_current.get("id"),
            "month":        old_current.get("month"),
            "name":         old_current.get("name"),
            "distillery":   old_current.get("distillery"),
            "region":       old_current.get("region"),
            "age":          old_current.get("age"),
            "abv":          old_current.get("abv"),
            "price_eur":    old_current.get("price_eur"),
            "affiliate_url": old_current.get("affiliate_url"),
            "newsletter_teaser": old_current.get("newsletter_teaser"),
            "approved":     True,
        }
        if not isinstance(data.get("archiv"), list):
            data["archiv"] = []
        data["archiv"].insert(0, archiv_entry)
        p(f"  Archiviert: {old_current.get('name', '?')} ({old_current.get('month', '?')})")

    # Draft zum current machen
    draft["approved"]    = True
    draft["approved_at"] = now
    data["current"] = draft
    data["draft"]   = None
    save_wotm(data)

    p(f"  Genehmigt: {draft['name']} als WOTM fuer {draft['month']}")

    # Site-v2 neu bauen
    p()
    p("  Starte Site-Build (main.py --build-v2)...")
    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_DIR / "main.py"), "--build-v2"],
            cwd=str(PROJECT_DIR),
            capture_output=False,
        )
        if result.returncode == 0:
            p("  Site erfolgreich gebaut.")
        else:
            p(f"  Build beendet mit Code {result.returncode}.")
    except Exception as exc:
        p(f"  Build-Fehler: {exc}")

    # Freigabe-Benachrichtigung per E-Mail
    if _NOTIFIER_AVAILABLE:
        from notifier import send_notification, _base_html, _cmd_box
        month   = draft.get("month", "")
        name    = draft.get("name", "?")
        subject = f"\u2705 WOTM genehmigt: {name} ({month})"
        content_html = (
            f'<p style="margin:0 0 6px 0;font-size:12px;color:#B8762E;'
            f'text-transform:uppercase;letter-spacing:1px;">WOTM genehmigt</p>'
            f'<h2 style="margin:0 0 16px 0;font-size:22px;color:#2A2520;">'
            f'{name}</h2>'
            f'<p style="margin:0 0 20px 0;font-size:15px;color:#4A4440;">'
            f'<strong>{name}</strong> ist jetzt der Whisky des Monats fuer '
            f'<strong>{month}</strong>. Die Site wurde neu gebaut.</p>'
            f'<p style="margin:0 0 8px 0;font-size:14px;color:#4A4440;">'
            f'<strong>Newsletter erstellen:</strong></p>'
            + _cmd_box("python newsletter_generator.py --auto-draft")
        )
        send_notification(subject, _base_html(f"WOTM genehmigt: {name}", content_html))


# ============================================================
# --reject: Draft verwerfen
# ============================================================

def cmd_reject():
    """Verwirft den aktuellen Draft ohne Aenderung am current."""
    data  = load_wotm()
    draft = data.get("draft")

    if not draft:
        p("  Kein Draft vorhanden.")
        return

    name = draft.get("name", "?")
    data["draft"] = None
    save_wotm(data)
    p(f"  Draft '{name}' verworfen.")


# ============================================================
# --archiv: Archivierte WOTMs auflisten
# ============================================================

def cmd_archiv():
    """Listet alle archivierten WOTMs auf."""
    data   = load_wotm()
    archiv = data.get("archiv", [])

    if not archiv:
        p("  Archiv ist leer.")
        return

    lines = []
    for entry in archiv:
        lines.append(
            f"{entry.get('month', '?'):20s}  {entry.get('name', '?')}"
            f"  ({entry.get('region', '?')})"
        )

    box(f"WOTM-ARCHIV  ({len(archiv)} Eintraege)", lines)


# ============================================================
# --edit: wotm.json im Standard-Editor oeffnen
# ============================================================

def cmd_edit():
    """Oeffnet wotm.json im Standard-Editor des Systems."""
    p(f"  Oeffne: {WOTM_PATH}")
    if sys.platform == "win32":
        os.startfile(str(WOTM_PATH))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(WOTM_PATH)])
    else:
        editor = os.environ.get("EDITOR", "nano")
        subprocess.run([editor, str(WOTM_PATH)])


# ============================================================
# Argument-Parser & Einstiegspunkt
# ============================================================

def build_parser():
    parser = argparse.ArgumentParser(
        description="Whisky des Monats Generator & Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Beispiele:
  python wotm_generator.py --show
  python wotm_generator.py --new "Ardbeg 10 Years" --region Islay --age 10 --abv 46.0 --price 45
  python wotm_generator.py --approve
  python wotm_generator.py --reject
  python wotm_generator.py --archiv
  python wotm_generator.py --edit""",
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--show",    action="store_true", help="Aktuellen WOTM anzeigen")
    group.add_argument("--new",     metavar="NAME",      help="Neuen Draft erstellen (z.B. 'Ardbeg 10 Years')")
    group.add_argument("--approve", action="store_true", help="Draft genehmigen & Site bauen")
    group.add_argument("--reject",  action="store_true", help="Draft verwerfen")
    group.add_argument("--archiv",  action="store_true", help="Archivierte WOTMs auflisten")
    group.add_argument("--edit",    action="store_true", help="wotm.json im Editor oeffnen")

    # Optionen fuer --new
    parser.add_argument("--distillery", metavar="NAME",  help="Destilleriebezeichnung")
    parser.add_argument("--region",     metavar="REGION",help="Whisky-Region (z.B. Islay, Speyside)")
    parser.add_argument("--age",        type=int,        help="Alter in Jahren")
    parser.add_argument("--abv",        type=float,      help="Alkoholgehalt in Prozent")
    parser.add_argument("--price",      type=int,        help="Preis in EUR (gerundet)")
    parser.add_argument("--affiliate",  metavar="URL",   help="Direkter Affiliate-Link")

    return parser


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.show:
        cmd_show()
    elif args.new:
        cmd_new(args)
    elif args.approve:
        cmd_approve()
    elif args.reject:
        cmd_reject()
    elif args.archiv:
        cmd_archiv()
    elif args.edit:
        cmd_edit()


if __name__ == "__main__":
    main()
