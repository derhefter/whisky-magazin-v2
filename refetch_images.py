"""
Refetch all article images with improved landscape-focused queries.
Deletes existing images and re-downloads from Unsplash.
"""
import json
import os
import sys
import io
from pathlib import Path

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PROJECT_DIR = Path(__file__).parent
ARTICLES_DIR = PROJECT_DIR / "articles"
IMAGES_DIR = PROJECT_DIR / "site" / "images"
IMAGES_V2_DIR = PROJECT_DIR / "site-v2" / "images"

# Load config
with open(PROJECT_DIR / "config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Import our fetcher
from image_fetcher import find_image_queries, get_unsplash_image_url, download_image

# Load all articles
articles = []
for fp in sorted(ARTICLES_DIR.glob("*.json")):
    with open(fp, "r", encoding="utf-8") as f:
        articles.append(json.load(f))

print(f"\n  {len(articles)} Artikel gefunden.\n")

used_photo_ids = set()
updated = 0
errors = 0

for article in articles:
    slug = article.get("meta", {}).get("slug", "")
    if not slug:
        continue

    title = article.get("title", slug)
    img_path_v1 = IMAGES_DIR / f"{slug}.jpg"
    img_path_v2 = IMAGES_V2_DIR / f"{slug}.jpg"

    # Delete existing images
    for p in [img_path_v1, img_path_v2]:
        if p.exists():
            p.unlink()

    # Get new queries
    queries = find_image_queries(article)
    print(f"  [{slug[:50]}]")
    print(f"    Queries: {queries[:2]}")

    # Fetch from Unsplash
    unsplash_key = config.get("content_settings", {}).get("unsplash_api_key", "")
    image_data = get_unsplash_image_url(queries, unsplash_key, used_photo_ids)

    if not image_data.get("photo_id"):
        print(f"    WARNUNG: Kein Unsplash-Bild gefunden!")
        errors += 1
        continue

    # Download to v1 images dir
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    if download_image(image_data["url"], img_path_v1):
        size_kb = img_path_v1.stat().st_size // 1024
        print(f"    OK: {img_path_v1.name} ({size_kb} KB)")

        # Also copy to v2
        if IMAGES_V2_DIR.exists():
            import shutil
            shutil.copy2(img_path_v1, img_path_v2)

        # Update article JSON with new image data
        article["image_photo_id"] = image_data["photo_id"]
        article["image_credit"] = image_data.get("attribution", "")

        # Find and save article file
        for fp in ARTICLES_DIR.glob("*.json"):
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("meta", {}).get("slug") == slug:
                data["image_photo_id"] = image_data["photo_id"]
                data["image_credit"] = image_data.get("attribution", "")
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                break

        updated += 1
    else:
        print(f"    FEHLER: Download fehlgeschlagen")
        errors += 1

print(f"\n  Fertig: {updated} Bilder aktualisiert, {errors} Fehler.\n")
