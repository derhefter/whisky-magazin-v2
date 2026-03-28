#!/usr/bin/env python3
"""
=============================================================
  WHISKY MAGAZIN - Mailchimp Setup-Wizard
=============================================================

Fuehrt durch die Einrichtung der Mailchimp-Integration
fuer den monatlichen Newsletter.

Nutzung:
  python mailchimp_setup.py
=============================================================
"""

import sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
import base64
import urllib.request
import urllib.error
from pathlib import Path

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


def print_step(number, title):
    """Gibt eine Schritt-Ueberschrift aus."""
    print()
    print(f"  --- Schritt {number}: {title} ---")
    print()


def ask(prompt, default=None):
    """Fragt nach einer Eingabe mit optionalem Standardwert."""
    if default:
        display = f"  {prompt} [{default}]: "
    else:
        display = f"  {prompt}: "
    try:
        value = input(display).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Abgebrochen.")
        sys.exit(0)
    if not value and default:
        return default
    return value


def load_config():
    """Laedt config.json oder gibt leeres Dict zurueck."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config):
    """Speichert die Konfiguration in config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


# ============================================================
# Mailchimp API Test
# ============================================================

def test_mailchimp_connection(api_key, server_prefix):
    """
    Testet die Mailchimp API-Verbindung via Ping-Endpoint.
    Nutzt HTTP Basic Auth: Username = 'anystring', Password = API-Key.
    """
    url = f"https://{server_prefix}.api.mailchimp.com/3.0/ping"

    # Basic Auth Header erstellen
    credentials = f"anystring:{api_key}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {encoded}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            # Erfolg: {"health_status": "Everything's Chimpy!"}
            return True, data.get("health_status", "OK")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            err_data = json.loads(body)
            detail = err_data.get("detail", str(e))
        except Exception:
            detail = str(e)
        return False, detail
    except urllib.error.URLError as e:
        return False, f"Netzwerkfehler: {e.reason}"
    except Exception as e:
        return False, str(e)


# ============================================================
# Setup-Wizard
# ============================================================

def run_setup():
    """Fuehrt den kompletten Setup-Wizard durch."""

    print_box([
        "WHISKY MAGAZIN - Mailchimp Setup",
        "",
        "Dieser Wizard richtet die Mailchimp-Integration",
        "fuer deinen Newsletter ein.",
        "",
        "Du brauchst: Mailchimp-Account + API-Key",
    ])

    # ----------------------------------------------------------
    # Schritt 1: API-Key Anleitung
    # ----------------------------------------------------------
    print_step(1, "Mailchimp API-Key holen")
    print("  So kommst du an deinen API-Key:")
    print()
    print("  1. Gehe zu: https://mailchimp.com/help/about-api-keys/")
    print("  2. Logge dich in deinen Mailchimp-Account ein")
    print("  3. Klicke auf deinen Avatar (oben rechts)")
    print("  4. Waehle 'Profile' -> 'Extras' -> 'API keys'")
    print("  5. Klicke 'Create A Key' und kopiere den Key")
    print()
    print("  Der API-Key sieht so aus:")
    print("  xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-us21")
    print("  (endet mit einem Bindestrich + Serverkennung)")
    print()

    input("  Druecke ENTER wenn du deinen API-Key hast...")

    # ----------------------------------------------------------
    # Schritt 2: API-Key eingeben
    # ----------------------------------------------------------
    print_step(2, "API-Key eingeben")

    while True:
        api_key = ask("Mailchimp API-Key")

        if not api_key:
            print("  FEHLER: API-Key darf nicht leer sein.")
            continue

        # Server-Prefix aus dem Key extrahieren (z.B. "us21")
        if "-" not in api_key:
            print("  FEHLER: Ungueltig. Key muss mit '-us21' (o.ae.) enden.")
            continue

        server_prefix = api_key.split("-")[-1]
        print(f"  Server-Prefix erkannt: {server_prefix}")
        break

    # ----------------------------------------------------------
    # Schritt 3: Audience/List-ID
    # ----------------------------------------------------------
    print_step(3, "Audience ID eingeben")
    print("  Die Audience ID findest du in Mailchimp unter:")
    print("  Audience -> Manage Audience -> Settings -> Audience name and defaults")
    print("  Dort steht die 'Audience ID' (z.B. 'a1b2c3d4e5')")
    print()

    while True:
        audience_id = ask("Audience ID (List ID)")
        if audience_id:
            break
        print("  FEHLER: Audience ID darf nicht leer sein.")

    # ----------------------------------------------------------
    # Schritt 4: Absender-Informationen
    # ----------------------------------------------------------
    print_step(4, "Absender-Informationen")
    print("  Diese Angaben erscheinen im Newsletter als Absender.")
    print()

    from_name = ask("Absender-Name", default="Steffen & Elmar")

    while True:
        from_email = ask("Absender-E-Mail (verifiziert in Mailchimp)")
        if "@" in from_email and "." in from_email:
            break
        print("  FEHLER: Bitte eine gueltige E-Mail-Adresse eingeben.")

    while True:
        reply_to = ask("Reply-To E-Mail", default=from_email)
        if "@" in reply_to and "." in reply_to:
            break
        print("  FEHLER: Bitte eine gueltige E-Mail-Adresse eingeben.")

    # ----------------------------------------------------------
    # Schritt 5: Verbindung testen
    # ----------------------------------------------------------
    print_step(5, "API-Verbindung testen")
    print(f"  Teste Verbindung zu {server_prefix}.api.mailchimp.com ...")
    print()

    success, message = test_mailchimp_connection(api_key, server_prefix)

    if success:
        print(f"  Verbindung OK! Mailchimp antwortet: {message}")
    else:
        print(f"  FEHLER bei der Verbindung: {message}")
        print()
        print("  Moegliche Ursachen:")
        print("  - API-Key falsch oder abgelaufen")
        print("  - Server-Prefix stimmt nicht")
        print("  - Netzwerkproblem")
        print()
        retry = ask("Trotzdem speichern? (j/n)", default="n")
        if retry.lower() != "j":
            print("\n  Setup abgebrochen. Bitte API-Key pruefen und neu starten.")
            sys.exit(1)

    # ----------------------------------------------------------
    # Schritt 6: In config.json speichern
    # ----------------------------------------------------------
    print_step(6, "Konfiguration speichern")

    config = load_config()
    config["mailchimp"] = {
        "api_key": api_key,
        "server_prefix": server_prefix,
        "audience_id": audience_id,
        "from_name": from_name,
        "from_email": from_email,
        "reply_to": reply_to,
        "configured": True,
    }
    save_config(config)

    print(f"  Gespeichert in: {CONFIG_PATH.name}")

    # ----------------------------------------------------------
    # Abschluss
    # ----------------------------------------------------------
    print_box([
        "Setup abgeschlossen!",
        "",
        "Mailchimp ist jetzt konfiguriert.",
        "",
        "Naechste Schritte:",
        "",
        "  1. Newsletter-Entwurf erstellen:",
        "     python newsletter_generator.py --draft",
        "",
        "  2. Vorschau im Browser:",
        "     python newsletter_generator.py --preview",
        "",
        "  3. Freigeben und senden:",
        "     python newsletter_generator.py --approve",
        "     python newsletter_generator.py --send",
    ])


# ============================================================
# Eintrittspunkt
# ============================================================

if __name__ == "__main__":
    try:
        run_setup()
    except KeyboardInterrupt:
        print("\n\n  Abgebrochen.")
        sys.exit(0)
