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
import urllib.request
import urllib.parse
import json as _json
from pathlib import Path

# Kompatibilitäts-Shim: requests-ähnliche get()-Funktion via urllib
class _FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
    def json(self):
        return self._data

class _Requests:
    def get(self, url, params=None, headers=None, timeout=10):
        if params:
            url = url + '?' + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return _FakeResponse(resp.status, _json.loads(resp.read()))
        except Exception:
            return _FakeResponse(0, {})

requests = _Requests()


# ─────────────────────────────────────────────────────────────────
# 1. Brand-spezifische Queries  →  was Unsplash wirklich findet
# ─────────────────────────────────────────────────────────────────
BRAND_QUERIES = {
    # Islay – Landschaften & Küsten, KEINE Flaschen
    "lagavulin":     "lagavulin bay islay coast scotland",
    "laphroaig":     "islay south coast rocky shore scotland",
    "ardbeg":        "islay dramatic coastline atlantic waves",
    "bowmore":       "bowmore village islay harbour scotland",
    "bruichladdich": "islay west coast white buildings atlantic",
    "bunnahabhain":  "islay north coast remote bay scotland",
    "caol ila":      "islay sound view jura scotland coast",
    "kilchoman":     "islay farm machir bay atlantic beach",
    # Speyside – Flüsse, Täler, Natur
    "macallan":      "speyside estate mansion river scotland",
    "glenfiddich":   "dufftown speyside valley river scotland",
    "glenlivet":     "glenlivet glen river valley green hills",
    "aberlour":      "aberlour village speyside river autumn",
    "glenfarclas":   "speyside ben rinnes mountain heather",
    "balvenie":      "dufftown speyside castle ruins scotland",
    "glen grant":    "speyside garden river peaceful landscape",
    # Highlands – Berge, Glens, dramatische Natur
    "glenmorangie":  "tain ross shire highland coast scotland",
    "dalmore":       "cromarty firth highland scotland coast",
    "balblair":      "dornoch firth highland landscape scotland",
    "edradour":      "pitlochry highland autumn river scotland",
    # Skye & Inseln
    "talisker":      "isle of skye coast cliffs carbost bay",
    "tobermory":     "tobermory colourful harbour mull scotland",
    "arran":         "arran island goatfell mountain scotland",
    "isle of arran": "arran island coast holy isle scotland",
    # Campbeltown
    "springbank":    "campbeltown harbour kintyre coast",
    "glengyle":      "kintyre peninsula coast campbeltown",
    "glen scotia":   "campbeltown harbour fishing boats scotland",
    # Orkney / Nordost
    "highland park": "orkney kirkwall harbour cathedral scotland",
    "scapa":         "scapa flow orkney coast dramatic sky",
    # Edinburgh / Glasgow
    "holyrood":      "edinburgh holyrood park arthurs seat",
    "auchentoshan":  "glasgow riverside architecture scotland",
    "clydeside":     "glasgow river clyde waterfront cityscape",
    "glenkinchie":   "east lothian countryside rolling hills",
    # Oban
    "oban":          "oban harbour bay boats scotland sunset",
    # Ben Nevis
    "ben nevis":     "ben nevis mountain fort william snow",
    # Irland
    "teeling":       "dublin liberties cobblestone streets",
    "jameson":       "dublin architecture evening river liffey",
    "bushmills":     "antrim coast giants causeway ireland",
    "midleton":      "cork countryside green ireland river",
    "redbreast":     "ireland countryside stone walls green",
    # USA – Landschaft, keine Flaschen
    "buffalo trace": "kentucky horse farm rolling green hills",
    "woodford":      "kentucky bluegrass countryside stone fence",
    "maker":         "kentucky red barn bourbon trail autumn",
    "jack daniel":   "tennessee lynchburg countryside hills",
    "four roses":    "kentucky bluegrass river countryside",
    "wild turkey":   "kentucky river cliffs autumn foliage",
    # Japan
    "nikka":         "hokkaido japan forest mountain stream",
    "suntory":       "yamazaki japan bamboo forest mountain",
    "yamazaki":      "japan mountains river valley autumn",
    "hakushu":       "japan forest mountain stream minami alps",
}

# Wenn Unsplash für den Brand-Namen keine Treffer liefert,
# wird diese generische (Unsplash-taugliche) Query probiert.
BRAND_FALLBACK = {
    "lagavulin":     "islay coast dramatic atlantic waves rocks",
    "laphroaig":     "islay southern coast seashore landscape",
    "ardbeg":        "islay rugged coast atlantic scotland",
    "bowmore":       "islay loch indaal calm water evening",
    "bruichladdich": "islay atlantic coast wild beach",
    "bunnahabhain":  "islay northeast coast remote bay",
    "caol ila":      "islay sound water crossing jura view",
    "kilchoman":     "islay west beach atlantic sunset",
    "macallan":      "speyside river spey landscape autumn",
    "glenfiddich":   "dufftown village speyside autumn landscape",
    "glenlivet":     "speyside glen river green valley hills",
    "aberlour":      "speyside autumn river village scotland",
    "talisker":      "skye dramatic coastline cuillin mountains",
    "arran":         "arran scotland coast goatfell mountain",
    "isle of arran": "arran island coast holy isle view",
    "springbank":    "kintyre peninsula coast atlantic scotland",
    "glengyle":      "campbeltown kintyre harbour fishing boats",
    "glen scotia":   "campbeltown harbour boats kintyre coast",
    "highland park": "orkney islands cliffs coast dramatic sky",
    "scapa":         "orkney landscape green coast dramatic",
    "holyrood":      "edinburgh old town calton hill view",
    "auchentoshan":  "glasgow architecture kelvingrove park",
    "clydeside":     "glasgow river clyde architecture evening",
    "oban":          "oban bay boats scotland evening coast",
    "ben nevis":     "glen nevis river mountain autumn colour",
    "teeling":       "dublin bridges river liffey evening",
    "jameson":       "dublin temple bar cobblestones evening",
    "bushmills":     "antrim coast cliffs ireland dramatic",
    "glenmorangie":  "tain highlands coast ross shire landscape",
    "buffalo trace": "kentucky rolling green hills horse farm",
    "woodford":      "kentucky autumn trees stone wall countryside",
    "maker":         "kentucky red countryside rolling hills",
    "jack daniel":   "tennessee rolling hills countryside green",
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
    "cocktail":       "cocktail bar evening warm atmosphere",
    "tasting":        "whisky tasting flight glasses amber dark",
    "tasting notes":  "whisky glass amber dram closeup wood",
    "verkostung":     "whisky glass amber dram closeup",
    "hype":           "whisky bottle glass elegant amber dark",
    "review":         "whisky glass closeup amber dram bokeh",
    "bewertung":      "whisky glass pouring amber dram dark",
    "flasche":        "whisky bottle elegant dark amber glass",
    "bottle":         "single malt whisky bottle glass amber",
    "käse":           "cheese board rustic wooden table artisan",
    "pairing":        "food tasting table evening candlelight",
    "bar":            "cozy pub interior warm evening scotland",
    "wohnmobil":      "campervan scotland highland road trip",
    "mietwagen":      "road trip scotland single track highland",
    "fähre":          "ferry scotland sea island crossing",
    "faehre":         "ferry scotland sea crossing waves",
    "wandern":        "hiking scotland highland trail misty",
    "strand":         "white sand beach scotland hebrides",
    "winter":         "scotland winter snow glen frost mountains",
    "weihnacht":      "christmas market winter lights festive",
    "frühling":       "spring heather scotland hills blossom",
    "herbst":         "autumn trees scotland loch reflection",
    "luxus":          "scottish castle luxury loch reflection",
    "schloss":        "castle scotland historic loch evening",
    "familie":        "scotland loch family landscape castle",
    "halloween":      "edinburgh night gothic architecture",
    "destillerie":    "distillery copper pot still interior",
    "distillery":     "distillery interior copper pot still",
    "single malt":    "scotland landscape glen river atmospheric",
    "bourbon":        "bourbon barrel rickhouse warehouse wood",
    "torfrauch":      "peat bog scotland landscape islay",
    "torf":           "peat cutting scotland islay landscape",
    "geschichte":     "historic stone building scotland landscape",
    "marathon":       "speyside landscape river trail scotland",
    "tour":           "scotland driving landscape road highland",
    "trail":          "scotland landscape path trail highland",
}

# ─────────────────────────────────────────────────────────────────
# 4. Kategorie-Fallback (letzter Ausweg)
# ─────────────────────────────────────────────────────────────────
CATEGORY_FALLBACK = {
    "whisky":    "whisky glass amber dram dark elegant",
    "reise":     "scotland landscape road highlands misty",
    "natur":     "scotland wilderness nature mountains loch",
    "lifestyle": "cozy evening interior warm atmosphere table",
    "urlaub":    "scotland loch castle landscape reflection",
}

# Titel-Keywords die auf einen Tasting/Flasche-Artikel hinweisen
TASTING_KEYWORDS = [
    "hype", "gerechtfertigt", "review", "bewertung", "tasting", "verkostung",
    "flasche", "bottle", "trinken", "dram", "notes", "aroma", "finish",
    "ist es gut", "lohnt", "wert", "empfehlung", "guide", "einsteiger"
]


def find_image_queries(article):
    """
    Gibt eine priorisierte Liste von Suchanfragen zurück.
    Die erste liefernde Query mit unbenutztem Foto gewinnt.
    """
    title_lower = article.get("title", "").lower()
    tags = [t.lower() for t in article.get("tags", [])]
    all_text = title_lower + " " + " ".join(tags)

    queries = []

    # Erkennung: Ist das ein Tasting/Bewertungs-Artikel (nicht Reise)?
    is_tasting_article = any(kw in all_text for kw in TASTING_KEYWORDS)
    article_type = article.get("type", "")
    is_travel = article_type in ("reisebericht", "reise") or "reise" in article.get("category", "").lower()

    # 1. Brand → für Reise-Artikel: Landschaft | für Tasting-Artikel: Glas/Flasche
    for brand, query in BRAND_QUERIES.items():
        if brand in all_text:
            if is_tasting_article and not is_travel:
                # Glas/Tasting-Bild mit Brand-Region als Kontext
                queries.append(f"whisky glass amber dram dark elegant closeup")
                queries.append(f"single malt whisky bottle glass bokeh")
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


def get_unsplash_candidates(query, api_key, per_page=4):
    """
    Liefert eine Liste von Bild-Kandidaten für die manuelle Auswahl im Admin-UI.
    Kein Duplikat-Filter, kein LoremFlickr-Fallback (UI zeigt Leer-Zustand sinnvoller an).
    """
    if not api_key or api_key in ("", "DEIN_UNSPLASH_API_KEY_OPTIONAL"):
        return []
    if not query or not query.strip():
        return []

    try:
        response = requests.get(
            "https://api.unsplash.com/search/photos",
            params={
                "query": query.strip(),
                "per_page": max(1, min(per_page, 12)),
                "orientation": "landscape",
                "content_filter": "high",
            },
            headers={"Authorization": f"Client-ID {api_key}"},
            timeout=10,
        )
        if response.status_code != 200:
            return []

        results = response.json().get("results", [])
        candidates = []
        for p in results:
            photographer = p["user"]["name"]
            photo_link = p["links"]["html"]
            raw = p["urls"]["raw"]
            candidates.append({
                "photo_id": p["id"],
                "url_full": raw + "?w=1200&h=630&fit=crop&crop=entropy&auto=format&q=80",
                "url_small": raw + "?w=400&h=225&fit=crop&crop=entropy&auto=format&q=70",
                "photographer": photographer,
                "description": p.get("alt_description") or p.get("description") or "",
                "attribution": (
                    f'Foto von <a href="{photo_link}?utm_source=whisky_magazin'
                    f'&utm_medium=referral">{photographer}</a> auf '
                    f'<a href="https://unsplash.com/?utm_source=whisky_magazin'
                    f'&utm_medium=referral">Unsplash</a>'
                ),
            })
        return candidates
    except Exception as e:
        print(f"    Unsplash Candidates Fehler: {e}")
        return []


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
