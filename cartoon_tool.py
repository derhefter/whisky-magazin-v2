"""
Cartoon Tool: Verwandelt persönliche Reisefotos in Cartoon-Illustrationen.

Nutzt die OpenAI gpt-image-1 API (Image Editing) um Fotos stilistisch
zu transformieren – Gesichter werden in freundliche Cartoon-Charaktere
umgewandelt, der Hintergrund (Schottland, Destillerien, Whisky) bleibt
erkennbar.

Nutzung:
  # Einzelnes Foto bearbeiten:
  python cartoon_tool.py --photo "C:/pfad/zum/foto.JPG" --article mein-artikel-slug

  # Batch-Modus für ein ganzes Jahr aus dem Scotland Archive:
  python cartoon_tool.py --batch --year 2023

  # Liste verfügbarer Fotos für ein Jahr:
  python cartoon_tool.py --list --year 2023
"""

import argparse
import base64
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
ARTICLES_DIR = PROJECT_DIR / "articles"
IMAGES_DIR = PROJECT_DIR / "site" / "images"
SCOTLAND_ARCHIVE = PROJECT_DIR.parent / "scotland-archive"

CARTOON_PROMPT = (
    "Transform this travel photo into a warm, friendly cartoon illustration. "
    "Keep the locations, landscapes, whisky bottles, and distillery buildings recognizable and detailed. "
    "Replace any human faces with charming cartoon character faces – friendly, slightly stylized, "
    "still recognizable as the same people (same hair, clothing, body shape) but anonymized and fun. "
    "The overall style should feel like a graphic novel meets travel watercolor: "
    "rich colors, clear outlines, playful but not childish. "
    "Maintain the original composition and perspective."
)


def load_config():
    config_path = PROJECT_DIR / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_article(slug):
    for json_file in ARTICLES_DIR.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                article = json.load(f)
            if article.get("meta", {}).get("slug") == slug:
                return json_file, article
        except Exception:
            continue
    return None, None


def save_article(json_path, article):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(article, f, ensure_ascii=False, indent=2)


def cartoonize_photo(photo_path, output_path, api_key):
    """
    Sendet ein Foto an die OpenAI gpt-image-1 API und speichert das Cartoon-Ergebnis.
    Gibt True zurück bei Erfolg.
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("FEHLER: openai Paket nicht installiert. Bitte: pip install openai")
        sys.exit(1)

    try:
        from PIL import Image
        import io
    except ImportError:
        print("FEHLER: Pillow nicht installiert. Bitte: pip install Pillow")
        sys.exit(1)

    # Foto laden und auf max. 1024x1024 verkleinern
    print(f"  Lade Foto: {photo_path}")
    img = Image.open(photo_path)

    # Konvertierung zu RGB falls nötig (HEIC, CMYK etc.)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")

    # Skalieren (proportional, max. 1024px)
    img.thumbnail((1024, 1024), Image.LANCZOS)
    print(f"  Bildgröße nach Skalierung: {img.size[0]}x{img.size[1]}px")

    # Als PNG in Memory speichern
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    client = OpenAI(api_key=api_key)

    print(f"  Sende an OpenAI gpt-image-1 API...")
    print(f"  (Geschätzte Kosten: ~$0.04)")

    try:
        response = client.images.edit(
            model="gpt-image-1",
            image=("foto.png", img_bytes, "image/png"),
            prompt=CARTOON_PROMPT,
            n=1,
            size="1024x1024",
        )
    except Exception as e:
        # Fallback: DALL-E 3 mit text-only prompt (kein Bildeingang)
        print(f"  gpt-image-1 nicht verfügbar ({e}), versuche DALL-E 3 Fallback...")
        response = client.images.generate(
            model="dall-e-3",
            prompt=(
                "A warm, friendly cartoon illustration of two people on a whisky tour in Scotland. "
                "The style is graphic novel meets travel watercolor. "
                "The people are shown as charming cartoon characters – friendly, slightly stylized. "
                "Background: Scottish highland landscape with a distillery visible. "
                "Rich colors, clear outlines, playful atmosphere."
            ),
            n=1,
            size="1024x1024",
            quality="standard",
        )

    # Bild speichern
    image_data = response.data[0]

    if hasattr(image_data, 'b64_json') and image_data.b64_json:
        image_bytes = base64.b64decode(image_data.b64_json)
    elif hasattr(image_data, 'url') and image_data.url:
        import requests
        r = requests.get(image_data.url, timeout=30)
        r.raise_for_status()
        image_bytes = r.content
    else:
        print("  FEHLER: Kein Bild in der API-Antwort.")
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(image_bytes)
    print(f"  ✓ Cartoon gespeichert: {output_path}")
    return True


def cmd_single(photo_path, article_slug, config):
    """Einzelnes Foto cartoonisieren und Artikel aktualisieren."""
    photo_path = Path(photo_path)
    if not photo_path.exists():
        print(f"FEHLER: Foto nicht gefunden: {photo_path}")
        sys.exit(1)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    output_filename = f"{article_slug}-personal.jpg"
    output_path = IMAGES_DIR / output_filename

    print(f"\nCartoon Tool – Einzelfoto")
    print(f"Foto:    {photo_path.name}")
    print(f"Artikel: {article_slug}")
    print(f"Ausgabe: {output_path}\n")

    confirm = input("Fortfahren? [j/N] ").strip().lower()
    if confirm not in ("j", "ja", "y", "yes"):
        print("Abgebrochen.")
        return

    success = cartoonize_photo(photo_path, output_path, config["openai"]["api_key"])
    if not success:
        print("FEHLER: Cartoon-Generierung fehlgeschlagen.")
        sys.exit(1)

    # Artikel aktualisieren
    if article_slug:
        json_path, article = load_article(article_slug)
        if article:
            article["image_url"] = f"/images/{output_filename}"
            article["image_alt"] = article.get("title", "Eigenes Reisefoto")
            article["image_credit"] = ""
            article["image_source"] = "personal_cartoon"
            save_article(json_path, article)
            print(f"  ✓ Artikel aktualisiert: {article.get('title', article_slug)}")
        else:
            print(f"  Warnung: Artikel '{article_slug}' nicht gefunden. Bild wurde gespeichert, aber kein Artikel aktualisiert.")

    print(f"\nFertig! Jetzt Website neu bauen:")
    print(f"  python main.py  →  Option [5] Website neu bauen")


def cmd_batch(year, config):
    """Batch-Modus: Fotos aus Scotland Archive verarbeiten."""
    archive_year_dir = SCOTLAND_ARCHIVE / str(year)

    # Suche nach Foto-Ordner
    photos_dir = None
    for candidate in [archive_year_dir / "photos", archive_year_dir / "Photos", archive_year_dir]:
        if candidate.is_dir():
            photos_dir = candidate
            break

    if not photos_dir:
        print(f"FEHLER: Keine Fotos gefunden für Jahr {year}")
        print(f"Gesucht in: {archive_year_dir}")
        sys.exit(1)

    # Alle Fotos auflisten
    photo_extensions = {".jpg", ".jpeg", ".png", ".heic", ".JPG", ".JPEG", ".PNG", ".HEIC"}
    photos = [p for p in photos_dir.iterdir() if p.suffix in photo_extensions]
    photos.sort()

    if not photos:
        print(f"Keine Fotos gefunden in: {photos_dir}")
        sys.exit(1)

    print(f"\nCartoon Tool – Batch-Modus ({year})")
    print(f"Gefunden: {len(photos)} Fotos in {photos_dir}\n")

    # Alle verfügbaren Artikel-Slugs anzeigen
    all_slugs = []
    for json_file in sorted(ARTICLES_DIR.glob("*.json")):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                a = json.load(f)
            slug = a.get("meta", {}).get("slug", "")
            title = a.get("title", "")
            if slug:
                all_slugs.append((slug, title))
        except Exception:
            continue

    # Assignments-Datei
    assignments_path = PROJECT_DIR / "cartoon_assignments.json"
    assignments = {}

    print("=" * 60)
    print("Für jedes Foto: Artikel-Slug eingeben (oder Enter zum Überspringen)")
    print("Verfügbare Artikel-Slugs werden bei Eingabe '?' angezeigt")
    print("=" * 60)

    for i, photo in enumerate(photos, 1):
        print(f"\n[{i}/{len(photos)}] {photo.name}")
        while True:
            slug_input = input("  Artikel-Slug (Enter = überspringen, '?' = Liste): ").strip()
            if not slug_input:
                break
            if slug_input == "?":
                print("\n  Verfügbare Slugs:")
                for s, t in all_slugs:
                    print(f"    {s:50s} {t[:40]}")
                print()
                continue
            # Prüfen ob Slug existiert
            matching = [(s, t) for s, t in all_slugs if s == slug_input]
            if not matching:
                # Fuzzy-Suche
                fuzzy = [(s, t) for s, t in all_slugs if slug_input in s]
                if fuzzy:
                    print(f"  Ähnliche Slugs:")
                    for s, t in fuzzy[:5]:
                        print(f"    {s} → {t[:40]}")
                    continue
                print(f"  Warnung: Slug '{slug_input}' nicht gefunden. Trotzdem verwenden? [j/N]")
                if input("  ").strip().lower() not in ("j", "ja"):
                    continue
            assignments[str(photo)] = slug_input
            print(f"  ✓ Zugewiesen: {photo.name} → {slug_input}")
            break

    if not assignments:
        print("\nKeine Zuweisungen gemacht. Abgebrochen.")
        return

    # Assignments speichern zur Überprüfung
    with open(assignments_path, "w", encoding="utf-8") as f:
        json.dump(assignments, f, ensure_ascii=False, indent=2)
    print(f"\n{len(assignments)} Zuweisungen gespeichert in: {assignments_path}")

    # Bestätigung vor Verarbeitung
    print(f"\nZuweisungen:")
    for photo_str, slug in assignments.items():
        print(f"  {Path(photo_str).name} → {slug}")

    print(f"\nKosten: ~${len(assignments) * 0.04:.2f} (gpt-image-1, $0.04/Bild)")
    confirm = input("\nAlle Fotos cartoonisieren? [j/N] ").strip().lower()
    if confirm not in ("j", "ja", "y", "yes"):
        print(f"Abgebrochen. Assignments gespeichert unter {assignments_path}")
        print(f"Später ausführen mit: python cartoon_tool.py --from-assignments")
        return

    # Verarbeitung
    success_count = 0
    for photo_str, slug in assignments.items():
        photo_path = Path(photo_str)
        output_path = IMAGES_DIR / f"{slug}-personal.jpg"
        print(f"\n→ {photo_path.name}")
        if cartoonize_photo(photo_path, output_path, config["openai"]["api_key"]):
            # Artikel aktualisieren
            json_path, article = load_article(slug)
            if article:
                article["image_url"] = f"/images/{slug}-personal.jpg"
                article["image_alt"] = article.get("title", "Eigenes Reisefoto")
                article["image_credit"] = ""
                article["image_source"] = "personal_cartoon"
                save_article(json_path, article)
                print(f"  ✓ Artikel aktualisiert: {article.get('title', slug)}")
            success_count += 1

    print(f"\n{'=' * 60}")
    print(f"Fertig! {success_count}/{len(assignments)} Fotos cartoonisiert.")
    if success_count > 0:
        print(f"\nJetzt Website neu bauen:")
        print(f"  python main.py  →  Option [5] Website neu bauen")


def cmd_list(year):
    """Fotos eines Jahres aus dem Scotland Archive auflisten."""
    archive_year_dir = SCOTLAND_ARCHIVE / str(year)
    photos_dir = None
    for candidate in [archive_year_dir / "photos", archive_year_dir / "Photos", archive_year_dir]:
        if candidate.is_dir():
            photos_dir = candidate
            break

    if not photos_dir:
        print(f"Kein Ordner gefunden für Jahr {year}")
        sys.exit(1)

    photo_extensions = {".jpg", ".jpeg", ".png", ".heic", ".JPG", ".JPEG", ".PNG", ".HEIC"}
    photos = sorted([p for p in photos_dir.iterdir() if p.suffix in photo_extensions])

    print(f"\nFotos aus {year} ({photos_dir}):")
    for i, p in enumerate(photos, 1):
        size_kb = p.stat().st_size // 1024
        print(f"  [{i:3d}] {p.name:40s} {size_kb:>6} KB")
    print(f"\nGesamt: {len(photos)} Fotos")


def cmd_from_assignments(config):
    """Assignments aus JSON-Datei verarbeiten."""
    assignments_path = PROJECT_DIR / "cartoon_assignments.json"
    if not assignments_path.exists():
        print(f"FEHLER: {assignments_path} nicht gefunden. Zuerst --batch ausführen.")
        sys.exit(1)

    with open(assignments_path, "r", encoding="utf-8") as f:
        assignments = json.load(f)

    print(f"\nVerarbeite {len(assignments)} Assignments aus {assignments_path.name}")
    for photo_str, slug in assignments.items():
        photo_path = Path(photo_str)
        output_path = IMAGES_DIR / f"{slug}-personal.jpg"
        if output_path.exists():
            print(f"  [Bereits vorhanden] {output_path.name}")
            continue
        print(f"\n→ {photo_path.name} → {slug}")
        if cartoonize_photo(photo_path, output_path, config["openai"]["api_key"]):
            json_path, article = load_article(slug)
            if article:
                article["image_url"] = f"/images/{slug}-personal.jpg"
                article["image_alt"] = article.get("title", "Eigenes Reisefoto")
                article["image_credit"] = ""
                article["image_source"] = "personal_cartoon"
                save_article(json_path, article)


def main():
    parser = argparse.ArgumentParser(description="Cartoon Tool für Whisky Magazin Reisefotos")
    parser.add_argument("--photo", metavar="PFAD", help="Pfad zum Foto")
    parser.add_argument("--article", metavar="SLUG", help="Artikel-Slug für das Foto")
    parser.add_argument("--batch", action="store_true", help="Batch-Modus (interaktiv)")
    parser.add_argument("--list", action="store_true", help="Fotos eines Jahres auflisten")
    parser.add_argument("--from-assignments", action="store_true", help="cartoon_assignments.json verarbeiten")
    parser.add_argument("--year", type=int, help="Jahr für Batch/List-Modus")
    args = parser.parse_args()

    config = load_config()

    if args.photo:
        cmd_single(args.photo, args.article or "", config)
    elif args.batch:
        if not args.year:
            print("FEHLER: --batch benötigt --year YYYY")
            sys.exit(1)
        cmd_batch(args.year, config)
    elif args.list:
        if not args.year:
            print("FEHLER: --list benötigt --year YYYY")
            sys.exit(1)
        cmd_list(args.year)
    elif args.from_assignments:
        cmd_from_assignments(config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
