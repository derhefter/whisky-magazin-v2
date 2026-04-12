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
SITE_URL        = os.environ.get("SITE_URL", "https://www.whiskyreise.de").strip()
AMAZON_TAG      = "whiskyreise74-21"

TOKEN_TTL = 86400
WOTM_FILE = "data/whisky-of-the-month.json"


# ── Auth ──────────────────────────────────────────────────────────────────────

def _verify_token(token: str) -> bool:
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
    key = (ADMIN_PASSWORD or "fallback").encode()
    sig = hmac.new(key, ts_str.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(token, f"{ts_str}.{sig}")


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
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

def _build_newsletter_html(entry, month_label, article_teasers):
    whisky_name    = entry.get("whisky_name", "")
    destillerie    = entry.get("destillerie", "")
    region         = entry.get("region", "")
    kommentar      = entry.get("kommentar", "")
    specials       = entry.get("specials", "")
    affiliate_link = entry.get("affiliate_link", "") or _make_affiliate_link(whisky_name)

    # Photos – support both old single photo_url and new photo_urls array
    photo_urls = entry.get("photo_urls") or []
    if not photo_urls and entry.get("photo_url"):
        photo_urls = [entry["photo_url"]]

    # Build photo gallery HTML
    photos_html = ""
    if photo_urls:
        if len(photo_urls) == 1:
            url = photo_urls[0]
            full_url = url if url.startswith("http") else f"{SITE_URL}{url}"
            photos_html = f'<img src="{full_url}" alt="{whisky_name}" style="width:100%;max-width:560px;border-radius:8px;margin:12px 0 16px;">'
        else:
            # Grid layout for multiple photos
            thumb_w = 260
            cells = ""
            for url in photo_urls[:4]:
                full_url = url if url.startswith("http") else f"{SITE_URL}{url}"
                cells += f'<td style="padding:4px;"><img src="{full_url}" alt="{whisky_name}" style="width:{thumb_w}px;max-width:100%;border-radius:6px;display:block;"></td>'
            photos_html = f'<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:12px 0 16px;"><tr>{cells}</tr></table>'

    # Article teasers
    articles_html = ""
    for a in article_teasers[:3]:
        title  = a.get("title", "")
        teaser = a.get("teaser", "")
        # Support both 'url' (direct) and 'slug' (legacy)
        url    = a.get("url", "")
        if not url:
            slug = a.get("slug", "")
            url  = f"{SITE_URL}/artikel/{slug}.html" if slug else SITE_URL
        if not title:
            continue
        articles_html += f"""
        <div style="margin-bottom:16px;padding:16px;background:#FAF8F4;border-radius:8px;">
          <a href="{url}" style="font-family:Georgia,serif;font-size:1.05rem;font-weight:600;color:#2A2520;text-decoration:none;">{title}</a>
          {'<p style="margin:6px 0 0;font-size:0.88rem;color:#6B6460;">' + teaser + '</p>' if teaser else ''}
          <a href="{url}" style="font-size:0.82rem;color:#C8963E;">Weiterlesen &#8594;</a>
        </div>"""

    # Specials block
    specials_block = ""
    if specials and specials.strip():
        # Convert plain-text specials to simple HTML paragraphs
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
              der neue Monat ist da &#8211; und wir haben wieder einiges f&#252;r euch: einen Whisky,
              der uns gerade nicht losla&#776;sst, ein paar neue Artikel und den u&#776;blichen
              Schottland-Moment des Monats. Kurz, knapp, hoffentlich lohnenswert.
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
              <h2 style="margin:0 0 4px;font-family:Georgia,serif;font-size:1.3rem;color:#2A2520;">{whisky_name}</h2>
              <p style="margin:0 0 12px;font-size:0.82rem;color:#9E9690;">{destillerie}{' &middot; ' + region if region else ''}</p>
              {photos_html}
              <p style="margin:12px 0;color:#2A2520;line-height:1.7;">{kommentar.replace(chr(10), '<br>')}</p>
              <a href="{affiliate_link}" style="display:inline-block;background:#C8963E;color:#fff;padding:10px 20px;border-radius:6px;font-size:0.88rem;text-decoration:none;font-weight:600;">Auf Amazon ansehen &#8594;</a>
            </div>
          </td>
        </tr>

        {specials_block}
        {articles_block}

        <!-- FOOTER -->
        <tr>
          <td style="background:#2A2520;padding:20px 32px;border-radius:0 0 12px 12px;text-align:center;">
            <p style="margin:0 0 8px;color:#9E9690;font-size:0.78rem;">
              <a href="{SITE_URL}" style="color:#C8963E;text-decoration:none;">whiskyreise.de</a>
              &nbsp;&middot;&nbsp;
              Steffen &amp; Ellas
            </p>
            <p style="margin:0;font-size:0.72rem;color:#6B6460;">
              Du erh&#228;ltst diesen Newsletter, weil du dich auf whiskyreise.de angemeldet hast.<br>
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


# ── Handler ───────────────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers().items():
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
        for k, v in (_cors_headers() | (extra_headers or {})).items():
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

            entry = {
                "whisky_name":    whisky_name,
                "destillerie":    (body.get("destillerie") or "").strip(),
                "region":         (body.get("region") or "").strip(),
                "kommentar":      (body.get("kommentar") or "").strip(),
                "specials":       (body.get("specials") or "").strip(),
                "affiliate_link": affiliate_link,
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
                    img_path = f"images/wotm/{month_key}_{idx+1}.{ext}"
                    existing = _github_get(f"contents/{img_path}")
                    img_sha  = existing.get("sha") if "error" not in existing else None
                    result   = _github_put(img_path, img_bytes, img_sha,
                                           f"WotM Foto {month_key} #{idx+1}")
                    if "error" not in result:
                        new_photo_urls.append(f"/{img_path}")
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
            entry["newsletter_html_final"] = saved_html or existing_entry.get("newsletter_html_final", "")

            data.setdefault("entries", {})[month_key] = entry
            save_err = _save_wotm_data(data, sha, f"WotM {month_key}: {whisky_name}")
            if save_err:
                return self._json(500, {"error": save_err})

            return self._json(200, {"ok": True, "entry": entry})

        # ── Save final newsletter HTML ────────────────────────────────────────
        if action == "save_newsletter":
            month_key      = (body.get("month_key") or "").strip()
            newsletter_html = (body.get("newsletter_html") or "").strip()

            data, sha = _load_wotm_data()
            if not data or month_key not in data.get("entries", {}):
                return self._json(404, {"error": "WotM-Eintrag nicht gefunden"})

            data["entries"][month_key]["newsletter_html_final"] = newsletter_html
            save_err = _save_wotm_data(data, sha, f"Newsletter-HTML gespeichert {month_key}")
            if save_err:
                return self._json(500, {"error": save_err})

            return self._json(200, {"ok": True})

        # ── Preview Newsletter HTML ──────────────────────────────────────────
        if action == "preview_html":
            month_key     = (body.get("month_key") or "").strip()
            month_label   = (body.get("month_label") or month_key).strip()
            article_teasers = body.get("article_teasers") or []

            entry = {
                "whisky_name":    (body.get("whisky_name") or "").strip(),
                "destillerie":    (body.get("destillerie") or "").strip(),
                "region":         (body.get("region") or "").strip(),
                "kommentar":      (body.get("kommentar") or "").strip(),
                "specials":       (body.get("specials") or "").strip(),
                "affiliate_link": (body.get("affiliate_link") or "").strip(),
                "photo_urls":     body.get("photo_urls") or [],
            }
            # Auto-generate affiliate link if missing
            if not entry["affiliate_link"] and entry["whisky_name"]:
                entry["affiliate_link"] = _make_affiliate_link(entry["whisky_name"])

            html = _build_newsletter_html(entry, month_label, article_teasers)
            return self._json(200, {"html": html})

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
