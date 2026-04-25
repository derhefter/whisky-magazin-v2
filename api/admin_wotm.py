"""Vercel Serverless Function: Whisky of the Month + Newsletter management."""
import base64
import hashlib
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

ADMIN_PASSWORD  = os.environ.get("DASHBOARD_PASSWORD", "").strip()
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO     = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
GITHUB_BRANCH   = os.environ.get("GITHUB_BRANCH", "main").strip()
BREVO_API_KEY   = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_LIST_ID   = os.environ.get("BREVO_LIST_ID", "3").strip()
SITE_URL        = os.environ.get("SITE_URL", "https://www.whisky-reise.com").strip()
AMAZON_TAG      = "whiskyreise74-21"
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "").strip()
OPENAI_MODEL    = "gpt-4o-mini"
KEY_VERSION     = os.environ.get("ADMIN_KEY_VERSION", "1").strip()

TOKEN_TTL = 8 * 3600  # 8h, war 24h
WOTM_FILE = "data/whisky-of-the-month.json"


# ── Auth ──────────────────────────────────────────────────────────────────────

def _verify_token(token: str) -> bool:
    if not ADMIN_PASSWORD:
        return False
    if not token or "." not in token:
        return False
    parts = token.split(".", 1)
    if len(parts) != 2:
        return False
    ts_str, _ = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    if time.time() - ts > TOKEN_TTL:
        return False
    key = f"{ADMIN_PASSWORD}:{KEY_VERSION}".encode()
    sig = hmac.new(key, ts_str.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(token, f"{ts_str}.{sig}")


ALLOWED_ORIGINS = [
    "https://www.whisky-reise.com",
    "https://whisky-reise.com",
    "http://localhost:8000",
]


def _cors_headers(origin=""):
    allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-admin-token",
    }


# ── GitHub helpers ─────────────────────────────────────────────────────────────

def _github_get(path):
    sep = "&" if "?" in path else "?"
    if path.startswith("contents/"):
        path = f"{path}{sep}ref={GITHUB_BRANCH}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{path}"
    req = Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "WhiskyMagazin-Dashboard",
    })
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"{e.code}: {body[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _github_put(path, content_bytes, sha_or_none, message):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("ascii"),
        "branch": GITHUB_BRANCH,
    }
    if sha_or_none:
        payload["sha"] = sha_or_none
    req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "WhiskyMagazin-Dashboard",
    }, method="PUT")
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": f"{e.code}: {body[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _load_wotm_data():
    file_data = _github_get(f"contents/{WOTM_FILE}")
    if "error" in file_data:
        if "404" in str(file_data.get("error", "")):
            return {"entries": {}}, None
        return None, None
    try:
        raw = base64.b64decode(file_data["content"].replace("\n", "")).decode("utf-8")
        return json.loads(raw), file_data.get("sha")
    except Exception:
        return {"entries": {}}, file_data.get("sha")


def _save_wotm_data(data, sha, message):
    content_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    result = _github_put(WOTM_FILE, content_bytes, sha, message)
    return result.get("error") if "error" in result else None


# ── Affiliate link helper ──────────────────────────────────────────────────────

def _make_affiliate_link(whisky_name):
    encoded = quote(whisky_name, safe="")
    return f"https://www.amazon.de/s?k={encoded}&tag={AMAZON_TAG}"


# ── OpenAI text helpers ────────────────────────────────────────────────────────

def _call_openai(messages, max_tokens=400):
    """Call OpenAI chat completions API. Returns text or None on error."""
    if not OPENAI_API_KEY:
        return None
    payload = json.dumps({
        "model": OPENAI_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }).encode("utf-8")
    req = Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _polish_kommentar(raw_text, whisky_name):
    """Reformulate rough notes into polished Steffen & Ellas newsletter style."""
    if not raw_text.strip():
        return raw_text
    result = _call_openai([
        {"role": "system", "content": (
            "Du schreibst für den monatlichen Newsletter 'Whisky & Schottland' von Steffen und Ellas, "
            "zwei leidenschaftlichen Whisky-Enthusiasten und Schottland-Reisenden. "
            "Stil: warm, persönlich, Wir-Form ('wir haben', 'uns hat'), wie ein Brief von Freunden. "
            "Max. 3–4 kurze, flüssige Sätze. Keine Überschriften, kein Fettdruck, nur fließender Text. "
            "WICHTIG: Enthält der Text eine URL (http://... oder https://...), ignoriere sie vollständig – "
            "die Destillerie wird im Newsletter bereits separat verlinkt. "
            "Korrekte deutsche Umlaute (ä/ö/ü/ß) verwenden."
        )},
        {"role": "user", "content": (
            f"Formuliere diesen Kommentar zum Whisky des Monats '{whisky_name}' aus. "
            f"Die groben Notizen sollen zu einem persönlichen, einladenden Text werden:\n\n{raw_text}"
        )},
    ], max_tokens=300)
    return result or raw_text


def _polish_specials(raw_text):
    """Reformulate rough specials notes into polished newsletter prose."""
    if not raw_text.strip():
        return raw_text
    result = _call_openai([
        {"role": "system", "content": (
            "Du schreibst für den monatlichen Newsletter 'Whisky & Schottland' von Steffen und Ellas. "
            "Stil: warm, persönlich, Wir-Form. Formuliere die Stichpunkte zu einladenden, kurzen Absätzen aus. "
            "Je Stichpunkt ein Absatz. Korrekte deutsche Umlaute (ä/ö/ü/ß)."
        )},
        {"role": "user", "content": (
            f"Formuliere diese Specials & News aus (je Stichpunkt/Zeile ein kurzer Absatz):\n\n{raw_text}"
        )},
    ], max_tokens=400)
    return result or raw_text


def _generate_intro(month_label, whisky_name, article_titles):
    """Generate a warm, personal newsletter intro for the given month."""
    articles_str = ", ".join(f'„{t}"' for t in article_titles[:3]) if article_titles else ""
    fallback = (
        f"der {month_label} ist da – und wir haben wieder einiges für euch: "
        f"unseren Whisky des Monats, neue Artikel und den üblichen Schottland-Moment."
    )
    if not OPENAI_API_KEY:
        return fallback
    result = _call_openai([
        {"role": "system", "content": (
            "Du schreibst den Einleitungstext des monatlichen Newsletters 'Whisky & Schottland' "
            "von Steffen und Ellas, zwei leidenschaftlichen Whisky-Enthusiasten und Schottland-Reisenden. "
            "Der Text kommt direkt nach 'Hallo ihr Lieben,' – also kein eigenes Hallo mehr. "
            "Stil: wie ein Brief von Freunden, die gerade aus Schottland schreiben. Warm, neugierig-machend. "
            "Max. 2–3 Sätze. Korrekte deutsche Umlaute (ä/ö/ü/ß)."
        )},
        {"role": "user", "content": (
            f"Schreibe den Einleitungstext für den {month_label}-Newsletter. "
            f"Unser Whisky des Monats ist der {whisky_name}."
            + (f" Neue Artikel diesen Monat: {articles_str}." if articles_str else "")
            + " Mach es persönlich und einladend, ohne zu viel vorwegzunehmen."
        )},
    ], max_tokens=120)
    return result or fallback


# ── GitHub: auto-fetch articles for newsletter ────────────────────────────────

def _fetch_month_articles(month_key):
    """Return up to 3 published articles for the newsletter.
    First tries the target month (YYYY-MM), then falls back to the 3 most
    recently published articles from any month.
    Each item: {title, url, teaser}
    """
    dir_data = _github_get("contents/articles")
    if not isinstance(dir_data, list):
        return []

    # All published JSON files (exclude drafts folder, dotfiles)
    all_files = sorted(
        [item for item in dir_data
         if (item.get("type") == "file"
             and item.get("name", "").endswith(".json")
             and not item.get("name", "").startswith(".")
             and "/drafts/" not in item.get("path", ""))],
        key=lambda x: x.get("name", ""),
        reverse=True,
    )

    # Prefer articles from the target month; fall back to most recent 3
    prefix = month_key + "-"
    month_files = [f for f in all_files if f["name"].startswith(prefix)]
    source_files = (month_files or all_files)[:3]

    teasers = []
    for item in source_files:
        file_data = _github_get(f"contents/{item['path']}")
        if isinstance(file_data, dict) and "error" not in file_data:
            try:
                raw = base64.b64decode(
                    file_data["content"].replace("\n", "")
                ).decode("utf-8")
                art = json.loads(raw)
                title  = art.get("title", "")
                meta   = art.get("meta", {}) or {}
                slug   = art.get("slug", "") or meta.get("slug", "")
                teaser = meta.get("teaser", "") or art.get("teaser", "")
                url    = f"{SITE_URL}/artikel/{slug}.html" if slug else SITE_URL
                if title:
                    teasers.append({"title": title, "url": url, "teaser": teaser})
            except Exception:
                pass
    return teasers


# ── Brevo Newsletter ───────────────────────────────────────────────────────────

def _brevo_create_campaign(subject, html_content, sender_name, sender_email):
    url = "https://api.brevo.com/v3/emailCampaigns"
    payload = json.dumps({
        "name": subject,
        "subject": subject,
        "sender": {"name": sender_name, "email": sender_email},
        "type": "classic",
        "htmlContent": html_content,
        "recipients": {"listIds": [int(BREVO_LIST_ID)]},
    }).encode("utf-8")
    req = Request(url, data=payload, headers={
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }, method="POST")
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return None, f"{e.code}: {body[:300]}"
    except Exception as e:
        return None, str(e)


def _brevo_send_now(campaign_id):
    url = f"https://api.brevo.com/v3/emailCampaigns/{campaign_id}/sendNow"
    req = Request(url, data=b"{}", headers={
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }, method="POST")
    try:
        with urlopen(req, timeout=15) as resp:
            return True, None
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"{e.code}: {body[:300]}"
    except Exception as e:
        return False, str(e)


# ── Newsletter HTML builder ────────────────────────────────────────────────────

import re as _re

def _linkify(text):
    """Convert bare URLs in text to clickable HTML links."""
    return _re.sub(
        r'(https?://[^\s<>"\']+)',
        r'<a href="\1" style="color:#C8963E;" target="_blank" rel="noopener noreferrer">\1</a>',
        text,
    )


def _build_newsletter_html(entry, month_label, article_teasers):
    whisky_name     = entry.get("whisky_name", "")
    destillerie     = (entry.get("destillerie", "") or "").strip()
    destillerie_url = (entry.get("destillerie_url", "") or "").strip()
    region          = entry.get("region", "")
    kommentar       = entry.get("kommentar", "")
    specials        = entry.get("specials", "")
    intro_text      = entry.get("intro_text", "")
    affiliate_link  = entry.get("affiliate_link", "") or _make_affiliate_link(whisky_name)

    # Tasting notes (optional)
    aroma      = (entry.get("aroma", "") or "").strip()
    geschmack  = (entry.get("geschmack", "") or "").strip()
    abgang     = (entry.get("abgang", "") or "").strip()
    bewertung  = entry.get("bewertung")   # 0–100
    alter      = entry.get("alter")       # Jahre
    abv        = entry.get("abv")         # %
    preis      = entry.get("preis_eur")   # €

    # Auto-detect: if destillerie field accidentally contains a URL, move it
    if destillerie and _re.match(r'https?://', destillerie):
        if not destillerie_url:
            destillerie_url = destillerie
        destillerie = ""

    # If destillerie name is empty but URL is set, use whisky_name as anchor
    if not destillerie and destillerie_url:
        destillerie = whisky_name

    if not intro_text:
        intro_text = (
            f"der {month_label} ist da \u2013 und wir haben wieder einiges f\u00fcr euch: "
            f"unseren Whisky des Monats, neue Artikel und den \u00fcblichen Schottland-Moment. "
            f"Kurz, knapp, hoffentlich lohnenswert."
        )

    # Make bare URLs in kommentar clickable (remaining ones after AI polishing)
    kommentar_html = _linkify(kommentar.replace("\n", "<br>")) if kommentar else ""

    # Photos – support data: URLs (local preview), relative paths, and full URLs
    photo_urls = entry.get("photo_urls") or []
    if not photo_urls and entry.get("photo_url"):
        photo_urls = [entry["photo_url"]]

    photos_html = ""
    valid_photos = []
    for url in photo_urls[:4]:
        if url.startswith("data:"):
            valid_photos.append(url)
        elif url.startswith("http"):
            valid_photos.append(url)
        elif url.startswith("/"):
            valid_photos.append(f"{SITE_URL}{url}")

    if valid_photos:
        n = len(valid_photos)
        if n == 1:
            photos_html = (
                f'<img src="{valid_photos[0]}" alt="{whisky_name}" '
                f'style="width:100%;max-width:560px;border-radius:8px;margin:12px 0 16px;display:block;">'
            )
        elif n == 2:
            # Eine Reihe, zwei gleichgroße Bilder (Container = 600px abzgl. Padding)
            cells = "".join(
                f'<td width="50%" style="padding:4px;vertical-align:top;">'
                f'<img src="{u}" alt="{whisky_name}" '
                f'style="width:100%;max-width:268px;border-radius:6px;display:block;"></td>'
                for u in valid_photos
            )
            photos_html = (
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                f'style="margin:12px 0 16px;"><tr>{cells}</tr></table>'
            )
        else:
            # 3 oder 4 Bilder: 2x2-Grid (3. Bild teilt sich die Reihe, ggf. mit leerem Cell)
            rows_html = ""
            for row_start in (0, 2):
                row_imgs = valid_photos[row_start:row_start + 2]
                cells = "".join(
                    f'<td width="50%" style="padding:4px;vertical-align:top;">'
                    f'<img src="{u}" alt="{whisky_name}" '
                    f'style="width:100%;max-width:268px;border-radius:6px;display:block;"></td>'
                    for u in row_imgs
                )
                # Bei nur 1 Bild in der zweiten Reihe (n=3): leere Zelle, damit das Bild links bündig bleibt
                if len(row_imgs) == 1:
                    cells += '<td width="50%" style="padding:4px;"></td>'
                rows_html += f'<tr>{cells}</tr>'
            photos_html = (
                f'<table width="100%" cellpadding="0" cellspacing="0" border="0" '
                f'style="margin:12px 0 16px;">{rows_html}</table>'
            )

    # Destillerie – link if URL provided
    if destillerie and destillerie_url:
        destillerie_html = (
            f'<a href="{destillerie_url}" style="color:#C8963E;text-decoration:none;" '
            f'target="_blank" rel="noopener noreferrer">{destillerie}</a>'
        )
    elif destillerie:
        destillerie_html = destillerie
    else:
        destillerie_html = ""

    # Sub-header: destillerie · region (never show raw URL)
    subheader_parts = []
    if destillerie_html:
        subheader_parts.append(destillerie_html)
    if region:
        subheader_parts.append(region)
    subheader = " &middot; ".join(subheader_parts)

    # ── Tasting card ──────────────────────────────────────────────────────────
    tasting_card = ""
    if aroma or geschmack or abgang or bewertung or preis:
        # Info line: REGION · X JAHRE · ABV% ABV
        info_parts = []
        if region:
            info_parts.append(region.upper())
        if alter:
            info_parts.append(f"{alter} JAHRE")
        if abv:
            info_parts.append(f"{abv}% ABV")
        info_line = " &middot; ".join(info_parts)

        # Tasting rows
        tasting_rows = ""
        for icon, label, text in [
            ("&#127800;", "Aroma",      aroma),
            ("&#9749;",   "Geschmack",  geschmack),
            ("&#10024;",  "Abgang",     abgang),
        ]:
            if not text:
                continue
            tasting_rows += f"""
              <tr>
                <td width="28" style="vertical-align:top;padding:0 10px 12px 0;font-size:1.1rem;white-space:nowrap;">{icon}</td>
                <td style="vertical-align:top;padding:0 0 12px 0;">
                  <p style="margin:0 0 3px;font-size:0.72rem;color:#C8963E;text-transform:uppercase;letter-spacing:1px;font-weight:700;">{label}</p>
                  <p style="margin:0;color:#2A2520;font-size:0.88rem;line-height:1.5;">{text}</p>
                </td>
              </tr>"""

        # Rating stars
        rating_html = ""
        if bewertung is not None:
            try:
                score = int(bewertung)
                filled = min(5, max(0, round(score / 20)))
                stars = "&#9733;" * filled + "&#9734;" * (5 - filled)
                rating_html = (
                    f'<p style="margin:10px 0 0;font-size:1.1rem;color:#C8963E;line-height:1;">'
                    f'{stars} '
                    f'<span style="font-size:0.88rem;font-weight:700;color:#2A2520;">{score}/100</span>'
                    f'</p>'
                )
            except Exception:
                pass

        # Price
        price_html = ""
        if preis:
            price_html = (
                f'<p style="margin:8px 0 0;font-size:0.88rem;color:#C8963E;font-weight:600;">'
                f'Ab ca. {preis}\u00a0\u20ac</p>'
            )

        tasting_card = f"""
              <div style="background:#FAF8F4;border-radius:8px;padding:18px 20px;margin:16px 0 4px;">
                {f'<p style="margin:0 0 14px;font-size:0.75rem;color:#9E9690;letter-spacing:0.5px;">{info_line}</p>' if info_line else ''}
                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                  {tasting_rows}
                </table>
                {rating_html}
                {price_html}
              </div>"""

    # ── Article teasers ───────────────────────────────────────────────────────
    articles_html = ""
    for a in article_teasers[:3]:
        title  = a.get("title", "")
        teaser = a.get("teaser", "")
        url    = a.get("url", "")
        if not url:
            slug = a.get("slug", "")
            url  = f"{SITE_URL}/artikel/{slug}.html" if slug else SITE_URL
        if not title:
            continue
        articles_html += f"""
        <div style="margin-bottom:16px;padding:16px;background:#FAF8F4;border-radius:8px;">
          <a href="{url}" style="font-family:Georgia,serif;font-size:1.05rem;font-weight:600;color:#2A2520;text-decoration:none;">{title}</a>
          {'<p style="margin:6px 0 0;font-size:0.88rem;color:#6B6460;line-height:1.5;">' + teaser + '</p>' if teaser else ''}
          <p style="margin:8px 0 0;"><a href="{url}" style="font-size:0.82rem;color:#C8963E;text-decoration:none;">Weiterlesen &#8594;</a></p>
        </div>"""

    # ── Specials block ────────────────────────────────────────────────────────
    specials_block = ""
    if specials and specials.strip():
        specials_paras = "".join(
            f'<p style="margin:0 0 10px;color:#2A2520;line-height:1.7;">{line.strip()}</p>'
            for line in specials.strip().split("\n") if line.strip()
        )
        specials_block = f"""
        <tr>
          <td style="background:#FFFFFF;padding:0 32px 28px;">
            <div style="border-top:1px solid #EDE9E3;padding-top:20px;">
              <p style="margin:0 0 14px;font-size:0.75rem;color:#C8963E;text-transform:uppercase;letter-spacing:2px;font-weight:600;">
                &#10024; Specials &amp; News
              </p>
              {specials_paras}
            </div>
          </td>
        </tr>"""

    articles_block = ""
    if articles_html:
        articles_block = f"""
        <tr>
          <td style="background:#FFFFFF;padding:0 32px 28px;">
            <div style="border-top:1px solid #EDE9E3;padding-top:20px;">
              <p style="margin:0 0 16px;font-size:0.75rem;color:#C8963E;text-transform:uppercase;letter-spacing:2px;font-weight:600;">
                &#128240; Neue Artikel
              </p>
              {articles_html}
            </div>
          </td>
        </tr>"""

    # ── Footer URL (derive display name from SITE_URL) ────────────────────────
    site_display = (SITE_URL
                    .replace("https://www.", "")
                    .replace("https://", "")
                    .replace("http://www.", "")
                    .rstrip("/"))

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Whisky &amp; Schottland | {month_label}</title>
</head>
<body style="margin:0;padding:0;background:#EDE9E3;font-family:'Inter',Arial,sans-serif;color:#2A2520;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#EDE9E3">
    <tr><td align="center" style="padding:32px 16px;">
      <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;">

        <!-- HEADER -->
        <tr>
          <td style="background:#2A2520;padding:28px 32px;border-radius:12px 12px 0 0;text-align:center;">
            <p style="margin:0;font-family:Georgia,serif;font-size:1.6rem;font-weight:700;color:#C8963E;letter-spacing:-0.5px;">
              Whisky &amp; Schottland
            </p>
            <p style="margin:4px 0 0;font-size:0.82rem;color:#9E9690;letter-spacing:1px;text-transform:uppercase;">
              {month_label}
            </p>
          </td>
        </tr>

        <!-- INTRO -->
        <tr>
          <td style="background:#FFFFFF;padding:28px 32px;">
            <p style="font-family:Georgia,serif;font-size:1.1rem;color:#2A2520;margin:0 0 12px;">
              Hallo ihr Lieben,
            </p>
            <p style="margin:0;color:#6B6460;line-height:1.7;">
              {intro_text}
            </p>
          </td>
        </tr>

        <!-- WHISKY DES MONATS -->
        <tr>
          <td style="background:#FFFFFF;padding:0 32px 28px;">
            <div style="border-top:2px solid #C8963E;padding-top:20px;">
              <p style="margin:0 0 4px;font-size:0.75rem;color:#C8963E;text-transform:uppercase;letter-spacing:2px;font-weight:600;">
                &#129347; Whisky des Monats
              </p>
              <h2 style="margin:0 0 4px;font-family:Georgia,serif;font-size:1.4rem;color:#2A2520;">{whisky_name}</h2>
              <p style="margin:0 0 8px;font-size:0.82rem;color:#9E9690;">{subheader}</p>
              {photos_html}
              {tasting_card}
              {'<p style="margin:16px 0 12px;color:#2A2520;line-height:1.7;">' + kommentar_html + '</p>' if kommentar_html else ''}
              <a href="{affiliate_link}" style="display:inline-block;background:#C8963E;color:#fff;padding:10px 22px;border-radius:6px;font-size:0.88rem;text-decoration:none;font-weight:600;margin-top:8px;">Auf Amazon ansehen &#8594;</a>
            </div>
          </td>
        </tr>

        {specials_block}
        {articles_block}

        <!-- FOOTER -->
        <tr>
          <td style="background:#2A2520;padding:20px 32px;border-radius:0 0 12px 12px;text-align:center;">
            <p style="margin:0 0 8px;color:#9E9690;font-size:0.78rem;">
              <a href="{SITE_URL}" style="color:#C8963E;text-decoration:none;">{site_display}</a>
              &nbsp;&middot;&nbsp;
              Steffen &amp; Ellas
            </p>
            <p style="margin:0;font-size:0.72rem;color:#6B6460;">
              Du erh&#228;ltst diesen Newsletter, weil du dich auf {site_display} angemeldet hast.<br>
              <a href="{{{{ unsubscribe }}}}" style="color:#6B6460;">Abmelden</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    return html


# ── whisky.de tasting notes scraper + OpenAI fallback ────────────────────────

def _fetch_whisky_de_tasting(whisky_name: str) -> dict:
    """Fetch tasting notes: tries whisky.de first, falls back to OpenAI if blocked."""

    def _strip_tags(s):
        return _re.sub(r'<[^>]+>', ' ', s).strip()

    def _extract(pattern, html, group=1, flags=_re.IGNORECASE | _re.DOTALL):
        m = _re.search(pattern, html, flags)
        return m.group(group).strip() if m else ""

    def _http_get(url, timeout=12):
        req = Request(url, headers={
            # Real browser UA to avoid bot blocking
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            "Accept-Encoding": "identity",
            "Cache-Control": "no-cache",
        })
        try:
            with urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace"), None
        except HTTPError as e:
            return "", f"HTTP {e.code}"
        except Exception as exc:
            return "", str(exc)

    # ── Attempt 1: whisky.de search ───────────────────────────────────────────
    # Try several known URL patterns for whisky.de search
    search_candidates = [
        f"https://www.whisky.de/suche/?suchbegriff={quote(whisky_name, safe='')}",
        f"https://www.whisky.de/online-shop/search.html?q={quote(whisky_name, safe='')}",
        f"https://www.whisky.de/shop/search.html?q={quote(whisky_name, safe='')}",
    ]

    search_html = ""
    search_err  = ""
    for url in search_candidates:
        search_html, search_err = _http_get(url)
        if search_html:
            break

    if search_html:
        # Find first product link
        product_path = (
            _re.search(r'href="(/(?:shop|online-shop)/(?:produkt|product)/[^"]+\.html)"', search_html)
            or _re.search(r'href="(/[^"]+/(?:whisky|whiskey)/[^"]+\.html)"', search_html)
        )
        if product_path:
            product_url  = "https://www.whisky.de" + product_path.group(1)
            detail_html, _ = _http_get(product_url)
            if detail_html:
                result = {"source": "whisky.de", "product_url": product_url}

                aroma = _extract(
                    r'(?:Nase|Aroma|Nose)\s*</[^>]+>\s*(?:<[^>]+>)?\s*([^<]{15,})', detail_html)
                if not aroma:
                    aroma = _extract(r'class="[^"]*(?:aroma|nose)[^"]*"[^>]*>([^<]{15,})', detail_html)
                result["aroma"] = _strip_tags(aroma)

                geschmack = _extract(
                    r'(?:Gaumen|Geschmack|Palate)\s*</[^>]+>\s*(?:<[^>]+>)?\s*([^<]{15,})', detail_html)
                if not geschmack:
                    geschmack = _extract(r'class="[^"]*(?:geschmack|palate)[^"]*"[^>]*>([^<]{15,})', detail_html)
                result["geschmack"] = _strip_tags(geschmack)

                abgang = _extract(
                    r'(?:Abgang|Finish)\s*</[^>]+>\s*(?:<[^>]+>)?\s*([^<]{15,})', detail_html)
                result["abgang"] = _strip_tags(abgang)

                try:
                    b = _extract(r'(\d{2,3})\s*(?:Punkte|Pkt|/100)', detail_html)
                    result["bewertung"] = int(b) if b else None
                except Exception:
                    result["bewertung"] = None

                try:
                    a = _extract(r'(\d{1,2})\s*(?:Jahre|Years?|YO|yo)\b', detail_html)
                    result["alter"] = int(a) if a else None
                except Exception:
                    result["alter"] = None

                try:
                    abv = _extract(r'(\d{2,3}[,.]?\d*)\s*%\s*(?:vol|Vol|ABV)', detail_html)
                    result["abv"] = float(abv.replace(",", ".")) if abv else None
                except Exception:
                    result["abv"] = None

                try:
                    preis = _extract(r'(\d+[,.]?\d+)\s*€', detail_html)
                    result["preis_eur"] = float(preis.replace(",", ".")) if preis else None
                except Exception:
                    result["preis_eur"] = None

                # Return whisky.de result if we got at least one tasting note
                if result.get("aroma") or result.get("geschmack") or result.get("abgang"):
                    return result

    # ── Attempt 2: OpenAI fallback ────────────────────────────────────────────
    if OPENAI_API_KEY:
        prompt = (
            f"Erstelle realistische Tasting Notes für den Whisky '{whisky_name}'. "
            "Antworte NUR als JSON-Objekt mit diesen Feldern (alle auf Deutsch, Strings):\n"
            '{"aroma": "...", "geschmack": "...", "abgang": "...", '
            '"bewertung": <Zahl 0-100 oder null>, "alter": <Zahl in Jahren oder null>, '
            '"abv": <Zahl in % oder null>, "preis_eur": <Zahl in EUR oder null>}\n'
            "Bewertung, Alter, ABV und Preis nur wenn du dir sicher bist, sonst null."
        )
        ai_text = _call_openai(
            [{"role": "system", "content": "Du bist ein Whisky-Experte. Antworte ausschließlich mit gültigem JSON."},
             {"role": "user",   "content": prompt}],
            max_tokens=300,
        )
        if ai_text:
            try:
                # Strip markdown fences if present
                clean = _re.sub(r'^```(?:json)?\s*|\s*```$', '', ai_text.strip())
                parsed = json.loads(clean)
                parsed["source"] = "KI (OpenAI)"
                return parsed
            except Exception:
                pass

    # ── Both failed ───────────────────────────────────────────────────────────
    detail = f"whisky.de: {search_err or 'kein Produkt gefunden'}"
    if not OPENAI_API_KEY:
        detail += " | OpenAI-Fallback nicht verfügbar (OPENAI_API_KEY fehlt)"
    return {"error": f"Keine Daten gefunden – {detail}", "source": "whisky.de"}


# ── Handler ───────────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers(self.headers.get("Origin", "")).items():
            self.send_header(k, v)
        self.end_headers()

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}, None
            if length > 10_000_000:  # 10 MB for multiple photo uploads
                return None, "Request body too large (max 10 MB)"
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8")), None
        except Exception as e:
            return None, str(e)

    def _json(self, code, data, extra_headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (_cors_headers(self.headers.get("Origin", "")) | (extra_headers or {})).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _check_auth(self):
        return _verify_token(self.headers.get("x-admin-token", ""))

    # ── GET ──────────────────────────────────────────────────────────────────
    def do_GET(self):
        if not self._check_auth():
            return self._json(401, {"error": "Unauthorized"})
        data, _ = _load_wotm_data()
        if data is None:
            return self._json(500, {"error": "Fehler beim Laden der WotM-Daten"})
        return self._json(200, data)

    # ── POST ─────────────────────────────────────────────────────────────────
    def do_POST(self):
        if not self._check_auth():
            return self._json(401, {"error": "Unauthorized"})

        body, err = self._read_body()
        if err:
            return self._json(400, {"error": err})

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        action = params.get("action", ["save"])[0]

        # ── Fetch tasting notes from whisky.de ───────────────────────────────
        if action == "fetch_tasting_notes":
            whisky_name = (body.get("whisky_name") or "").strip()
            if not whisky_name:
                return self._json(400, {"error": "whisky_name erforderlich"})
            result = _fetch_whisky_de_tasting(whisky_name)
            return self._json(200, result)

        # ── Save WotM entry ──────────────────────────────────────────────────
        if action == "save":
            month_key = (body.get("month_key") or "").strip()
            if not month_key or len(month_key) != 7:
                return self._json(400, {"error": "month_key muss im Format YYYY-MM sein"})

            whisky_name = (body.get("whisky_name") or "").strip()
            if not whisky_name:
                return self._json(400, {"error": "whisky_name ist erforderlich"})

            # Auto-generate affiliate link if not provided
            affiliate_link = (body.get("affiliate_link") or "").strip()
            if not affiliate_link:
                affiliate_link = _make_affiliate_link(whisky_name)

            # Save article teasers (list of {title, url, teaser})
            raw_articles = body.get("article_teasers") or []
            article_teasers_clean = [
                {"title": (a.get("title") or "").strip(),
                 "url":   (a.get("url")   or "").strip(),
                 "teaser":(a.get("teaser") or "").strip()}
                for a in raw_articles if (a.get("title") or "").strip()
            ]

            def _safe_float(val):
                try:
                    return float(val) if val not in (None, "") else None
                except Exception:
                    return None

            def _safe_int(val):
                try:
                    return int(val) if val not in (None, "") else None
                except Exception:
                    return None

            entry = {
                "whisky_name":    whisky_name,
                "destillerie":    (body.get("destillerie") or "").strip(),
                "destillerie_url":(body.get("destillerie_url") or "").strip(),
                "region":         (body.get("region") or "").strip(),
                "intro_text":     (body.get("intro_text") or "").strip(),
                "kommentar":      (body.get("kommentar") or "").strip(),
                "specials":       (body.get("specials") or "").strip(),
                "affiliate_link": affiliate_link,
                # Tasting notes (optional)
                "aroma":          (body.get("aroma") or "").strip(),
                "geschmack":      (body.get("geschmack") or "").strip(),
                "abgang":         (body.get("abgang") or "").strip(),
                "bewertung":      _safe_int(body.get("bewertung")),
                "alter":          _safe_int(body.get("alter")),
                "abv":            _safe_float(body.get("abv")),
                "preis_eur":      _safe_float(body.get("preis_eur")),
                "article_teasers": article_teasers_clean,
                "photo_urls":     [],
                "erstellt_am":    time.strftime("%Y-%m-%d"),
                "newsletter_gesendet": False,
                "newsletter_html_final": "",
            }

            # Multiple photo uploads
            photo_b64_list = body.get("photo_b64_list") or []
            photo_ext_list = body.get("photo_ext_list") or []
            new_photo_urls = []

            for idx, photo_b64 in enumerate(photo_b64_list[:4]):
                if not photo_b64:
                    continue
                try:
                    if "," in photo_b64:
                        photo_b64 = photo_b64.split(",", 1)[1]
                    img_bytes = base64.b64decode(photo_b64)
                    ext = (photo_ext_list[idx] if idx < len(photo_ext_list) else "jpg").strip().lstrip(".")
                    # Speicherort im Repo: site-v2/images/wotm/ (Vercel output directory)
                    # URL im Browser: /images/wotm/... (site-v2 wird als root ausgeliefert)
                    img_repo_path = f"site-v2/images/wotm/{month_key}_{idx+1}.{ext}"
                    img_url_path  = f"/images/wotm/{month_key}_{idx+1}.{ext}"
                    existing = _github_get(f"contents/{img_repo_path}")
                    img_sha  = existing.get("sha") if "error" not in existing else None
                    result   = _github_put(img_repo_path, img_bytes, img_sha,
                                           f"WotM Foto {month_key} #{idx+1}")
                    if "error" not in result:
                        new_photo_urls.append(img_url_path)
                except Exception:
                    pass

            # Load existing data for merging
            data, sha = _load_wotm_data()
            if data is None:
                data = {"entries": {}}

            existing_entry = (data.get("entries") or {}).get(month_key, {})

            # Keep existing photos if no new ones uploaded
            if new_photo_urls:
                entry["photo_urls"] = new_photo_urls
            else:
                entry["photo_urls"] = existing_entry.get("photo_urls") or []
                if not entry["photo_urls"] and existing_entry.get("photo_url"):
                    entry["photo_urls"] = [existing_entry["photo_url"]]

            # Keep existing article_teasers if no new ones provided
            if not article_teasers_clean:
                entry["article_teasers"] = existing_entry.get("article_teasers", [])

            # Preserve newsletter sent status and saved HTML
            if existing_entry.get("newsletter_gesendet"):
                entry["newsletter_gesendet"] = existing_entry["newsletter_gesendet"]
            saved_html = (body.get("newsletter_html_final") or "").strip()

            # Invalidate stale newsletter HTML if photos or articles changed:
            # the saved HTML may reference an outdated image set / teaser list.
            old_photos   = existing_entry.get("photo_urls") or []
            new_photos   = entry["photo_urls"] or []
            old_articles = existing_entry.get("article_teasers") or []
            new_articles = entry["article_teasers"] or []
            content_changed = (
                len(old_photos) != len(new_photos)
                or set(old_photos) != set(new_photos)
                or len(old_articles) != len(new_articles)
            )
            if saved_html:
                entry["newsletter_html_final"] = saved_html
            elif content_changed:
                # Frontend hat keine HTML mitgeschickt UND Inhalte haben sich geändert
                # → alte HTML verwerfen, damit der Redakteur neu generieren muss.
                entry["newsletter_html_final"] = ""
            else:
                entry["newsletter_html_final"] = existing_entry.get("newsletter_html_final", "")

            data.setdefault("entries", {})[month_key] = entry
            save_err = _save_wotm_data(data, sha, f"WotM {month_key}: {whisky_name}")
            if save_err:
                return self._json(500, {"error": save_err})

            return self._json(200, {"ok": True, "entry": entry})

        # ── Save final newsletter HTML ────────────────────────────────────────
        if action == "save_newsletter":
            month_key       = (body.get("month_key") or "").strip()
            newsletter_html = (body.get("newsletter_html") or "").strip()

            if not month_key:
                return self._json(400, {"error": "month_key fehlt"})
            if not newsletter_html:
                return self._json(400, {"error": "newsletter_html ist leer – bitte zuerst generieren"})

            # Retry once on SHA mismatch (409 conflict)
            for attempt in range(2):
                data, sha = _load_wotm_data()
                if data is None:
                    return self._json(502, {"error": "GitHub nicht erreichbar – bitte erneut versuchen"})
                if month_key not in data.get("entries", {}):
                    return self._json(404, {"error": "WotM-Eintrag nicht gefunden – bitte zuerst Whisky-Daten speichern"})

                data["entries"][month_key]["newsletter_html_final"] = newsletter_html
                save_err = _save_wotm_data(data, sha, f"Newsletter-HTML gespeichert {month_key}")
                if not save_err:
                    break
                if attempt == 0 and ("409" in str(save_err) or "sha" in str(save_err).lower()):
                    continue  # retry with fresh SHA
                return self._json(500, {"error": save_err})

            return self._json(200, {"ok": True})

        # ── Preview Newsletter HTML ──────────────────────────────────────────
        if action == "preview_html":
            month_key    = (body.get("month_key") or "").strip()
            month_label  = (body.get("month_label") or month_key).strip()
            # skip_polish=True: use texts exactly as provided (user edited them)
            skip_polish  = bool(body.get("skip_polish", False))

            entry = {
                "whisky_name":    (body.get("whisky_name") or "").strip(),
                "destillerie":    (body.get("destillerie") or "").strip(),
                "destillerie_url":(body.get("destillerie_url") or "").strip(),
                "region":         (body.get("region") or "").strip(),
                "kommentar":      (body.get("kommentar") or "").strip(),
                "specials":       (body.get("specials") or "").strip(),
                "intro_text":     (body.get("intro_text") or "").strip(),
                "affiliate_link": (body.get("affiliate_link") or "").strip(),
                "photo_urls":     body.get("photo_urls") or [],
                # Tasting notes
                "aroma":          (body.get("aroma") or "").strip(),
                "geschmack":      (body.get("geschmack") or "").strip(),
                "abgang":         (body.get("abgang") or "").strip(),
                "bewertung":      body.get("bewertung"),
                "alter":          body.get("alter"),
                "abv":            body.get("abv"),
                "preis_eur":      body.get("preis_eur"),
            }
            if not entry["affiliate_link"] and entry["whisky_name"]:
                entry["affiliate_link"] = _make_affiliate_link(entry["whisky_name"])

            # Article teasers: manuelle Eingaben + Auto-Fill leerer Slots aus dem Vormonat.
            # (Newsletter geht Anfang des Monats raus → ergänze um Artikel aus dem Vormonat,
            #  wenn der Redakteur weniger als 3 Artikel manuell hinterlegt hat.)
            article_teasers = [
                a for a in (body.get("article_teasers") or [])
                if (a.get("title") or "").strip()
            ]
            if len(article_teasers) < 3 and month_key:
                try:
                    nl_year, nl_month = map(int, month_key.split("-"))
                    prev_month = nl_month - 1 if nl_month > 1 else 12
                    prev_year  = nl_year if nl_month > 1 else nl_year - 1
                    prev_key   = f"{prev_year}-{prev_month:02d}"
                except Exception:
                    prev_key = month_key
                fetched = _fetch_month_articles(prev_key) or []
                # Doppelte URLs vermeiden (Redakteur hat Artikel bereits manuell eingetragen)
                existing_urls = {(a.get("url") or "").strip().rstrip("/") for a in article_teasers}
                for a in fetched:
                    if len(article_teasers) >= 3:
                        break
                    url_norm = (a.get("url") or "").strip().rstrip("/")
                    if url_norm and url_norm not in existing_urls:
                        article_teasers.append(a)
                        existing_urls.add(url_norm)

            # Polish texts via AI – skipped when skip_polish=True
            ai_active = bool(OPENAI_API_KEY) and not skip_polish
            polished_kommentar = entry["kommentar"]
            polished_specials  = entry["specials"]
            polished_intro     = entry["intro_text"]

            if ai_active:
                if entry["kommentar"]:
                    result = _polish_kommentar(entry["kommentar"], entry["whisky_name"])
                    if result:
                        polished_kommentar = result
                        entry["kommentar"] = result

                if entry["specials"]:
                    result = _polish_specials(entry["specials"])
                    if result:
                        polished_specials = result
                        entry["specials"] = result

            # Generate intro if still empty
            if not entry["intro_text"]:
                article_titles = [a.get("title", "") for a in article_teasers]
                generated = _generate_intro(
                    month_label, entry["whisky_name"], article_titles)
                polished_intro = generated
                entry["intro_text"] = generated

            html = _build_newsletter_html(entry, month_label, article_teasers)
            return self._json(200, {
                "html": html,
                "ai_active": ai_active,
                "polished": {
                    "kommentar":  polished_kommentar,
                    "specials":   polished_specials,
                    "intro_text": polished_intro,
                },
                "article_teasers": article_teasers,
            })

        # ── Send Newsletter ──────────────────────────────────────────────────
        if action == "send_newsletter":
            month_key   = (body.get("month_key") or "").strip()
            month_label = (body.get("month_label") or month_key).strip()

            data, sha = _load_wotm_data()
            if not data or month_key not in data.get("entries", {}):
                return self._json(404, {"error": "WotM-Eintrag nicht gefunden"})

            entry = data["entries"][month_key]

            # Use saved final HTML if available, otherwise generate fresh
            # Article teasers come from the saved entry (set at save time)
            html = entry.get("newsletter_html_final") or ""
            if not html:
                article_teasers = entry.get("article_teasers") or []
                html = _build_newsletter_html(entry, month_label, article_teasers)

            subject = f"Whisky & Schottland | {month_label} - Unser Whisky des Monats"
            campaign, err = _brevo_create_campaign(
                subject, html, "Steffen & Ellas", "newsletter@whiskyreise.de")
            if err:
                return self._json(500, {"error": f"Kampagne erstellen fehlgeschlagen: {err}"})

            campaign_id = campaign.get("id")
            ok, err2 = _brevo_send_now(campaign_id)
            if not ok:
                return self._json(500, {"error": f"Senden fehlgeschlagen: {err2}", "campaign_id": campaign_id})

            entry["newsletter_gesendet"] = time.strftime("%Y-%m-%d %H:%M")
            _save_wotm_data(data, sha, f"Newsletter gesendet {month_key}")

            return self._json(200, {"ok": True, "campaign_id": campaign_id})

        return self._json(400, {"error": f"Unbekannte action: {action}"})

    def log_message(self, fmt, *args):
        pass
