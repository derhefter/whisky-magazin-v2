"""
Map Data Builder: Erzeugt map-data.json aus scotland-archive Stops + Artikeln.
Liest GPS-Stops, Routen und Fotos, dedupliziert Orte, matcht Artikel.
"""

import json
import math
import os
import re
from pathlib import Path
from PIL import Image

PROJECT_DIR = Path(__file__).parent
ARCHIVE_DIR = PROJECT_DIR.parent / "scotland-archive"
SITE_DIR = PROJECT_DIR / "site"
ARTICLES_DIR = PROJECT_DIR / "articles"

# Thumbnail-Groesse
THUMB_WIDTH = 400
THUMB_QUALITY = 75

# Haversine-Schwelle fuer Deduplizierung (Meter)
DEDUP_DISTANCE_M = 300


# ============================================================
# Hilfsfunktionen
# ============================================================

def haversine_m(lat1, lon1, lat2, lon2):
    """Entfernung zwischen zwei GPS-Koordinaten in Metern."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def slugify(text):
    """Einfacher Slug aus Text."""
    text = text.lower().strip()
    text = re.sub(r'[äÄ]', 'ae', text)
    text = re.sub(r'[öÖ]', 'oe', text)
    text = re.sub(r'[üÜ]', 'ue', text)
    text = re.sub(r'[ß]', 'ss', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')


def classify_stop(place_name):
    """Klassifiziert einen Stop anhand des Namens."""
    name_lower = place_name.lower()
    if any(kw in name_lower for kw in ['distillery', 'destillerie', 'brennerei', 'brewery',
                                         'whisky experience', 'scotch whisky']):
        return 'distillery'
    if any(kw in name_lower for kw in ['airport', 'flughafen', 'heathrow', 'hotel',
                                         'b&b', 'hostel', 'airbnb', 'unterkunft',
                                         'faehre', 'fähre', 'ferry', 'tankstelle',
                                         'ankunft', 'abfahrt', 'abreise']):
        return 'travel_stop'
    if any(kw in name_lower for kw in ['castle', 'loch', 'beach', 'glen ', 'ben ',
                                         'mountain', 'hiking', 'trail', 'waterfall',
                                         'isle', 'insel', 'bucht', 'bay', 'cliff']):
        return 'nature'
    if any(kw in name_lower for kw in ['pub', 'bar', 'restaurant', 'shop', 'market',
                                         'museum', 'cathedral', 'kirk', 'stadium',
                                         'experience', 'visitor centre', 'visitor center',
                                         'heritage', 'exhibition', 'gallery']):
        return 'poi'
    # Wenn nichts passt, pruefen ob es eine bekannte Stadt/Region ist
    return 'city'


def detect_country(region, place_name):
    """Erkennt das Land basierend auf Region/Ortsname."""
    combined = f"{region} {place_name}".lower()
    if any(kw in combined for kw in ['kentucky', 'tennessee', 'louisville', 'bourbon',
                                      'usa', 'nashville', 'lynchburg', 'woodford',
                                      'estill', 'danville', 'franklin ky',
                                      'dueling grounds', 'wilderness trail',
                                      'glenns creek', 'regeneration distillery',
                                      'bardstown', 'clermont', 'loretto',
                                      'lawrenceburg', 'lexington', 'versailles',
                                      'frankfort', 'shelbyville', 'clarksville',
                                      'tullahoma', 'georgetown', 'eastern kentucky']):
        return 'USA'
    if any(kw in combined for kw in ['dublin', 'ireland', 'irland', 'irish',
                                      'teeling', 'jameson']):
        return 'Irland'
    if any(kw in combined for kw in ['london', 'heathrow', 'england']):
        return 'England'
    if any(kw in combined for kw in ['berlin', 'dresden', 'deutschland', 'hamburg',
                                      'münchen', 'germany', 'deutsche', 'thüringen',
                                      'thuringen', 'thueringen', 'nine springs',
                                      'bayern', 'sachsen', 'nordrhein']):
        return 'Deutschland'
    return 'Schottland'


def simplify_coords(coords, tolerance=0.005):
    """Vereinfacht eine Koordinatenliste (Douglas-Peucker-aehnlich, simpel)."""
    if len(coords) <= 10:
        return coords
    # Jeden n-ten Punkt behalten, plus Start und Ende
    step = max(1, len(coords) // 50)
    simplified = [coords[0]]
    for i in range(step, len(coords) - 1, step):
        simplified.append(coords[i])
    simplified.append(coords[-1])
    return simplified


# ============================================================
# Daten laden
# ============================================================

def load_all_stops():
    """Laedt alle Stops aus allen Jahren des scotland-archive."""
    all_stops = []
    archive_years = sorted([
        d for d in ARCHIVE_DIR.iterdir()
        if d.is_dir() and d.name.isdigit()
    ], key=lambda d: d.name)

    for year_dir in archive_years:
        stops_file = year_dir / "derived" / "stops.json"
        if not stops_file.exists():
            continue
        year = int(year_dir.name)
        with open(stops_file, "r", encoding="utf-8") as f:
            stops = json.load(f)
        for stop in stops:
            stop["_year"] = year
            stop["_archive_dir"] = str(year_dir)
        all_stops.extend(stops)

    print(f"  {len(all_stops)} Stops aus {len(archive_years)} Jahren geladen.")
    return all_stops


def load_all_routes():
    """Laedt alle GeoJSON-Routen aus dem scotland-archive."""
    routes = []
    archive_years = sorted([
        d for d in ARCHIVE_DIR.iterdir()
        if d.is_dir() and d.name.isdigit()
    ], key=lambda d: d.name)

    for year_dir in archive_years:
        geojson_file = year_dir / "derived" / "route.geojson"
        if not geojson_file.exists():
            continue
        year = int(year_dir.name)
        with open(geojson_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Route-LineString extrahieren
        for feature in data.get("features", []):
            geom = feature.get("geometry", {})
            if geom.get("type") == "LineString":
                coords = simplify_coords(geom["coordinates"])
                routes.append({
                    "year": year,
                    "label": f"Reise {year}",
                    "geojson": {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": coords
                        },
                        "properties": {"year": year}
                    }
                })
                break  # Nur eine Route pro Jahr

    print(f"  {len(routes)} Routen geladen.")
    return routes


def load_all_articles():
    """Laedt alle Artikel-Metadaten (ohne HTML-Content)."""
    articles = []
    if not ARTICLES_DIR.exists():
        return articles
    for f in sorted(ARTICLES_DIR.glob("*.json")):
        with open(f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # HTML-Content nicht benoetigt
        data.pop("html_content", None)
        articles.append(data)
    print(f"  {len(articles)} Artikel geladen.")
    return articles


def load_manual_locations():
    """Laedt manuell gepflegte Locations aus data/manual-locations.json."""
    manual_file = PROJECT_DIR / "data" / "manual-locations.json"
    if not manual_file.exists():
        return []
    with open(manual_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    locations = data.get("locations", [])
    print(f"  {len(locations)} manuelle Locations geladen.")
    return locations


# ============================================================
# Deduplizierung & Zusammenfuehrung
# ============================================================

def deduplicate_stops(stops):
    """Fasst Stops an aehnlichen Koordinaten zusammen."""
    locations = []

    for stop in stops:
        lat = stop.get("lat")
        lon = stop.get("lon")
        if lat is None or lon is None:
            continue
        # Ungueltige Koordinaten (0,0 = "Null Island") filtern
        if abs(lat) < 1 and abs(lon) < 1:
            continue
        name = stop.get("place_name", "Unbekannt")
        year = stop.get("_year", 0)
        assets = stop.get("assets", [])
        region = stop.get("region", "")
        archive_dir = stop.get("_archive_dir", "")

        # Existierenden Ort in der Naehe suchen -- nur gleichen Typ zusammenfuehren
        stop_type = classify_stop(name)
        merged = False
        for loc in locations:
            dist = haversine_m(lat, lon, loc["lat"], loc["lon"])
            if dist < DEDUP_DISTANCE_M and loc["type"] == stop_type:
                # Zusammenfuehren
                if year not in loc["years_visited"]:
                    loc["years_visited"].append(year)
                    loc["years_visited"].sort()
                # Fotos hinzufuegen
                for asset in assets[:2]:  # Max 2 Fotos pro Stop-Besuch
                    photo_entry = {
                        "src": asset,
                        "year": year,
                        "archive_dir": archive_dir
                    }
                    if len(loc["_photos"]) < 8:  # Max 8 Fotos pro Ort
                        loc["_photos"].append(photo_entry)
                # Besseren Namen bevorzugen (laengerer Name = spezifischer)
                if len(name) > len(loc["name"]) and 'ankunft' not in name.lower():
                    loc["name"] = name
                merged = True
                break

        if not merged:
            loc_id = f"loc-{slugify(name)}"
            # ID-Kollisionen vermeiden
            existing_ids = {l["id"] for l in locations}
            if loc_id in existing_ids:
                loc_id = f"{loc_id}-{year}"
            locations.append({
                "id": loc_id,
                "name": name,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "type": classify_stop(name),
                "region": region,
                "country": detect_country(region, name),
                "years_visited": [year],
                "articles": [],
                "_photos": [
                    {"src": a, "year": year, "archive_dir": archive_dir}
                    for a in assets[:2]
                ]
            })

    print(f"  {len(stops)} Stops -> {len(locations)} einzigartige Orte.")
    return locations


# ============================================================
# Artikel-Matching
# ============================================================

def extract_year_from_slug(slug):
    """Extrahiert eine Jahreszahl (2007-2025) aus einem Slug."""
    match = re.search(r'(20[0-2]\d)', slug)
    if match:
        year = int(match.group(1))
        if 2007 <= year <= 2025:
            return year
    return None


def match_articles_to_locations(articles, locations):
    """Verknuepft Artikel mit Locations ueber Tags und Year-Matching."""
    # Index: Ortsname (lowercase) -> Location
    name_index = {}

    def add_index(key, loc):
        key = key.strip()
        if len(key) >= 3 and key not in name_index:
            name_index[key] = loc

    for loc in locations:
        name_lower = loc["name"].lower()
        add_index(name_lower, loc)

        # Schrittweises Stripping von Suffixen und Präfixen
        cleaned = name_lower
        # 1. Trailing company suffixes
        for suf in [" co.", " co", " company", " ltd", " llc"]:
            if cleaned.endswith(suf):
                cleaned = cleaned[:-len(suf)].strip()
                add_index(cleaned, loc)
                break
        # 2. Distillery-type suffixes
        for suf in [" distillery", " distilling", " destillerie", " brewery", " brewing", " whisky"]:
            if cleaned.endswith(suf):
                cleaned = cleaned[:-len(suf)].strip()
                add_index(cleaned, loc)
                break
        # 3. Leading articles / prefixes
        for pre in ["the ", "isle of ", "loch "]:
            if cleaned.startswith(pre):
                short = cleaned[len(pre):]
                add_index(short, loc)
        # 4. Also index key words individually for compound names like "Glasgow Distillery"
        # so that tag "Glasgow Distillery" matches "Glasgow Distillery Co"
        words = name_lower.split()
        for i in range(1, len(words)):
            partial = " ".join(words[:i])
            if len(partial) >= 5:
                add_index(partial, loc)

    # Index: Region (lowercase) -> Locations
    region_index = {}
    for loc in locations:
        region = (loc.get("region") or "").lower()
        if region not in region_index:
            region_index[region] = []
        region_index[region].append(loc)

    # Index: Year -> Locations
    year_index = {}
    for loc in locations:
        for y in loc["years_visited"]:
            if y not in year_index:
                year_index[y] = []
            year_index[y].append(loc)

    matched_count = 0
    for article in articles:
        slug = article.get("meta", {}).get("slug", "")
        tags = [t.lower() for t in article.get("tags", [])]
        article_type = article.get("type", "")

        # 1. Explizite locations im Artikel (falls vorhanden) — kein continue, läuft zusätzlich
        if "locations" in article:
            for loc_data in article["locations"]:
                # Supports both string ("Macallan Distillery") and dict ({"name": "..."})
                if isinstance(loc_data, str):
                    loc_name = loc_data.lower()
                else:
                    loc_name = loc_data.get("name", "").lower()
                if loc_name in name_index:
                    target = name_index[loc_name]
                    if slug not in target["articles"]:
                        target["articles"].append(slug)
                        matched_count += 1

        # 2. Tag-basiertes Matching (inkl. title-Wörter)
        title_words = [w.lower() for w in article.get("title", "").split() if len(w) >= 5]
        search_terms = list(set(tags + title_words))
        for tag in search_terms:
            if tag in name_index:
                target = name_index[tag]
                if slug not in target["articles"]:
                    target["articles"].append(slug)
                    matched_count += 1

        # 3. Year-basiertes Matching fuer Reiseberichte
        if article_type == "reisebericht":
            year = extract_year_from_slug(slug)
            if year and year in year_index:
                for loc in year_index[year]:
                    if slug not in loc["articles"]:
                        loc["articles"].append(slug)
                        matched_count += 1

    print(f"  {matched_count} Artikel-Location-Verknuepfungen erstellt.")


# ============================================================
# Foto-Thumbnails
# ============================================================

def generate_thumbnails(locations):
    """Erzeugt Thumbnails fuer die Karten-Popups."""
    thumb_dir = SITE_DIR / "images" / "map"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    generated = 0
    for loc in locations:
        photos_out = []
        for i, photo in enumerate(loc.get("_photos", [])):
            src = photo["src"]
            archive_dir = photo.get("archive_dir", "")

            # Quellpfad zusammensetzen
            if archive_dir:
                source_path = Path(archive_dir).parent / src
            else:
                source_path = ARCHIVE_DIR / src

            if not source_path.exists():
                continue

            # Thumbnail-Dateiname
            thumb_name = f"{loc['id']}_{i}.jpg"
            thumb_path = thumb_dir / thumb_name

            if not thumb_path.exists():
                try:
                    with Image.open(source_path) as img:
                        # EXIF-Rotation beruecksichtigen
                        from PIL import ImageOps
                        img = ImageOps.exif_transpose(img)
                        # Resize
                        ratio = THUMB_WIDTH / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((THUMB_WIDTH, new_height), Image.LANCZOS)
                        img = img.convert("RGB")
                        img.save(thumb_path, "JPEG", quality=THUMB_QUALITY)
                        generated += 1
                except Exception as e:
                    print(f"  WARNUNG: Thumbnail-Fehler fuer {source_path}: {e}")
                    continue

            photos_out.append({
                "src": f"/images/map/{thumb_name}",
                "year": photo["year"],
                "caption": loc["name"]
            })

        loc["photos"] = photos_out

    print(f"  {generated} neue Thumbnails erzeugt.")


# ============================================================
# Hauptfunktion
# ============================================================

def build_map_data(config=None):
    """Baut die komplette map-data.json aus allen Quellen."""
    print("\n  Karten-Daten werden erstellt...")

    # 1. Stops laden & deduplizieren
    stops = load_all_stops()
    locations = deduplicate_stops(stops)

    # 2. Routen -- deaktiviert (vom Nutzer als verwirrend empfunden)
    routes = []

    # 3. Manuelle Locations laden & mergen (Google Maps Listen etc.)
    manual_locs = load_manual_locations()
    added_manual = 0
    for ml in manual_locs:
        lat, lon = ml.get("lat", 0), ml.get("lon", 0)
        name = ml.get("name", "")
        if not name or not lat or not lon:
            continue
        loc_type = ml.get("type", "distillery")
        # Pruefen ob schon vorhanden (gleicher Typ + gleicher Name + < 300m Entfernung)
        # Name-Check verhindert, dass benachbarte Destillerien (z.B. Springbank/Glengyle)
        # fälschlicherweise zusammengeführt werden.
        already_exists = False
        for existing in locations:
            if existing["type"] == loc_type:
                dist = haversine_m(lat, lon, existing["lat"], existing["lon"])
                if dist < DEDUP_DISTANCE_M and name.lower() == existing["name"].lower():
                    already_exists = True
                    break
        if not already_exists:
            loc_id = f"loc-{slugify(name)}"
            existing_ids = {l["id"] for l in locations}
            if loc_id in existing_ids:
                loc_id = f"{loc_id}-manual"
            locations.append({
                "id": loc_id,
                "name": name,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "type": loc_type,
                "region": ml.get("region", ""),
                "country": ml.get("country", ""),
                "years_visited": ml.get("years_visited", [2024] if ml.get("country") == "USA" else []),
                "articles": [],
                "_photos": [],
                "_manual": True
            })
            added_manual += 1
    print(f"  {added_manual} neue manuelle Locations hinzugefuegt ({len(manual_locs) - added_manual} bereits vorhanden).")

    # 3b. Name-basierte Deduplizierung für Destillerien:
    # Wenn GPS-Stops dieselbe Destillerie mehrfach an verschiedenen Koordinaten haben
    # (z.B. Annandale 4×, Girvan 6×), behalten wir nur den besten Eintrag.
    name_best = {}  # key -> best location
    for loc in locations:
        if loc["type"] != "distillery":
            continue
        key = loc["name"].lower()
        if key not in name_best:
            name_best[key] = loc
        else:
            existing = name_best[key]
            # Daten zusammenführen (Jahre, Fotos)
            for y in loc["years_visited"]:
                if y not in existing["years_visited"]:
                    existing["years_visited"].append(y)
            existing["_photos"].extend(loc.get("_photos", []))
            # Manuelle Einträge haben korrektere Koordinaten → bevorzugen
            if loc.get("_manual") and not existing.get("_manual"):
                loc["years_visited"] = existing["years_visited"][:]
                loc["_photos"] = existing["_photos"][:]
                loc["articles"] = list(set(existing.get("articles", []) + loc.get("articles", [])))
                name_best[key] = loc

    # Locations neu aufbauen: Nicht-Destillerien bleiben, Destillerien → je 1 pro Name
    non_distilleries = [l for l in locations if l["type"] != "distillery"]
    locations = non_distilleries + list(name_best.values())
    print(f"  Deduplizierung: {len(name_best)} einzigartige Destillerien (Name-basiert).")

    # 4. Artikel laden & matchen
    articles = load_all_articles()
    match_articles_to_locations(articles, locations)

    # 4. Thumbnails erzeugen
    generate_thumbnails(locations)

    # 5. Artikel-Metadaten fuer Popup-Anzeige sammeln
    article_meta = {}
    for a in articles:
        slug = a.get("meta", {}).get("slug", "")
        if slug:
            article_meta[slug] = {
                "title": a.get("title", ""),
                "teaser": a.get("meta", {}).get("teaser", ""),
                "image": a.get("image_url", ""),
                "category": a.get("category", ""),
                "date": a.get("date_display", a.get("date", ""))
            }

    # 6. Regions und Years sammeln
    all_regions = sorted(set(loc["region"] for loc in locations if loc["region"]))
    all_years = sorted(set(y for loc in locations for y in loc["years_visited"]))
    all_countries = sorted(set(loc["country"] for loc in locations))

    # 7. Interne Felder entfernen
    for loc in locations:
        loc.pop("_photos", None)
        loc.pop("_manual", None)

    # 8. JSON schreiben
    data_dir = SITE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    map_data = {
        "locations": locations,
        "routes": routes,
        "articles": article_meta,
        "regions": all_regions,
        "years": all_years,
        "countries": all_countries,
        "stats": {
            "total_locations": len(locations),
            "total_distilleries": sum(1 for l in locations if l["type"] == "distillery"),
            "total_routes": len(routes),
            "total_articles": len(articles),
            "years_covered": f"{min(all_years)}-{max(all_years)}" if all_years else ""
        }
    }

    output_path = data_dir / "map-data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(map_data, f, ensure_ascii=False, indent=None)

    # Auch eine huebsche Version fuer Debugging
    debug_path = data_dir / "map-data-debug.json"
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(map_data, f, ensure_ascii=False, indent=2)

    # Auch in site-v2 schreiben (identische Kopie)
    site_v2_data_dir = PROJECT_DIR / "site-v2" / "data"
    if site_v2_data_dir.exists():
        import shutil
        shutil.copy2(output_path, site_v2_data_dir / "map-data.json")
        shutil.copy2(debug_path, site_v2_data_dir / "map-data-debug.json")
        print(f"  map-data.json auch in site-v2/data/ geschrieben")

    size_kb = output_path.stat().st_size / 1024
    print(f"  map-data.json geschrieben ({size_kb:.1f} KB)")
    print(f"  {map_data['stats']['total_locations']} Orte, "
          f"{map_data['stats']['total_distilleries']} Destillerien, "
          f"{map_data['stats']['total_routes']} Routen")

    return map_data


if __name__ == "__main__":
    build_map_data()
