#!/usr/bin/env python3
"""
=============================================================
  WHISKY MAGAZIN - Automatischer Website-Generator
=============================================================

Generiert SEO-optimierte Whisky- und Reise-Artikel und
baut daraus eine komplette statische Website.

Kein WordPress noetig. Kein Server noetig. Einfach ausfuehren.

Nutzung:
  python main.py                  -> Menue anzeigen
  python main.py --generate       -> Einen Artikel generieren
  python main.py --generate -n 3  -> 3 Artikel generieren
  python main.py --build          -> Website neu bauen
  python main.py --auto           -> Artikel generieren + Website bauen
  python main.py --serve          -> Lokalen Webserver starten
  python main.py --build-v2       -> Website v2 (Notebook-Design) bauen
  python main.py --serve-v2       -> V2 lokalen Webserver starten
  python main.py --stats          -> Statistiken anzeigen
"""

import argparse
import http.server
import json
import os
import random
import socketserver
import subprocess
import sys
import time
import webbrowser

# Windows Konsolen-Encoding Fix
os.environ["PYTHONIOENCODING"] = "utf-8"
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
ARTICLES_DIR = PROJECT_DIR / "articles"
SITE_DIR = PROJECT_DIR / "site"
SITE_V2_DIR = PROJECT_DIR / "site-v2"

sys.path.insert(0, str(PROJECT_DIR))

from site_builder import build_site, load_all_articles
from site_builder_v2 import build_site as build_site_v2
from topic_library import WHISKY_TOPICS

# Lazy-Import: content_generator erst bei Bedarf laden (braucht openai)
generate_article = None


# ============================================================
# Konfiguration
# ============================================================

def load_config():
    """Laedt die Konfiguration aus config.json."""
    config_path = PROJECT_DIR / "config.json"

    if not config_path.exists():
        print()
        print("  +===============================================+")
        print("  |  config.json nicht gefunden!                   |")
        print("  |                                                |")
        print("  |  Bitte kopiere config.example.json             |")
        print("  |  nach config.json und trage deinen             |")
        print("  |  OpenAI API-Key ein.                           |")
        print("  +===============================================+")
        print()
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    if config["openai"]["api_key"].startswith("sk-DEIN"):
        print()
        print("  FEHLER: OpenAI API-Key ist noch nicht eingetragen!")
        print("  Oeffne config.json und ersetze 'sk-DEIN_OPENAI_API_KEY'")
        print("  mit deinem echten API-Key.")
        print()
        sys.exit(1)

    return config


# ============================================================
# Themen-Verwaltung
# ============================================================

def load_used_topics():
    used_path = PROJECT_DIR / "used_topics.json"
    if used_path.exists():
        with open(used_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_used_topic(topic_title):
    used = load_used_topics()
    used.append({"title": topic_title, "date": datetime.now().isoformat()})
    with open(PROJECT_DIR / "used_topics.json", "w", encoding="utf-8") as f:
        json.dump(used, f, indent=2, ensure_ascii=False)


def pick_next_topic():
    used = load_used_topics()
    used_titles = {t["title"] for t in used}
    available = [t for t in WHISKY_TOPICS if t["title"] not in used_titles]

    if not available:
        print("  HINWEIS: Alle Themen verwendet! Starte von vorne...")
        available = WHISKY_TOPICS

    # Abwechslung bei Kategorien
    if len(available) > 5:
        recent_cats = []
        for t in reversed(used[-5:]):
            for topic in WHISKY_TOPICS:
                if topic["title"] == t["title"]:
                    recent_cats.append(topic.get("category", ""))
                    break
        preferred = [t for t in available if t.get("category", "") not in recent_cats]
        if preferred:
            available = preferred

    return random.choice(available)


# ============================================================
# Artikel speichern
# ============================================================

def save_article(article_data):
    """Speichert einen Artikel als JSON im articles-Ordner."""
    ARTICLES_DIR.mkdir(exist_ok=True)
    slug = article_data.get("meta", {}).get("slug", "artikel")
    date_str = article_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    filename = f"{date_str}_{slug}.json"
    filepath = ARTICLES_DIR / filename

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(article_data, f, indent=2, ensure_ascii=False)

    print(f"  Gespeichert: {filepath.name}")
    return filepath


# ============================================================
# Logging
# ============================================================

def log_action(action, details=""):
    log_path = PROJECT_DIR / "magazin.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {action}"
    if details:
        line += f" | {details}"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ============================================================
# Hauptfunktionen
# ============================================================

def cmd_generate(config, count=1):
    """Generiert neue Artikel."""
    global generate_article
    if generate_article is None:
        from content_generator import generate_article as _gen
        generate_article = _gen

    print(f"\n  Generiere {count} Artikel...\n")

    success = 0
    for i in range(count):
        print(f"  --- Artikel {i + 1} von {count} ---\n")

        topic = pick_next_topic()
        print(f"  Thema:     {topic['title']}")
        print(f"  Kategorie: {topic.get('category', 'Allgemein')}")
        print(f"  Typ:       {topic.get('type', 'article')}")
        print()

        try:
            article_data = generate_article(topic, config)
            save_article(article_data)
            save_used_topic(topic["title"])
            log_action("GENERATED", topic["title"])
            success += 1
            print(f"  Artikel erfolgreich generiert!\n")
        except Exception as e:
            print(f"\n  FEHLER: {e}\n")
            log_action("ERROR", f"{topic['title']} | {e}")

        if i < count - 1:
            wait = random.randint(3, 8)
            print(f"  Warte {wait} Sekunden...\n")
            time.sleep(wait)

    print(f"  ====================================")
    print(f"  ERGEBNIS: {success}/{count} Artikel generiert")
    print(f"  ====================================\n")
    return success


def cmd_build(config):
    """Baut die Website neu."""
    build_site(config)


def cmd_build_v2(config):
    """Baut die Website v2 (Notebook-Design) neu."""
    build_site_v2(config)


def cmd_serve_v2():
    """Startet einen lokalen Webserver fuer die v2-Website."""
    if not SITE_V2_DIR.exists():
        print("  FEHLER: Website v2 noch nicht gebaut!")
        print("  Fuehre zuerst 'Website v2 bauen' aus.")
        return

    port = 8082
    os.chdir(str(SITE_V2_DIR))

    handler = http.server.SimpleHTTPRequestHandler
    handler.extensions_map.update({".html": "text/html; charset=utf-8"})

    print(f"\n  Lokaler Webserver (v2) gestartet!")
    print(f"  Oeffne im Browser: http://localhost:{port}")
    print(f"  Druecke Strg+C zum Beenden.\n")

    webbrowser.open(f"http://localhost:{port}")

    with socketserver.TCPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server beendet.")


def cmd_auto(config, count=1):
    """Generiert Artikel UND baut die Website."""
    generated = cmd_generate(config, count)
    if generated > 0:
        print()
        cmd_build(config)
    return generated


def cmd_serve():
    """Startet einen lokalen Webserver zur Vorschau."""
    if not SITE_DIR.exists():
        print("  FEHLER: Website noch nicht gebaut!")
        print("  Fuehre zuerst 'Website bauen' aus.")
        return

    port = 8080
    os.chdir(str(SITE_DIR))

    handler = http.server.SimpleHTTPRequestHandler
    handler.extensions_map.update({".html": "text/html; charset=utf-8"})

    print(f"\n  Lokaler Webserver gestartet!")
    print(f"  Oeffne im Browser: http://localhost:{port}")
    print(f"  Druecke Strg+C zum Beenden.\n")

    # Browser automatisch oeffnen
    webbrowser.open(f"http://localhost:{port}")

    with socketserver.TCPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server beendet.")


def cmd_stats():
    """Zeigt Statistiken an."""
    articles = load_all_articles()
    used = load_used_topics()
    total_topics = len(WHISKY_TOPICS)

    print(f"\n  +======================================+")
    print(f"  |   STATISTIKEN                         |")
    print(f"  +======================================+\n")

    print(f"  Artikel generiert:   {len(articles)}")
    print(f"  Themen verwendet:    {len(used)} / {total_topics}")
    remaining = total_topics - len(used)
    print(f"  Themen uebrig:       {remaining}")

    if total_topics > 0:
        pct = (len(used) / total_topics) * 100
        bar_len = 25
        filled = int(bar_len * pct / 100)
        bar = "#" * filled + "-" * (bar_len - filled)
        print(f"  Fortschritt:         [{bar}] {pct:.0f}%")

    if remaining > 0:
        weeks = remaining / 3
        print(f"  Reicht noch fuer:    ca. {weeks:.0f} Wochen (bei 3/Woche)")

    if articles:
        # Kategorien zaehlen
        cats = {}
        for a in articles:
            c = a.get("category", "?")
            cats[c] = cats.get(c, 0) + 1

        print(f"\n  Artikel nach Kategorie:")
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"    {cat}: {count}")

    # Log lesen
    log_path = PROJECT_DIR / "magazin.log"
    if log_path.exists():
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        errors = sum(1 for l in lines if "ERROR" in l)
        if errors:
            print(f"\n  Fehler im Log: {errors}")

    # Letzte Artikel
    if articles:
        print(f"\n  Letzte 5 Artikel:")
        for a in articles[:5]:
            d = _short_date(a.get("date", ""))
            t = a["title"][:45]
            print(f"    {d}  {t}")

    print()


def _short_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return date_str


def cmd_test(config):
    """Testet die OpenAI-Verbindung."""
    print("\n  Teste OpenAI API-Verbindung...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config["openai"]["api_key"])
        response = client.chat.completions.create(
            model=config["openai"].get("model", "gpt-4o"),
            max_tokens=30,
            messages=[{"role": "user", "content": "Sage 'Slainte Mhath!' und erklaere es in einem Satz auf Deutsch."}],
        )
        result = response.choices[0].message.content.strip()
        print(f"  OpenAI OK!")
        print(f"  Antwort: {result}")
        print(f"\n  Alles bereit! Du kannst jetzt Artikel generieren.")
    except Exception as e:
        print(f"  FEHLER: {e}")
        print(f"\n  Bitte pruefe deinen API-Key in config.json.")


# ============================================================
# Interaktives Menue
# ============================================================

def interactive_menu(config):
    """Zeigt ein interaktives Menue."""
    articles = load_all_articles()

    print(f"\n  Was moechtest du tun?\n")

    print(f"  --- INHALTE ---")
    print(f"  [1]  Verbindung testen")
    print(f"  [2]  Einen Artikel generieren")
    print(f"  [3]  Drei Artikel generieren")
    print()

    print(f"  --- WEBSITE ---")
    print(f"  [4]  Website V1 bauen (Classic, aus {len(articles)} Artikeln)")
    print(f"  [5]  Website V1 anzeigen")
    print(f"  [9]  Website V2 bauen (Notebook)")
    print(f"  [10] Website V2 anzeigen")
    print()

    print(f"  --- REDAKTION ---")
    print(f"  [11] Whisky des Monats erstellen")
    print(f"  [12] Newsletter Entwurf erstellen")
    print(f"  [13] Newsletter Vorschau + Freigabe")
    print(f"  [14] Newsletter senden")
    print()

    print(f"  --- SETUP ---")
    print(f"  [15] Mailchimp einrichten")
    print(f"  [16] Zeitplaner einrichten")
    print(f"  [7]  Statistiken")
    print(f"  [0]  Beenden")
    print()

    try:
        choice = input("  Deine Wahl (0-16): ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    if choice == "1":
        cmd_test(config)
    elif choice == "2":
        cmd_auto(config, 1)
    elif choice == "3":
        cmd_auto(config, 3)
    elif choice == "4":
        cmd_build(config)
    elif choice == "5":
        cmd_serve()
    elif choice == "6":
        cmd_serve()
    elif choice == "7":
        cmd_stats()
    elif choice == "8":
        return
    elif choice == "9":
        cmd_build_v2(config)
    elif choice == "10":
        cmd_serve_v2()
    elif choice == "11":
        whisky_name = input("  Whisky-Name (z.B. 'Lagavulin 16'): ").strip()
        subprocess.run([sys.executable, "wotm_generator.py", "--new", whisky_name], cwd=str(PROJECT_DIR))
    elif choice == "12":
        subprocess.run([sys.executable, "newsletter_generator.py", "--draft"], cwd=str(PROJECT_DIR))
    elif choice == "13":
        subprocess.run([sys.executable, "newsletter_generator.py", "--preview"], cwd=str(PROJECT_DIR))
        freigabe = input("  Freigeben? (j/n): ").strip().lower()
        if freigabe == "j":
            subprocess.run([sys.executable, "newsletter_generator.py", "--approve"], cwd=str(PROJECT_DIR))
    elif choice == "14":
        confirm = input("  Wirklich senden? (j/n): ").strip().lower()
        if confirm == "j":
            subprocess.run([sys.executable, "newsletter_generator.py", "--send"], cwd=str(PROJECT_DIR))
    elif choice == "15":
        subprocess.run([sys.executable, "mailchimp_setup.py"], cwd=str(PROJECT_DIR))
    elif choice == "16":
        subprocess.run([sys.executable, "schedule_setup.py"], cwd=str(PROJECT_DIR))
    elif choice == "0":
        return
    else:
        print("  Ungueltige Auswahl.")


# ============================================================
# Eintrittspunkt
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Whisky Magazin - Automatischer Website-Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--generate", action="store_true", help="Artikel generieren")
    parser.add_argument("--build", action="store_true", help="Website bauen")
    parser.add_argument("--auto", action="store_true", help="Generieren + Bauen")
    parser.add_argument("--serve", action="store_true", help="Lokalen Webserver starten")
    parser.add_argument("--build-v2", action="store_true", help="Website v2 (Notebook-Design) bauen")
    parser.add_argument("--serve-v2", action="store_true", help="V2 lokalen Webserver starten")
    parser.add_argument("--stats", action="store_true", help="Statistiken anzeigen")
    parser.add_argument("--test", action="store_true", help="Verbindung testen")
    parser.add_argument("-n", "--count", type=int, default=1, help="Anzahl Artikel")

    args = parser.parse_args()

    print()
    print("  +==========================================+")
    print("  |   WHISKY MAGAZIN                          |")
    print("  |   Automatischer Website-Generator          |")
    print("  +==========================================+")

    config = load_config()

    if args.test:
        cmd_test(config)
    elif args.generate:
        cmd_generate(config, args.count)
    elif args.build:
        cmd_build(config)
    elif args.auto:
        cmd_auto(config, args.count)
    elif args.serve:
        cmd_serve()
    elif args.build_v2:
        cmd_build_v2(config)
    elif args.serve_v2:
        cmd_serve_v2()
    elif args.stats:
        cmd_stats()
    else:
        interactive_menu(config)


if __name__ == "__main__":
    main()
