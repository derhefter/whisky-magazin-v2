"""
Image Fetcher – Whisky Magazin
==============================
Suche-Hierarchie pro Artikel:
  1. Brand/Destillerie-Name  (spezifischste Query)
  2. Brand-Fallback           (Unsplash-taugliche Regionalkeywords)
  3. Ort / Region
  4. Themen-Keyword
  5. Kategorie-Fallback       (generisch)

Duplikat-Schutz: Einmal verwendete Unsplash-Photo-IDs werden
übersprungen → jeder Artikel bekommt ein eigenes Bild.
"""

import re
import requests
from pathlib import Path


# ─────────────────────────────────────────────────────────────────
# 1. Brand-spezifische Queries  →  was Unsplash wirklich findet
# ─────────────────────────────────────────────────────────────────
BRAND_QUERIES = {
    # Islay
    "lagavulin":     "lagavulin distillery islay",
    "laphroaig":     "laphroaig distillery islay",
    "ardbeg":        "ardbeg distillery islay",
    "bowmore":       "bowmore distillery islay",
    "bruichladdich": "bruichladdich distillery islay",
    "bunnahabhain":  "bunnahabhain distillery islay",
    "caol ila":      "caol ila distillery islay",
    "kilchoman":     "kilchoman distillery islay",
    # Speyside
    "macallan":      "macallan scotch whisky",
    "glenfiddich":   "glenfiddich whisky speyside",
    "glenlivet":     "glenlivet whisky speyside valley",
    "aberlour":      "aberlour speyside distillery",
    "glenfarclas":   "speyside malt whisky distillery",
    "balvenie":      "balvenie dufftown distillery",
    "glen grant":    "glen grant speyside",
    # Highlands
    "glenmorangie":  "glenmorangie distillery highlands",
    "dalmore":       "dalmore whisky highland",
    "balblair":      "balblair highland distillery",
    "edradour":      "edradour pitlochry distillery",
    # Skye & Inseln
    "talisker":      "talisker distillery skye coast",
    "tobermory":     "tobermory mull island",
    "arran":         "arran island scotland distillery",
    "isle of arran": "arran island scotland",
    # Campbeltown
    "springbank":    "springbank distillery campbeltown",
    "glengyle":      "campbeltown kintyre scotland",
    "glen scotia":   "campbeltown harbour scotland",
    # Orkney / Nordost
    "highland park": "highland park distillery orkney",
    "scapa":         "scapa orkney distillery",
    # Edinburgh / Glasgow
    "holyrood":      "holyrood distillery edinburgh",
    "auchentoshan":  "auchentoshan distillery glasgow",
    "clydeside":     "clydeside distillery glasgow",
    "glenkinchie":   "glenkinchie distillery lowlands",
    # Oban
    "oban":          "oban distillery harbour",
    # Ben Nevis
    "ben nevis":     "ben nevis fort william mountain",
    # Irland
    "teeling":       "teeling distillery dublin",
    "jameson":       "jameson distillery dublin ireland",
    "bushmills":     "bushmills distillery antrim ireland",
    "midleton":      "midleton distillery cork ireland",
    "redbreast":     "ireland whiskey pot still",
    # USA
    "buffalo trace": "buffalo trace distillery kentucky",
    "woodford":      "woodford reserve distillery kentucky",
    "maker":         "makers mark distillery kentucky",
    "jack daniel":   "jack daniels distillery tennessee",
    "four roses":    "four roses distillery kentucky",
    "wild turkey":   "wild turkey distillery kentucky",
    # Japan
    "nikka":         "nikka distillery japan",
    "suntory":       "suntory yamazaki distillery japan",
    "yamazaki":      "yamazaki distillery japan mountains",
    "hakushu":       "hakushu distillery japan forest",
}

# Wenn Unsplash für den Brand-Namen keine Treffer liefert,
# wird diese generische (Unsplash-taugliche) Query probiert.
BRAND_FALLBACK = {
    "lagavulin":     "islay coast dramatic rocks scotland",
    "laphroaig":     "islay coast sea spray rocks",
    "ardbeg":        "islay coast whisky landscape",
    "bowmore":       "islay village harbour boat",
    "bruichladdich": "islay white building atlantic coast",
    "bunnahabhain":  "islay north coast landscape",
    "caol ila":      "islay sound ferry distillery",
    "kilchoman":     "islay farm atlantic ocean",
    "macallan":      "speyside single malt whisky amber glass",
    "glenfiddich":   "speyside valley dufftown scotland river",
    "glenlivet":     "speyside glen river valley green",
    "aberlour":      "speyside river village autumn",
    "talisker":      "isle of skye dramatic sea cliffs",
    "arran":         "arran island sea scotland lighthouse",
    "isle of arran": "arran island scotland loch",
    "springbank":    "kintyre peninsula coast scotland sea",
    "glengyle":      "campbeltown kintyre coast harbour",
    "glen scotia":   "campbeltown scotland harbour sea",
    "highland park": "orkney islands dramatic coast cliffs",
    "scapa":         "orkney scotland green landscape sea",
    "holyrood":      "edinburgh old town night lights",
    "auchentoshan":  "glasgow cityscape river scotland",
    "clydeside":     "glasgow river clyde waterfront night",
    "oban":          "oban harbour boats scotland coast",
    "ben nevis":     "glen nevis mountain scotland autumn",
    "teeling":       "dublin ireland ha penny bridge night",
    "jameson":       "dublin cobblestones pub ireland",
    "bushmills":     "antrim coast ireland landscape",
    "glenmorangie":  "ross shire highlands scotland coast",
    "buffalo trace": "kentucky horse farm rolling hills",
    "woodford":      "kentucky bluegrass hills autumn",
    "maker":         "kentucky countryside bourbon trail",
    "jack daniel":   "tennessee hills countryside",
}


# ─────────────────────────────────────────────────────────────────
# 2. Orte / Regionen
# ─────────────────────────────────────────────────────────────────
LOCATION_QUERIES = {
    "islay":        "islay scotland coast landscape",
    "speyside":     "speyside scotland river valley autumn",
    "highlands":    "scottish highlands glen mist dramatic",
    "highland":     "scottish highlands mountains valley",
    "lowlands":     "scottish lowlands green countryside",
    "campbeltown":  "campbeltown kintyre peninsula sea",
    "edinburgh":    "edinburgh castle old town scotland",
    "glasgow":      "glasgow scotland architecture river",
    "skye":         "isle of skye scotland dramatic cliffs",
    "orkney":       "orkney islands sea cliffs scotland",
    "mull":         "mull island scotland sea mountains",
    "arran":        "arran island scotland coast",
    "oban":         "oban harbour scotland boats sea",
    "trossachs":    "loch lomond trossachs mountains",
    "loch ness":    "loch ness scotland misty calm water",
    "loch":         "scottish loch reflection mountains mist",
    "eilean donan": "eilean donan castle scotland",
    "dublin":       "dublin ireland architecture evening",
    "ireland":      "ireland green coast cliffs atlantic",
    "irland":       "ireland countryside cliffs sea",
    "kentucky":     "kentucky rolling green hills autumn",
    "tennessee":    "tennessee countryside misty hills",
    "berlin":       "berlin germany architecture skyline",
    "spreewald":    "spreewald germany canals nature",
    "dresden":      "dresden germany frauenkirche elbe",
}


# ─────────────────────────────────────────────────────────────────
# 3. Themen / Aktivitäten
# ─────────────────────────────────────────────────────────────────
TOPIC_QUERIES = {
    "wildlife":       "red deer highland scotland dramatic",
    "hirsche":        "red deer stag highland scotland autumn",
    "adler":          "golden eagle scotland sky dramatic",
    "robben":         "grey seals scotland coast rocks",
    "cocktail":       "whisky cocktail crystal glass amber",
    "tasting":        "whisky tasting row glasses amber",
    "käse":           "cheese board rustic wood wine",
    "pairing":        "whisky food pairing table evening",
    "bar":            "whisky bar dark oak interior moody",
    "wohnmobil":      "campervan scotland highland road trip",
    "mietwagen":      "road trip scotland single track highland",
    "fähre":          "ferry scotland sea island crossing",
    "faehre":         "ferry scotland sea crossing waves",
    "wandern":        "hiking scotland highland trail misty",
    "strand":         "white sand beach scotland hebrides",
    "winter":         "scotland winter snow glen frost",
    "weihnacht":      "christmas market winter lights festive",
    "frühling":       "spring heather scotland hills blossom",
    "herbst":         "autumn trees scotland loch reflection",
    "luxus":          "scottish castle luxury loch reflection",
    "schloss":        "castle scotland historic loch",
    "familie":        "scotland loch family landscape castle",
    "halloween":      "edinburgh halloween ghost tour",
    "destillerie":    "whisky distillery copper pot still",
    "distillery":     "whisky distillery copper still interior",
    "single malt":    "single malt scotch amber glass backlit",
    "bourbon":        "bourbon barrel warehouse rick house",
    "torfrauch":      "peat fire scotland smoky whisky",
    "torf":           "peat cutting scotland islay",
    "geschichte":     "whisky distillery historic stone scotland",
    "marathon":       "speyside distillery trail landscape",
    "tour":           "scotland whisky landscape driving tour",
    "trail":          "scotland whisky trail landscape path",
}

# ─────────────────────────────────────────────────────────────────
# 4. Kategorie-Fallback (letzter Ausweg)
# ─────────────────────────────────────────────────────────────────
CATEGORY_FALLBACK = {
    "whisky":    "scotch whisky amber glass barrel aged",
    "reise":     "scotland landscape road highlands misty",
    "natur":     "scotland wilderness nature mountains loch",
    "lifestyle": "whisky glass lifestyle evening moody",
    "urlaub":    "scotland loch castle landscape reflection",
}


def find_image_queries(article):
    """
    Gibt eine priorisierte Liste von Suchanfragen zurück.
    Die erste liefernde Query mit unbenutztem Foto gewinnt.
    """
    title_lower = article.get("title", "").lower()
    tags = [t.lower() for t in article.get("tags", [])]
    all_text = title_lower + " " + " ".join(tags)

    queries = []

    # 1. Brand → Brand-Fallback
    for brand, query in BRAND_QUERIES.items():
        if brand in all_text:
            queries.append(query)
            if brand in BRAND_FALLBACK:
                queries.append(BRAND_FALLBACK[brand])
            break

    # 2. Ort / Region
    for location, query in LOCATION_QUERIES.items():
        if location in all_text and query not in queries:
            queries.append(query)
            break

    # 3. Thema
    for topic, query in TOPIC_QUERIES.items():
        if topic in all_text and query not in queries:
            queries.append(query)
            break

    # 4. Kategorie-Fallback (immer dabei)
    category = article.get("category", "").lower()
    fallback = CATEGORY_FALLBACK.get(category, "scotland whisky landscape")
    if fallback not in queries:
        queries.append(fallback)

    return queries


# Rückwärtskompatibilität für dry-run in add_images.py
def find_image_query(article):
    """Gibt die erste (spezifischste) Query zurück."""
    return find_image_queries(article)[0]


def get_unsplash_image_url(queries, api_key=None, used_photo_ids=None):
    """
    Probiert jede Query in Reihenfolge bis ein noch-nicht-genutztes Foto gefunden wird.
    used_photo_ids wird in-place aktualisiert → Duplikatschutz für den Gesamtlauf.
    """
    if used_photo_ids is None:
        used_photo_ids = set()
    if isinstance(queries, str):
        queries = [queries]

    if api_key and api_key not in ("", "DEIN_UNSPLASH_API_KEY_OPTIONAL"):
        for query in queries:
            try:
                response = requests.get(
                    "https://api.unsplash.com/search/photos",
                    params={
                        "query": query,
                        "per_page": 20,
                        "orientation": "landscape",
                        "content_filter": "high",
                    },
                    headers={"Authorization": f"Client-ID {api_key}"},
                    timeout=10,
                )

                if response.status_code == 200:
                    results = response.json().get("results", [])
                    # Nur ungenutzte Fotos, sortiert nach Downloads (Qualität)
                    available = sorted(
                        [p for p in results if p["id"] not in used_photo_ids],
                        key=lambda p: p.get("downloads", 0),
                        reverse=True,
                    )
                    if available:
                        best = available[0]
                        used_photo_ids.add(best["id"])
                        photographer = best["user"]["name"]
                        photo_link = best["links"]["html"]
                        img_url = (
                            best["urls"]["raw"]
                            + "?w=1200&h=630&fit=crop&crop=entropy&auto=format&q=80"
                        )
                        print(f"    Query '{query}' → {best['id'][:20]}… ({photographer})")
                        return {
                            "url": img_url,
                            "photographer": photographer,
                            "photo_id": best["id"],
                            "attribution": (
                                f'Foto von <a href="{photo_link}?utm_source=whisky_magazin'
                                f'&utm_medium=referral">{photographer}</a> auf '
                                f'<a href="https://unsplash.com/?utm_source=whisky_magazin'
                                f'&utm_medium=referral">Unsplash</a>'
                            ),
                        }
                    elif results:
                        print(f"    Query '{query}': {len(results)} Fotos, alle schon genutzt")
                    else:
                        print(f"    Query '{query}': 0 Treffer")

                elif response.status_code == 401:
                    print("    Unsplash: Ungültiger API-Key. Wechsle zu LoremFlickr.")
                    break
                elif response.status_code == 429:
                    print("    Unsplash: Rate-Limit erreicht.")
                    break

            except Exception as e:
                print(f"    Unsplash Fehler: {e}")

    # Letzter Ausweg: LoremFlickr (keyword-basiert, kein API-Key)
    keywords = ",".join(queries[-1].split()[:3])
    print(f"    Fallback LoremFlickr: '{keywords}'")
    return {
        "url": f"https://loremflickr.com/1200/630/{keywords}",
        "photographer": "",
        "photo_id": None,
        "attribution": "",
    }


def download_image(image_url, save_path):
    """Lädt ein Bild herunter, prüft Mindestgröße."""
    try:
        response = requests.get(image_url, timeout=30, allow_redirects=True)
        if response.status_code == 200 and len(response.content) > 5000:
            with open(save_path, "wb") as f:
                f.write(response.content)
            return True
        print(f"    Fehler: HTTP {response.status_code}, {len(response.content)} Bytes")
    except Exception as e:
        print(f"    Download fehlgeschlagen: {e}")
    return False


def _safe_slug(text):
    """ASCII-sicherer Dateiname aus beliebigem Text."""
    text = text.lower()
    for src, dst in [("ä","ae"),("ö","oe"),("ü","ue"),("ß","ss"),("&","-"),("'","")]:
        text = text.replace(src, dst)
    text = re.sub(r"[^a-z0-9\-]", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:60]


def fetch_and_save_image(article, config, images_dir, used_photo_ids=None):
    """
    Findet Query-Kette → holt Unsplash-URL (duplikatfrei) → lädt runter → speichert.
    Gibt Dict mit url, alt, credit, photo_id zurück. None bei Fehler.
    """
    if used_photo_ids is None:
        used_photo_ids = set()

    images_dir = Path(images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    meta_slug = article.get("meta", {}).get("slug", "")
    slug = _safe_slug(meta_slug) if meta_slug else _safe_slug(article.get("title", "artikel"))
    save_path = images_dir / f"{slug}.jpg"

    if save_path.exists():
        photo_id = article.get("image_photo_id")
        if photo_id:
            used_photo_ids.add(photo_id)
        print(f"    Vorhanden: {save_path.name}")
        return {
            "url": f"/images/{slug}.jpg",
            "alt": article.get("title", ""),
            "credit": article.get("image_credit", ""),
            "photo_id": photo_id,
        }

    unsplash_key = config.get("content_settings", {}).get("unsplash_api_key", "")
    queries = find_image_queries(article)
    print(f"    Queries: {queries[:2]}")

    image_data = get_unsplash_image_url(queries, unsplash_key, used_photo_ids)
    print(f"    Lade: {image_data['url'][:70]}...")

    if not download_image(image_data["url"], save_path):
        return None

    size_kb = save_path.stat().st_size // 1024
    print(f"    OK: {save_path.name} ({size_kb} KB)")
    return {
        "url": f"/images/{slug}.jpg",
        "alt": article.get("title", ""),
        "credit": image_data.get("attribution", ""),
        "photo_id": image_data.get("photo_id"),
    }
