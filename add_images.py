"""
Backfill-Script: Fügt Bilder zu bestehenden Artikeln hinzu.

Nutzung:
  python add_images.py                  # Alle Artikel ohne Bild bearbeiten
  python add_images.py --dry-run        # Nur zeigen, was getan würde
  python add_images.py --article SLUG   # Einen bestimmten Artikel bearbeiten
  python add_images.py --force          # Alle Artikel neu bearbeiten (auch mit Bild)
"""

import argparse
import json
import sys
from pathlib import Path

# UTF-8 Ausgabe auf Windows erzwingen
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(__file__).parent
ARTICLES_DIR = PROJECT_DIR / "articles"
SITE_DIR = PROJECT_DIR / "site"
IMAGES_DIR = SITE_DIR / "images"


def load_config():
    config_path = PROJECT_DIR / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_articles():
    articles_with_paths = []
    for json_file in sorted(ARTICLES_DIR.glob("*.json"), reverse=True):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                article = json.load(f)
            articles_with_paths.append((json_file, article))
        except Exception as e:
            print(f"  Warnung: Konnte {json_file.name} nicht laden: {e}")
    return articles_with_paths


def save_article(json_path, article):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(article, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Bilder zu Whisky-Magazin-Artikeln hinzufügen")
    parser.add_argument("--dry-run", action="store_true", help="Nur zeigen, keine Änderungen")
    parser.add_argument("--article", metavar="SLUG", help="Nur diesen Artikel bearbeiten")
    parser.add_argument("--force", action="store_true", help="Auch Artikel mit Bild neu bearbeiten")
    args = parser.parse_args()

    try:
        from image_fetcher import fetch_and_save_image, find_image_queries
    except ImportError:
        print("FEHLER: image_fetcher.py nicht gefunden.")
        sys.exit(1)

    config = load_config()
    articles = load_articles()

    if not articles:
        print("Keine Artikel gefunden.")
        return

    # Filter nach --article
    if args.article:
        articles = [(p, a) for p, a in articles if a.get("meta", {}).get("slug") == args.article]
        if not articles:
            print(f"Artikel '{args.article}' nicht gefunden.")
            sys.exit(1)

    # Statistik
    total = len(articles)
    skipped = 0
    processed = 0
    failed = 0

    # Globaler Duplikatschutz: bereits genutzte Unsplash-Photo-IDs sammeln
    used_photo_ids = set()
    for _, art in articles:
        if art.get("image_photo_id"):
            used_photo_ids.add(art["image_photo_id"])

    print(f"\nWhisky Magazin – Bilder hinzufügen")
    print(f"{'DRY-RUN: ' if args.dry_run else ''}Verarbeite {total} Artikel...\n")

    for json_path, article in articles:
        title = article.get("title", "?")
        slug = article.get("meta", {}).get("slug", json_path.stem)

        # Überspringen falls Bild vorhanden und kein --force
        if article.get("image_url") and not args.force:
            print(f"  [Übersprungen] {title[:60]} (hat bereits Bild)")
            skipped += 1
            continue

        print(f"  [{processed + 1}] {title[:60]}")

        if args.dry_run:
            queries = find_image_queries(article)
            print(f"    → Queries: {queries[:3]}")
            processed += 1
            continue

        # Bild fetchen (used_photo_ids wird in-place aktualisiert)
        image_data = fetch_and_save_image(article, config, IMAGES_DIR, used_photo_ids)
        if image_data:
            article["image_url"]      = image_data["url"]
            article["image_alt"]      = image_data["alt"]
            article["image_credit"]   = image_data["credit"]
            article["image_photo_id"] = image_data.get("photo_id", "")
            article["image_source"]   = "unsplash"
            save_article(json_path, article)
            print(f"    ✓ Gespeichert: {image_data['url']}")
            processed += 1
        else:
            print(f"    ✗ Fehlgeschlagen")
            failed += 1

    print(f"\n{'─' * 50}")
    print(f"Fertig! Verarbeitet: {processed}, Übersprungen: {skipped}, Fehler: {failed}")

    if processed > 0 and not args.dry_run:
        print(f"\nJetzt Website neu bauen:")
        print(f"  python main.py  →  Option [5] Website neu bauen")
        print(f"  oder direkt: python -c \"from site_builder import build_site; import json; build_site(json.load(open('config.json')))\"")


if __name__ == "__main__":
    main()
