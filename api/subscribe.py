"""Vercel Serverless Function: Newsletter Double Opt-In via Brevo Transactional API."""
import json
import os
import re
import time
import hashlib
import hmac
from collections import defaultdict
from http.server import BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urlparse, parse_qs


BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
BREVO_LIST_ID = int(os.environ.get("BREVO_LIST_ID", "3"))
REDIRECT_URL = os.environ.get("BREVO_REDIRECT_URL", "https://www.whisky-reise.com/danke.html")
BASE_URL = os.environ.get("BASE_URL", "https://www.whisky-reise.com")

# Eigenes Secret fuer DOI-/Unsubscribe-Tokens. Frueher wurde sha256(BREVO_API_KEY)
# benutzt - das brach bei jeder Brevo-Key-Rotation alle bereits versandten Links.
# Fuer Migration werden alte Tokens uebergangsweise weiter akzeptiert (siehe _verify_token).
NEWSLETTER_TOKEN_SECRET = os.environ.get("NEWSLETTER_TOKEN_SECRET", "").strip()

# Cloudflare Turnstile (Captcha): Secret im Vercel-Env, Verify gegen siteverify-Endpoint.
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "").strip()


def _verify_turnstile(token: str, remote_ip: str = "") -> bool:
    """Verify a Cloudflare Turnstile token. Returns True on success.
    Wenn TURNSTILE_SECRET_KEY nicht gesetzt ist, wird die Pruefung uebersprungen
    (Fail-open fuer den Migrations-/Setup-Zeitraum)."""
    if not TURNSTILE_SECRET_KEY:
        return True
    if not token:
        return False
    try:
        payload = json.dumps({
            "secret": TURNSTILE_SECRET_KEY,
            "response": token,
            "remoteip": remote_ip or "",
        }).encode("utf-8")
        req = Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return bool(data.get("success"))
    except Exception:
        return False

ALLOWED_ORIGINS = [
    "https://www.whisky-reise.com",
    "https://www.whisky-magazin.de",
    "https://whisky-magazin.de",
    "http://localhost:3000",
    "http://localhost:8000",
]

_rate_store = defaultdict(list)
RATE_LIMIT_PER_MINUTE = 5
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

FEEDBACK_RECIPIENT = "feedback@whisky-reise.com"
_feedback_rate = defaultdict(list)
FEEDBACK_RATE_LIMIT = 3  # max pro Stunde pro IP

# Trusted-Form Bypass: Forms ohne sichtbares Captcha (Beta-Fragebogen,
# Glossar-Feedback) duerfen den Turnstile-Check ueberspringen, dafuer aber
# striktes IP-Rate-Limit + Origin-Check (do_POST validiert Origin bereits
# gegen ALLOWED_ORIGINS).
TRUSTED_FORM_SOURCES = {"fragebogen", "glossar"}
_trusted_form_rate = defaultdict(list)
TRUSTED_FORM_RATE_LIMIT = 5  # max pro Stunde pro IP


def _is_trusted_form_rate_limited(ip: str) -> bool:
    now = time.time()
    cutoff = now - 3600
    _trusted_form_rate[ip] = [t for t in _trusted_form_rate[ip] if t > cutoff]
    if len(_trusted_form_rate[ip]) >= TRUSTED_FORM_RATE_LIMIT:
        return True
    _trusted_form_rate[ip].append(now)
    return False

# DOI confirmation email HTML (uses HTML entities for umlauts to avoid encoding issues)
DOI_HTML = (
    '<!DOCTYPE html><html><head><meta charset="utf-8"></head>'
    '<body style="font-family:Inter,Helvetica,Arial,sans-serif;background:#FAFAF7;margin:0;padding:40px 20px;">'
    '<div style="max-width:520px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">'
    '<div style="background:#2C2C2C;padding:32px 24px;text-align:center;">'
    '<span style="font-family:Georgia,serif;font-size:24px;color:#fff;font-weight:700;">whisky</span>'
    '<span style="color:#C8963E;font-size:24px;">.</span>'
    '<span style="font-size:14px;letter-spacing:3px;text-transform:uppercase;color:rgba(255,255,255,0.7);margin-left:4px;">MAGAZIN</span>'
    '</div>'
    '<div style="padding:40px 32px;text-align:center;">'
    '<h1 style="font-family:Georgia,serif;font-size:22px;color:#2C2C2C;margin:0 0 16px;">Fast geschafft!</h1>'
    '<p style="font-size:15px;color:#5C5C5C;line-height:1.7;margin:0 0 28px;">'
    'Du hast dich f&uuml;r unseren Newsletter angemeldet. '
    'Best&auml;tige jetzt deine E-Mail-Adresse, um dabei zu sein.</p>'
    '<a href="CONFIRM_URL_PLACEHOLDER" style="display:inline-block;background:#C8963E;color:#fff;'
    'text-decoration:none;padding:14px 36px;border-radius:6px;font-size:15px;font-weight:600;">'
    'Anmeldung best&auml;tigen</a>'
    '<p style="font-size:13px;color:#8A8A8A;margin:28px 0 0;line-height:1.6;">'
    'Einmal im Monat die besten Whisky-Geschichten und Reise-Tipps.<br>'
    'Kein Spam. Jederzeit abbestellbar.</p>'
    '</div>'
    '<div style="border-top:1px solid #E8E4DF;padding:20px 32px;text-align:center;">'
    '<p style="font-size:12px;color:#8A8A8A;margin:0;">&copy; 2007&ndash;2026 Whisky Magazin</p>'
    '</div></div></body></html>'
)


def _legacy_secret():
    """Altes Secret-Schema (sha256 vom Brevo-Key). Nur fuer Verify alter Links."""
    if not BREVO_API_KEY:
        return None
    return hashlib.sha256(BREVO_API_KEY.encode()).hexdigest()[:32]


def _current_secret():
    """Aktuelles Token-Secret. Bevorzugt NEWSLETTER_TOKEN_SECRET, faellt sonst auf
    das Legacy-Schema zurueck (Abwaertskompatibilitaet, falls Env-Var fehlt)."""
    if NEWSLETTER_TOKEN_SECRET:
        return NEWSLETTER_TOKEN_SECRET
    return _legacy_secret()


def _make_token(email):
    secret = _current_secret()
    if not secret:
        raise RuntimeError("Weder NEWSLETTER_TOKEN_SECRET noch BREVO_API_KEY gesetzt")
    return hmac.new(secret.encode(), email.lower().strip().encode(), hashlib.sha256).hexdigest()


def _verify_token(email, token):
    """True, wenn Token gegen aktuelles Secret ODER Legacy-Secret gueltig ist.
    Migrationspfad: nach 30 Tagen kann der Legacy-Pfad entfernt werden."""
    if not token:
        return False
    candidates = []
    cur = _current_secret()
    if cur:
        candidates.append(cur)
    legacy = _legacy_secret()
    if legacy and legacy not in candidates:
        candidates.append(legacy)
    msg = email.lower().strip().encode()
    for secret in candidates:
        expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
        if hmac.compare_digest(token, expected):
            return True
    return False


def _send_welcome_email(email):
    """Send a welcome newsletter to newly confirmed subscribers."""
    B = BASE_URL
    unsub_token = _make_token(email)
    unsub_url = B + "/api/subscribe?action=unsubscribe&email=" + email + "&token=" + unsub_token
    welcome_html = (
        '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<title>Willkommen beim Whisky Magazin</title></head>'
        '<body style="margin:0;padding:0;background:#FAFAF7;font-family:Inter,Helvetica,Arial,sans-serif;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#FAFAF7;">'
        '<tr><td align="center" style="padding:32px 16px;">'
        '<table width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.06);">'
        # HEADER
        '<tr><td style="background:#2C2C2C;padding:32px 32px 28px;text-align:center;">'
        '<span style="font-family:Georgia,serif;font-size:26px;color:#fff;font-weight:700;">whisky</span>'
        '<span style="color:#C8963E;font-size:26px;">.</span>'
        '<span style="font-size:13px;letter-spacing:3px;text-transform:uppercase;color:#999999;margin-left:4px;">MAGAZIN</span>'
        '<p style="font-size:12px;color:#777777;margin:12px 0 0;letter-spacing:1px;text-transform:uppercase;">Schottland-Post &middot; Willkommensausgabe</p>'
        '</td></tr>'
        # GREETING
        '<tr><td style="padding:36px 32px 24px;">'
        '<h1 style="font-family:Georgia,serif;font-size:24px;color:#2C2C2C;margin:0 0 12px;">Willkommen bei der Schottland-Post!</h1>'
        '<p style="font-size:15px;color:#5C5C5C;line-height:1.7;margin:0;">'
        'Sch&ouml;n, dass du dabei bist! Ab sofort erh&auml;ltst du einmal im Monat die besten '
        'Whisky-Geschichten und Reise-Tipps direkt in dein Postfach. '
        'Hier ist deine erste Ausgabe &ndash; viel Spa&szlig; beim Lesen!</p>'
        '</td></tr>'
        '<tr><td style="padding:0 32px;"><div style="border-top:2px solid #C8963E;width:48px;"></div></td></tr>'
        # ARTICLES
        '<tr><td style="padding:28px 32px 8px;">'
        '<h2 style="font-family:Georgia,serif;font-size:18px;color:#2C2C2C;margin:0 0 4px;">Unsere neuesten Geschichten</h2>'
        '<p style="font-size:13px;color:#8A8A8A;margin:0;">Frisch aus der Redaktion</p>'
        '</td></tr>'
        '<tr><td style="padding:0 32px;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0">'
        # Article 1
        '<tr><td style="padding:20px 0;">'
        '<a href="' + B + '/artikel/whisky-geschenke-15-ideen-fuer-liebhaber.html" style="text-decoration:none;color:#2C2C2C;">'
        '<strong style="font-family:Georgia,serif;font-size:16px;">Whisky-Geschenke: 15 Ideen f&uuml;r Liebhaber</strong></a>'
        '<p style="font-size:13px;color:#5C5C5C;line-height:1.6;margin:6px 0 0;">Suchst du das perfekte Geschenk f&uuml;r Whisky-Fans? Von Gl&auml;sern bis zum Tasting-Set.</p>'
        '</td></tr>'
        # Article 2
        '<tr><td style="padding:20px 0;border-top:1px solid #E8E4DF;">'
        '<a href="' + B + '/artikel/die-10-besten-single-malts-unter-50-euro.html" style="text-decoration:none;color:#2C2C2C;">'
        '<strong style="font-family:Georgia,serif;font-size:16px;">Die 10 besten Single Malts unter 50 Euro</strong></a>'
        '<p style="font-size:13px;color:#5C5C5C;line-height:1.6;margin:6px 0 0;">Herausragender Whisky muss nicht teuer sein. Unsere Top 10 f&uuml;r jedes Budget.</p>'
        '</td></tr>'
        # Article 3
        '<tr><td style="padding:20px 0;border-top:1px solid #E8E4DF;">'
        '<a href="' + B + '/artikel/schottische-k%C3%BCche-mehr-als-haggis.html" style="text-decoration:none;color:#2C2C2C;">'
        '<strong style="font-family:Georgia,serif;font-size:16px;">Schottische K&uuml;che: Mehr als Haggis</strong></a>'
        '<p style="font-size:13px;color:#5C5C5C;line-height:1.6;margin:6px 0 0;">Von frischem Seafood bis zum perfekten Shortbread &ndash; schottische Kulinarik &uuml;berrascht.</p>'
        '</td></tr>'
        # Article 4
        '<tr><td style="padding:20px 0;border-top:1px solid #E8E4DF;">'
        '<a href="' + B + '/artikel/glenfiddich-vs-glenlivet-der-grosse-vergleich.html" style="text-decoration:none;color:#2C2C2C;">'
        '<strong style="font-family:Georgia,serif;font-size:16px;">Glenfiddich vs. Glenlivet: Der gro&szlig;e Vergleich</strong></a>'
        '<p style="font-size:13px;color:#5C5C5C;line-height:1.6;margin:6px 0 0;">Zwei Speyside-Giganten im direkten Duell. Wer gewinnt?</p>'
        '</td></tr>'
        '</table></td></tr>'
        '<tr><td style="padding:8px 32px 28px;text-align:center;">'
        '<a href="' + B + '" style="display:inline-block;background:#C8963E;color:#fff;text-decoration:none;padding:12px 28px;border-radius:6px;font-size:14px;font-weight:600;">Alle Artikel lesen &rarr;</a>'
        '</td></tr>'
        # WHISKY TIPP
        '<tr><td style="padding:0 32px;">'
        '<div style="background:#FAF6F0;border-radius:8px;padding:28px;border-left:4px solid #C8963E;">'
        '<p style="font-size:11px;color:#C8963E;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin:0 0 12px;">&#127867; Whisky-Tipp des Monats</p>'
        '<h3 style="font-family:Georgia,serif;font-size:20px;color:#2C2C2C;margin:0 0 8px;">Talisker 10 Jahre</h3>'
        '<p style="font-size:12px;color:#8A8A8A;margin:0 0 12px;">Isle of Skye &middot; ca. 28&ndash;35 &euro;</p>'
        '<p style="font-size:14px;color:#5C5C5C;line-height:1.7;margin:0 0 16px;">Der klassische Einstieg in die Welt der Insel-Whiskys. Rauchig, maritim und mit einer w&uuml;rzigen Pfeffer-Note im Abgang.</p>'
        '<a href="https://www.amazon.de/s?k=Talisker+10&tag=whiskyreise74-21" style="display:inline-block;background:#2C2C2C;color:#fff;text-decoration:none;padding:10px 24px;border-radius:6px;font-size:13px;font-weight:600;">Bei Amazon ansehen &rarr;</a>'
        '</div></td></tr>'
        # REISE TIPP
        '<tr><td style="padding:24px 32px 0;">'
        '<div style="background:#F4F7F4;border-radius:8px;padding:28px;border-left:4px solid #7A9E7E;">'
        '<p style="font-size:11px;color:#7A9E7E;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin:0 0 12px;">&#9992; Reise-Tipp des Monats</p>'
        '<h3 style="font-family:Georgia,serif;font-size:20px;color:#2C2C2C;margin:0 0 12px;">Die North Coast 500</h3>'
        '<p style="font-size:14px;color:#5C5C5C;line-height:1.7;margin:0 0 16px;">Schottlands Antwort auf die Route 66: 500 Meilen entlang der spektakul&auml;ren Nordk&uuml;ste, vorbei an einsamen Str&auml;nden und versteckten Destillerien.</p>'
        '<a href="' + B + '/kategorie/reise.html" style="display:inline-block;background:#7A9E7E;color:#fff;text-decoration:none;padding:10px 24px;border-radius:6px;font-size:13px;font-weight:600;">Reise-Artikel lesen &rarr;</a>'
        '</div></td></tr>'
        # ELMAR REISEPLANUNG
        '<tr><td style="padding:24px 32px 0;">'
        '<div style="background:#2C2C2C;border-radius:8px;padding:32px;">'
        '<p style="font-size:11px;color:#C8963E;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin:0 0 16px;text-align:center;">Schottland-Reise planen</p>'
        '<h3 style="font-family:Georgia,serif;font-size:20px;color:#fff;margin:0 0 16px;text-align:center;">Deine Reise. Von einem, der Schottland kennt.</h3>'
        '<p style="font-size:14px;color:#c8c8c8;line-height:1.7;margin:0 0 8px;text-align:left;">'
        'Elmar ist ausgebildeter <strong style="color:#fff;">Reisekaufmann</strong> und seit &uuml;ber '
        '18 Jahren regelm&auml;&szlig;ig in Schottland unterwegs. Er kennt die versteckten '
        'Destillerien, die sch&ouml;nsten K&uuml;stenstra&szlig;en und die Pubs, in denen noch G&auml;lisch gesprochen wird.</p>'
        '<p style="font-size:14px;color:#c8c8c8;line-height:1.7;margin:16px 0 24px;text-align:left;">'
        'Ob Whisky-Tour durch die Speyside, Roadtrip &uuml;ber die Inseln oder Highland-Wandern &ndash; '
        'Elmar plant deine individuelle Reise mit Profi-Wissen und echtem Schottland-Enthusiasmus.</p>'
        '<div style="text-align:center;">'
        '<a href="mailto:rosenhefter@gmail.com?cc=whisky-news@whisky-reise.com&amp;subject=Schottland-Reiseplanung" style="display:inline-block;background:#C8963E;color:#fff;text-decoration:none;padding:12px 28px;border-radius:6px;font-size:14px;font-weight:600;">Reiseplanung anfragen &rarr;</a>'
        '<p style="font-size:12px;color:#777777;margin:16px 0 0;">110+ besuchte Destillerien &middot; 18+ Jahre Schottland-Erfahrung</p>'
        '</div></div></td></tr>'
        # FOOTER
        '<tr><td style="padding:32px;border-top:1px solid #E8E4DF;margin-top:32px;text-align:center;">'
        '<span style="font-family:Georgia,serif;font-size:18px;color:#2C2C2C;font-weight:700;">whisky</span>'
        '<span style="color:#C8963E;font-size:18px;">.</span>'
        '<span style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#8A8A8A;margin-left:3px;">MAGAZIN</span>'
        '<p style="font-size:12px;color:#8A8A8A;line-height:1.6;margin:12px 0 0;">'
        'Du erh&auml;ltst diese E-Mail, weil du dich f&uuml;r den<br>Whisky Magazin Newsletter angemeldet hast.</p>'
        '<p style="font-size:12px;margin:16px 0 0;">'
        '<a href="' + B + '" style="color:#C8963E;text-decoration:none;">Website</a>'
        ' &middot; <a href="' + B + '/karte.html" style="color:#C8963E;text-decoration:none;">Whisky-Karte</a>'
        ' &middot; <a href="' + B + '/ueber-uns.html" style="color:#C8963E;text-decoration:none;">&Uuml;ber uns</a></p>'
        '<p style="margin:20px 0 0;">'
        '<a href="' + unsub_url + '" style="color:#8A8A8A;font-size:12px;text-decoration:underline;">Newsletter abbestellen</a></p>'
        '<p style="font-size:11px;color:#B0B0B0;margin:12px 0 0;">&copy; 2007&ndash;2026 Whisky Magazin &middot; Steffen &amp; Elmar</p>'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )

    payload = json.dumps({
        "sender": {"name": "Steffen & Elmar", "email": "whisky-news@whisky-reise.com"},
        "to": [{"email": email}],
        "subject": "Willkommen beim Whisky Magazin \u2013 Deine erste Schottland-Post!",
        "htmlContent": welcome_html,
    }).encode("utf-8")

    req = Request("https://api.brevo.com/v3/smtp/email", data=payload, headers={
        "api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json",
    }, method="POST")
    urlopen(req)


def _send_thank_you_feedback(email, name):
    """Branded thank-you e-mail after beta-tester survey submission."""
    first_name = name.split()[0] if name else "du"
    B = BASE_URL
    html = (
        '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1.0"></head>'
        '<body style="margin:0;padding:0;background:#FAFAF7;font-family:Inter,Helvetica,Arial,sans-serif;">'
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#FAFAF7;">'
        '<tr><td align="center" style="padding:32px 16px;">'
        '<table width="560" cellpadding="0" cellspacing="0" border="0" '
        'style="max-width:560px;width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 16px rgba(0,0,0,0.06);">'
        '<tr><td style="background:#2C2C2C;padding:32px;text-align:center;">'
        '<span style="font-family:Georgia,serif;font-size:26px;color:#fff;font-weight:700;">whisky</span>'
        '<span style="color:#C8963E;font-size:26px;">.</span>'
        '<span style="font-size:13px;letter-spacing:3px;text-transform:uppercase;color:#999;margin-left:4px;">MAGAZIN</span>'
        '</td></tr>'
        '<tr><td style="padding:40px 32px 28px;text-align:center;">'
        '<div style="font-size:52px;margin-bottom:20px;">&#127811;</div>'
        '<h1 style="font-family:Georgia,serif;font-size:26px;color:#2C2C2C;margin:0 0 14px;">'
        'Vielen Dank, ' + first_name + '!</h1>'
        '<p style="font-size:15px;color:#5C5C5C;line-height:1.7;margin:0;">'
        'Dein Feedback ist bei uns angekommen. Wir lesen jede Antwort pers&ouml;nlich &ndash; '
        'du hilfst uns wirklich, whisky&#8209;reise.com besser zu machen.</p>'
        '</td></tr>'
        '<tr><td style="padding:0 32px;"><div style="border-top:2px solid #C8963E;width:48px;margin:0 auto;"></div></td></tr>'
        '<tr><td style="padding:28px 32px;">'
        '<div style="background:#1A1A1A;border-radius:10px;padding:28px;text-align:center;">'
        '<p style="font-size:11px;color:#C8963E;text-transform:uppercase;letter-spacing:2px;font-weight:700;margin:0 0 14px;">&#127881; Deine Verlosungs-Teilnahme</p>'
        '<h2 style="font-family:Georgia,serif;font-size:20px;color:#fff;margin:0 0 14px;">Du bist dabei &ndash; Tasting mit Steffen &amp; Elmar</h2>'
        '<p style="font-size:14px;color:#c8c8c8;line-height:1.7;margin:0;">'
        'Wir verlosen <strong style="color:#E8B86D;">3 Pl&auml;tze</strong> f&uuml;r ein pers&ouml;nliches '
        'Whisky-Tasting &ndash; 5 ausgew&auml;hlte Whiskys, gemeinsam mit uns. '
        'Die drei besten Feedbacks gewinnen. Wir melden uns bei dir!</p>'
        '</div></td></tr>'
        '<tr><td style="padding:20px 32px 32px;text-align:center;">'
        '<a href="' + B + '" style="display:inline-block;background:#C8963E;color:#fff;text-decoration:none;'
        'padding:13px 28px;border-radius:6px;font-size:15px;font-weight:600;">Magazin entdecken &rarr;</a>'
        '</td></tr>'
        '<tr><td style="padding:24px 32px;border-top:1px solid #E8E4DF;text-align:center;">'
        '<span style="font-family:Georgia,serif;font-size:16px;color:#2C2C2C;font-weight:700;">whisky</span>'
        '<span style="color:#C8963E;font-size:16px;">.</span>'
        '<span style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#8A8A8A;margin-left:3px;">MAGAZIN</span>'
        '<p style="font-size:12px;color:#8A8A8A;margin:12px 0 0;">'
        'Du erh&auml;ltst diese E-Mail, weil du an unserem Beta-Tester-Feedback teilgenommen hast.</p>'
        '<p style="font-size:11px;color:#B0B0B0;margin:8px 0 0;">'
        '&copy; 2007&ndash;2026 Whisky Magazin &middot; Steffen &amp; Elmar</p>'
        '</td></tr>'
        '</table></td></tr></table></body></html>'
    )
    payload = json.dumps({
        "sender": {"name": "Steffen & Elmar", "email": "whisky-news@whisky-reise.com"},
        "to": [{"email": email, "name": name}],
        "subject": "Danke f\u00fcr dein Feedback \u2013 du bist dabei! \U0001f943",
        "htmlContent": html,
    }).encode("utf-8")
    req = Request("https://api.brevo.com/v3/smtp/email", data=payload, headers={
        "api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json",
    }, method="POST")
    urlopen(req)


def _is_feedback_rate_limited(ip):
    now = time.time()
    _feedback_rate[ip] = [t for t in _feedback_rate[ip] if now - t < 3600]
    if len(_feedback_rate[ip]) >= FEEDBACK_RATE_LIMIT:
        return True
    _feedback_rate[ip].append(now)
    return False


def _send_feedback_email(page_name, page_type, page_url, message, reply_email):
    type_label = {"distillery": "Destillerie", "whisky": "Whisky"}.get(page_type, page_type)
    reply_row = f"<tr><td style='padding:6px 0;color:#5C5C5C;font-size:14px;'><strong>Antwort-Mail:</strong> {reply_email}</td></tr>" if reply_email else ""
    html = (
        '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"></head>'
        '<body style="font-family:Inter,Helvetica,Arial,sans-serif;background:#FAFAF7;margin:0;padding:24px;">'
        '<div style="max-width:520px;margin:0 auto;background:#fff;border-radius:10px;overflow:hidden;'
        'box-shadow:0 2px 12px rgba(0,0,0,0.08);">'
        '<div style="background:#2C2C2C;padding:24px 28px;">'
        '<span style="font-family:Georgia,serif;font-size:20px;color:#fff;font-weight:700;">whisky</span>'
        '<span style="color:#C8963E;font-size:20px;">.</span>'
        '<span style="font-size:12px;letter-spacing:3px;text-transform:uppercase;color:rgba(255,255,255,0.6);margin-left:4px;">MAGAZIN</span>'
        '<p style="font-size:12px;color:#999;margin:8px 0 0;">Redaktionelles Feedback</p>'
        '</div>'
        '<div style="padding:28px 28px 20px;">'
        f'<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">'
        f'<tr><td style="padding:6px 0;color:#5C5C5C;font-size:14px;"><strong>Seite:</strong> <a href="https://www.whisky-reise.com{page_url}" style="color:#C8963E;">{page_name}</a></td></tr>'
        f'<tr><td style="padding:6px 0;color:#5C5C5C;font-size:14px;"><strong>Typ:</strong> {type_label}</td></tr>'
        f'{reply_row}'
        '</table>'
        '<div style="background:#FAF6F0;border-left:4px solid #C8963E;border-radius:0 6px 6px 0;padding:16px 20px;font-size:15px;line-height:1.7;color:#2C2C2C;">'
        f'{message.replace(chr(10), "<br>")}'
        '</div>'
        '</div>'
        '<div style="padding:16px 28px;border-top:1px solid #E8E4DF;font-size:12px;color:#8A8A8A;">'
        '&copy; Whisky Magazin &middot; Automatisch generiert'
        '</div></div></body></html>'
    )
    payload = json.dumps({
        "sender": {"name": "Whisky Magazin Feedback", "email": "whisky-news@whisky-reise.com"},
        "to": [{"email": FEEDBACK_RECIPIENT}],
        "replyTo": {"email": reply_email} if reply_email else {"email": "whisky-news@whisky-reise.com"},
        "subject": f"[Feedback] {type_label}: {page_name}",
        "htmlContent": html,
    }).encode("utf-8")
    req = Request("https://api.brevo.com/v3/smtp/email", data=payload, headers={
        "api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json",
    }, method="POST")
    urlopen(req)


def _cors_headers(origin=""):
    base = {"Access-Control-Allow-Methods": "POST, GET, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"}
    if origin in ALLOWED_ORIGINS:
        base["Access-Control-Allow-Origin"] = origin
    return base


def _is_rate_limited(ip):
    now = time.time()
    _rate_store[ip] = [t for t in _rate_store[ip] if now - t < 60]
    if len(_rate_store[ip]) >= RATE_LIMIT_PER_MINUTE:
        return True
    _rate_store[ip].append(now)
    return False


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        origin = self.headers.get("Origin", "")
        self.send_response(204)
        for k, v in _cors_headers(origin).items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        """Handle DOI confirmation and unsubscribe link clicks."""
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            action = params.get("action", [""])[0]
            email = params.get("email", [""])[0].strip().lower()
            token = params.get("token", [""])[0]

            if action == "confirm" and email and token:
                if _verify_token(email, token):
                    # Check if already in list (prevent duplicate welcome emails on re-click)
                    already_subscribed = False
                    try:
                        check_req = Request("https://api.brevo.com/v3/contacts/" + email, headers={
                            "api-key": BREVO_API_KEY, "Accept": "application/json",
                        }, method="GET")
                        check_resp = urlopen(check_req)
                        check_data = json.loads(check_resp.read().decode())
                        if BREVO_LIST_ID in check_data.get("listIds", []):
                            already_subscribed = True
                    except Exception:
                        pass

                    # Add to Brevo list (updateEnabled=True prevents duplicates)
                    try:
                        payload = json.dumps({"email": email, "listIds": [BREVO_LIST_ID], "updateEnabled": True}).encode("utf-8")
                        req = Request("https://api.brevo.com/v3/contacts", data=payload, headers={
                            "api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json",
                        }, method="POST")
                        urlopen(req)
                    except Exception:
                        pass

                    # Send welcome email only for first-time confirmations
                    if not already_subscribed:
                        try:
                            _send_welcome_email(email)
                        except Exception:
                            pass  # Don't block redirect if welcome email fails

                    self.send_response(302)
                    self.send_header("Location", REDIRECT_URL)
                    self.end_headers()
                    return

            elif action == "unsubscribe" and email and token:
                if _verify_token(email, token):
                    # Remove from Brevo list
                    try:
                        payload = json.dumps({"emails": [email]}).encode("utf-8")
                        req = Request(
                            f"https://api.brevo.com/v3/contacts/lists/{BREVO_LIST_ID}/contacts/remove",
                            data=payload, headers={
                                "api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json",
                            }, method="POST")
                        urlopen(req)
                    except Exception:
                        pass

                    # Show unsubscribe confirmation page
                    unsub_html = (
                        '<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
                        '<meta name="viewport" content="width=device-width,initial-scale=1.0">'
                        '<title>Abmeldung best&auml;tigt</title></head>'
                        '<body style="margin:0;padding:0;background:#FAFAF7;font-family:Inter,Helvetica,Arial,sans-serif;">'
                        '<div style="max-width:520px;margin:80px auto;padding:48px 32px;background:#fff;border-radius:12px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.08);">'
                        '<h1 style="font-family:Georgia,serif;font-size:24px;color:#2C2C2C;margin:0 0 16px;">Abmeldung best&auml;tigt</h1>'
                        '<p style="font-size:15px;color:#5C5C5C;line-height:1.7;margin:0 0 28px;">'
                        'Du wurdest erfolgreich vom Whisky Magazin Newsletter abgemeldet. '
                        'Schade, dass du gehst!</p>'
                        '<a href="' + BASE_URL + '" style="display:inline-block;background:#C8963E;color:#fff;text-decoration:none;padding:12px 28px;border-radius:6px;font-size:14px;font-weight:600;">'
                        'Zur&uuml;ck zum Magazin</a>'
                        '</div></body></html>'
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(unsub_html.encode("utf-8"))
                    return

            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><p>Ungueltiger oder abgelaufener Link.</p></body></html>")
        except Exception:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Server error")

    def do_POST(self):
        origin = self.headers.get("Origin", "")
        cors = _cors_headers(origin)

        try:
            client_ip = self.headers.get("X-Forwarded-For", "unknown")
            if client_ip and "," in client_ip:
                client_ip = client_ip.split(",")[0].strip()
        except Exception:
            client_ip = "unknown"

        if _is_rate_limited(client_ip):
            return self._json(429, {"error": "Zu viele Anfragen. Bitte warte einen Moment."}, cors)

        if origin and origin not in ALLOWED_ORIGINS:
            return self._json(403, {"error": "Zugriff verweigert."}, cors)

        try:
            length = int(self.headers.get("Content-Length", 0))
            if length > 4096:
                return self._json(400, {"error": "Anfrage zu gross."}, cors)
            body = json.loads(self.rfile.read(length)) if length else {}
        except Exception:
            return self._json(400, {"error": "Ungueltige Anfrage."}, cors)

        # Feedback-Aktion (redaktionelle Anmerkungen)
        if body.get("action") == "feedback":
            honeypot = body.get("honeypot", "")
            if honeypot:
                return self._json(400, {"error": "Ungueltige Anfrage."}, cors)
            source = body.get("source", "")
            if source in TRUSTED_FORM_SOURCES:
                # Glossar-Feedback hat kein Captcha-Widget. Stattdessen striktes IP-Limit.
                if _is_trusted_form_rate_limited(client_ip):
                    return self._json(429, {"error": "Zu viele Anfragen. Bitte warte eine Stunde."}, cors)
            else:
                if not _verify_turnstile(body.get("turnstile_token", ""), client_ip):
                    return self._json(400, {"error": "Captcha-Pruefung fehlgeschlagen. Bitte Seite neu laden."}, cors)
            if _is_feedback_rate_limited(client_ip):
                return self._json(429, {"error": "Zu viele Feedback-Einsendungen. Bitte warte eine Stunde."}, cors)
            message = (body.get("message") or "").strip()
            if len(message) < 20:
                return self._json(400, {"error": "Bitte mindestens 20 Zeichen eingeben."}, cors)
            if len(message) > 2000:
                return self._json(400, {"error": "Nachricht zu lang (max. 2000 Zeichen)."}, cors)
            page_name = (body.get("page_name") or "")[:200]
            page_type = (body.get("page_type") or "")[:50]
            page_url = (body.get("page_url") or "")[:300]
            reply_email = (body.get("reply_email") or "").strip().lower()
            if reply_email and not EMAIL_REGEX.match(reply_email):
                reply_email = ""
            if not BREVO_API_KEY:
                return self._json(500, {"error": "Mail-Service nicht konfiguriert."}, cors)
            try:
                _send_feedback_email(page_name, page_type, page_url, message, reply_email)
                return self._json(200, {"ok": True}, cors)
            except Exception as exc:
                return self._json(500, {"error": str(exc)}, cors)

        # Thank-you e-mail action (beta-tester survey)
        if body.get("action") == "thankyou":
            source = body.get("source", "")
            if source in TRUSTED_FORM_SOURCES:
                if _is_trusted_form_rate_limited(client_ip):
                    return self._json(429, {"error": "Zu viele Anfragen. Bitte warte eine Stunde."}, cors)
            else:
                if not _verify_turnstile(body.get("turnstile_token", ""), client_ip):
                    return self._json(400, {"error": "Captcha-Pruefung fehlgeschlagen. Bitte Seite neu laden."}, cors)
            email = (body.get("email") or "").strip().lower()
            name = (body.get("name") or "").strip()
            if not email or not BREVO_API_KEY:
                return self._json(400, {"error": "E-Mail oder API-Key fehlt."}, cors)
            try:
                _send_thank_you_feedback(email, name)
                return self._json(200, {"ok": True}, cors)
            except Exception as exc:
                return self._json(500, {"error": str(exc)}, cors)

        email = (body.get("email") or "").strip().lower()
        if not email or not EMAIL_REGEX.match(email) or len(email) > 254:
            return self._json(400, {"error": "Bitte gib eine gueltige E-Mail-Adresse ein."}, cors)

        source = body.get("source", "")
        if source in TRUSTED_FORM_SOURCES:
            # Newsletter-Anmeldung aus Beta-Fragebogen (kein Captcha-Widget vorhanden).
            if _is_trusted_form_rate_limited(client_ip):
                return self._json(429, {"error": "Zu viele Anfragen. Bitte warte eine Stunde."}, cors)
        elif not _verify_turnstile(body.get("turnstile_token", ""), client_ip):
            return self._json(400, {"error": "Captcha-Pruefung fehlgeschlagen. Bitte Seite neu laden."}, cors)

        if not BREVO_API_KEY:
            return self._json(500, {"error": "Newsletter-Service nicht konfiguriert."}, cors)

        # Check if already subscribed or DOI pending
        try:
            req = Request("https://api.brevo.com/v3/contacts/" + email, headers={
                "api-key": BREVO_API_KEY, "Accept": "application/json",
            }, method="GET")
            resp = urlopen(req)
            contact = json.loads(resp.read().decode())
            if BREVO_LIST_ID in contact.get("listIds", []):
                return self._json(200, {"message": "Du bist bereits angemeldet!"}, cors)
            # Contact exists but not in list = DOI was sent but not confirmed, or unsubscribed
            # Allow re-send of DOI email (user may have missed it)
        except HTTPError as e:
            if e.code == 404:
                pass  # New contact, proceed with DOI
            else:
                return self._json(500, {"error": "Anmeldung fehlgeschlagen. Bitte versuche es sp\u00e4ter."}, cors)
        except Exception:
            return self._json(500, {"error": "Anmeldung fehlgeschlagen. Bitte versuche es sp\u00e4ter."}, cors)

        # Send DOI email via Brevo transactional API
        try:
            token = _make_token(email)
            confirm_url = BASE_URL + "/api/subscribe?action=confirm&email=" + email + "&token=" + token
            html = DOI_HTML.replace("CONFIRM_URL_PLACEHOLDER", confirm_url)

            payload = json.dumps({
                "sender": {"name": "Steffen & Elmar", "email": "whisky-news@whisky-reise.com"},
                "to": [{"email": email}],
                "subject": "Bitte best\u00e4tige deine Anmeldung zum Whisky Magazin Newsletter",
                "htmlContent": html,
            }).encode("utf-8")

            req = Request("https://api.brevo.com/v3/smtp/email", data=payload, headers={
                "api-key": BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json",
            }, method="POST")
            urlopen(req)

            return self._json(200, {
                "message": "Bitte E-Mail best\u00e4tigen!"
            }, cors)
        except Exception:
            return self._json(500, {
                "error": "Anmeldung fehlgeschlagen. Bitte versuche es sp\u00e4ter."
            }, cors)

    def _json(self, status, data, cors):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        for k, v in cors.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, fmt, *args):
        pass
