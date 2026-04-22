"""
Backfill-Skript: Koordinaten für Destillerien ohne GPS-Daten via Nominatim/OSM ergänzen.

Verwendung:
    python scripts/backfill_distillery_coords.py

Was es tut:
    - Liest data/glossary/distilleries.json
    - Für jeden Eintrag OHNE coordinates.lat/lng: fragt Nominatim an
    - Trägt gefundene Koordinaten als {lat, lng, source: "nominatim", verified: false} ein
    - Schreibt die aktualisierten Daten zurück in distilleries.json
    - Gibt nicht auflösbare Einträge in scripts/backfill_unresolved.txt aus

Nominatim-TOS: max 1 Request/Sekunde, User-Agent mit Kontakt-E-Mail.
"""

import json
import time
import urllib.request
import urllib.parse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DISTILLERIES_FILE = PROJECT_DIR / "data" / "glossary" / "distilleries.json"
UNRESOLVED_FILE = Path(__file__).parent / "backfill_unresolved.txt"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "whisky-magazin (steffenhefter@googlemail.com)"
SLEEP_BETWEEN = 1.1  # Nominatim TOS: max 1 req/sec


def query_nominatim(name, country):
    """Fragt Nominatim nach Koordinaten für eine Destillerie."""
    country_map = {
        "scotland": "Scotland",
        "ireland": "Ireland",
        "germany": "Germany",
        "japan": "Japan",
        "usa": "United States",
        "oesterreich": "Austria",
    }
    country_en = country_map.get(country, country)

    # Versuche erst mit "Distillery"-Suffix, dann ohne
    queries = [
        f"{name} Distillery {country_en}",
        f"{name} {country_en}",
    ]

    for q in queries:
        params = urllib.parse.urlencode({
            "q": q,
            "format": "json",
            "limit": 1,
            "addressdetails": 0,
        })
        url = f"{NOMINATIM_URL}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data:
                result = data[0]
                lat = float(result["lat"])
                lng = float(result["lon"])
                print(f"  ✓ {name}: lat={lat:.4f}, lng={lng:.4f}  (via '{q}')")
                return {"lat": round(lat, 5), "lng": round(lng, 5), "source": "nominatim", "verified": False}
        except Exception as e:
            print(f"  FEHLER bei Query '{q}': {e}")
        time.sleep(SLEEP_BETWEEN)

    return None


def main():
    if not DISTILLERIES_FILE.exists():
        print(f"Datei nicht gefunden: {DISTILLERIES_FILE}")
        sys.exit(1)

    with open(DISTILLERIES_FILE, "r", encoding="utf-8") as f:
        distilleries = json.load(f)

    print(f"Geladene Destillerien: {len(distilleries)}")

    missing = [d for d in distilleries if not (d.get("coordinates") or {}).get("lat")]
    already_done = len(distilleries) - len(missing)
    print(f"  Bereits mit Koordinaten: {already_done}")
    print(f"  Ohne Koordinaten (werden gesucht): {len(missing)}")

    if not missing:
        print("\nAlle Destillerien haben bereits Koordinaten. Nichts zu tun.")
        return

    unresolved = []
    for item in missing:
        name = item.get("name", "")
        country_id = item.get("country_id", "scotland")
        print(f"\nSuche: {name} ({country_id})")
        coords = query_nominatim(name, country_id)
        time.sleep(SLEEP_BETWEEN)

        if coords:
            item["coordinates"] = coords
        else:
            print(f"  ✗ Nicht gefunden: {name}")
            unresolved.append(f"{item.get('id', '?')} | {name} | {country_id}")

    # Aktualisierte Daten zurückschreiben
    with open(DISTILLERIES_FILE, "w", encoding="utf-8") as f:
        json.dump(distilleries, f, ensure_ascii=False, indent=2)
    print(f"\n✓ distilleries.json aktualisiert.")

    if unresolved:
        with open(UNRESOLVED_FILE, "w", encoding="utf-8") as f:
            f.write("# Nicht aufgelöste Destillerien – Koordinaten bitte manuell im Admin eintragen\n")
            f.write("\n".join(unresolved))
        print(f"✗ {len(unresolved)} nicht aufgelöste Einträge → {UNRESOLVED_FILE}")
        for u in unresolved:
            print(f"  - {u}")
    else:
        print("✓ Alle Destillerien aufgelöst.")

    print(f"\nFertig. {len(missing) - len(unresolved)}/{len(missing)} Koordinaten ergänzt.")


if __name__ == "__main__":
    main()
