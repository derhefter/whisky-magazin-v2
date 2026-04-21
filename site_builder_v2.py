"""
Site Builder: Generiert eine komplette statische Website aus Artikel-Daten.
Erstellt HTML-Seiten, Startseite, Kategorie-Seiten und Sitemap.
"""

import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
SITE_DIR = PROJECT_DIR / "site-v2"
ARTICLES_DIR = PROJECT_DIR / "articles"

# Flag: CSS wurde bereits extrahiert und geschrieben
_CSS_EXTRACTED = False

# Pinterest Tracking Tag (wird auf jeder Seite vor </head> eingefügt)
_PINTEREST_TAG = """    <!-- Pinterest Tag -->
    <script>
    !function(e){if(!window.pintrk){window.pintrk = function () {
    window.pintrk.queue.push(Array.prototype.slice.call(arguments))};var
      n=window.pintrk;n.queue=[],n.version="3.0";var
      t=document.createElement("script");t.async=!0,t.src=e;var
      r=document.getElementsByTagName("script")[0];
      r.parentNode.insertBefore(t,r)}}("https://s.pinimg.com/ct/core.js");
    pintrk('load', '2613413631015');
    pintrk('page');
    </script>
    <noscript>
    <img height="1" width="1" style="display:none;" alt=""
      src="https://ct.pinterest.com/v3/?event=init&tid=2613413631015&noscript=1" />
    </noscript>
    <!-- end Pinterest Tag -->"""


def _externalize_css(html_content):
    """Extrahiert inline-CSS aus HTML, schreibt es einmalig als style.css,
    und ersetzt den <style>-Block durch einen <link>-Tag."""
    global _CSS_EXTRACTED
    style_start = html_content.find('    <style>')
    style_end = html_content.find('    </style>') + len('    </style>')
    if style_start < 0 or style_end <= style_start:
        return html_content

    css_content = html_content[style_start + len('    <style>\n'):style_end - len('\n    </style>')]

    if not _CSS_EXTRACTED:
        css_path = SITE_DIR / "style.css"
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(css_content.strip() + "\n")
        _CSS_EXTRACTED = True

    link_tag = '    <link rel="stylesheet" href="/style.css">'
    return html_content[:style_start] + link_tag + html_content[style_end:]


# ============================================================
# Produkt-Datenbank für Amazon-Affiliate-Links
# ============================================================
_PRODUCTS_CACHE = None

def _load_products():
    """Lädt die Produkt-Datenbank mit ASINs."""
    global _PRODUCTS_CACHE
    if _PRODUCTS_CACHE is not None:
        return _PRODUCTS_CACHE
    products_path = PROJECT_DIR / "data" / "products.json"
    if products_path.exists():
        with open(products_path, "r", encoding="utf-8") as f:
            _PRODUCTS_CACHE = json.load(f)
    else:
        _PRODUCTS_CACHE = {}
    return _PRODUCTS_CACHE


def _amazon_search_url(product_name, tag="whiskyreise74-21"):
    """Erstellt eine Amazon-Such-URL aus einem Produktnamen."""
    from urllib.parse import quote_plus
    search_term = quote_plus(product_name)
    return f"https://www.amazon.de/s?k={search_term}&tag={tag}"


def _build_product_box(product, tag="whiskyreise74-21"):
    """Erstellt HTML für eine Produktbox."""
    url = _amazon_search_url(product["name"], tag)
    price = product.get("price_range", "")
    price_html = f'<span class="product-price">ca. {price} &euro;</span>' if price else ''
    return f'''<div class="product-box">
        <div class="product-info">
            <h4 class="product-name">{product["name"]}</h4>
            <p class="product-desc">{product["short"]}</p>
            {price_html}
        </div>
        <a href="{url}" target="_blank" rel="noopener noreferrer sponsored" class="btn btn-primary product-btn">Bei Amazon ansehen &rarr;</a>
    </div>'''


def _enhance_amazon_links(html_content, tag="whiskyreise74-21"):
    """Prüft Amazon-Links – Search-URLs bleiben erhalten (keine ASIN-Konvertierung)."""
    # Search-URLs (amazon.de/s?k=...) sind zuverlässiger als ASIN-Direktlinks,
    # da ASINs sich ändern können und dann zu 404-Seiten führen.
    # Diese Funktion lässt bestehende Search-URLs unverändert.
    return html_content


def _inject_product_boxes(html_content, tag="whiskyreise74-21"):
    """Fügt Produktboxen nach <h2>/<h3> Überschriften ein, die Produktnamen enthalten."""
    products = _load_products()
    if not products:
        return html_content

    all_products = {}
    for section in ["whiskys", "zubehoer"]:
        all_products.update(products.get(section, {}))

    # Generische Begriffe die in fast jedem Whisky-Artikel vorkommen –
    # als Suchwort ungeeignet, weil sie sonst überall matchen.
    _GENERIC = {
        "Whisky", "Whiskey", "Single", "Malt", "Scotch", "Bourbon",
        "Irish", "Das", "Die", "Der", "Ein", "Set", "Glas", "Tasting",
    }

    # Finde Stellen wo ein Produkt in einer Überschrift erwähnt wird
    inserted = set()
    for key, prod in all_products.items():
        # Suche nach dem spezifischsten Wort im Produktnamen (kein generischer Begriff)
        name_parts = prod["name"].split()
        search_term = ""
        for part in name_parts:
            clean = part.strip("()")
            if len(clean) >= 5 and clean not in _GENERIC:
                search_term = clean
                break
        if not search_term:
            continue

        # Suche nach </h2> oder </h3> nach einer Überschrift die den Produktnamen enthält
        pattern = re.compile(
            rf'(<h[23][^>]*>[^<]*{re.escape(search_term)}[^<]*</h[23]>)',
            re.IGNORECASE
        )
        match = pattern.search(html_content)
        if match and key not in inserted:
            box = _build_product_box(prod, tag)
            # Füge Box nach dem nächsten </p> ein
            p_end = html_content.find('</p>', match.end())
            if p_end > 0:
                insert_pos = p_end + len('</p>')
                html_content = html_content[:insert_pos] + '\n' + box + html_content[insert_pos:]
                inserted.add(key)

    return html_content


# ============================================================
# Deutsche Monatsnamen
# ============================================================
MONATE = {
    "January": "Januar", "February": "Februar", "March": "März",
    "April": "April", "May": "Mai", "June": "Juni",
    "July": "Juli", "August": "August", "September": "September",
    "October": "Oktober", "November": "November", "December": "Dezember",
}


def _json_ld_article(article, base_url):
    """Erzeugt JSON-LD Structured Data für einen Artikel."""
    slug = article.get("meta", {}).get("slug", "")
    meta = article.get("meta", {})
    img = article.get("image_url", "")
    if img and not img.startswith("http"):
        img = f"{base_url}{img}"
    date_pub = article.get("date", "")
    # Wortanzahl aus dem Content berechnen
    content_text = re.sub(r"<[^>]+>", "", article.get("html_content", article.get("content", "")))
    word_count = len(content_text.split())
    ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article.get("title", ""),
        "description": meta.get("meta_description", ""),
        "image": img,
        "datePublished": date_pub,
        "dateModified": date_pub,
        "wordCount": word_count,
        "inLanguage": "de-DE",
        "author": {
            "@type": "Organization",
            "name": "Steffen & Elmar",
            "url": f"{base_url}/ueber-uns.html"
        },
        "publisher": {
            "@type": "Organization",
            "name": "Whisky Magazin",
            "url": base_url,
            "logo": {
                "@type": "ImageObject",
                "url": f"{base_url}/images/authors-steffen-elmar.jpg"
            }
        },
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"{base_url}/artikel/{slug}.html"
        }
    }
    return f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'


def _json_ld_website(base_url):
    """Erzeugt JSON-LD WebSite Schema mit SearchAction für die Startseite."""
    ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Whisky Magazin",
        "alternateName": "Whisky Reise",
        "url": base_url,
        "description": "Dein Guide für Whisky, Destillerien & Reisen – seit 2007",
        "inLanguage": "de-DE",
        "potentialAction": {
            "@type": "SearchAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": f"{base_url}/suche.html?q={{search_term_string}}"
            },
            "query-input": "required name=search_term_string"
        },
        "publisher": {
            "@type": "Organization",
            "name": "Whisky Magazin",
            "url": base_url,
            "logo": {
                "@type": "ImageObject",
                "url": f"{base_url}/images/authors-steffen-elmar.jpg"
            },
            "foundingDate": "2007",
            "description": "Whisky Magazin – Schottland-Reisen, Destillerie-Besuche und Whisky-Wissen seit 2007. Von Steffen & Elmar.",
            "sameAs": [
                f"{base_url}/ueber-uns.html"
            ]
        }
    }
    return f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'


def _json_ld_breadcrumb(items, base_url):
    """Erzeugt JSON-LD BreadcrumbList Schema."""
    item_list = []
    for i, (name, url) in enumerate(items, 1):
        item_list.append({
            "@type": "ListItem",
            "position": i,
            "name": name,
            "item": f"{base_url}{url}" if not url.startswith("http") else url
        })
    ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": item_list
    }
    return f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'


def _german_date(date_str):
    """Wandelt ein Datum in deutsches Format um."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        month_en = dt.strftime("%B")
        month_de = MONATE.get(month_en, month_en)
        return f"{dt.day}. {month_de} {dt.year}"
    except Exception:
        return date_str


# ============================================================
# HTML-Templates (eingebettet - keine externen Abhängigkeiten)
# ============================================================

def _base_template():
    """Basis-HTML-Template für alle Seiten."""
    return """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="google-site-verification" content="3OKzP9zKRrZV5V4-chXaN7GG39fdLAEeymXqKeqn4Rw">
    <meta name="p:domain_verify" content="4b7a0461f2dd530e9a9c5894618a229d">
    <title>{title} | {site_name}</title>
    <meta name="description" content="{meta_description}">
    <meta name="keywords" content="{keywords}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{og_description}">
    <meta property="og:type" content="article">
    <meta property="og:image" content="{og_image}">
    <meta property="og:url" content="{canonical_url}">
    <meta property="og:site_name" content="Whisky Magazin">
    <meta property="og:locale" content="de_DE">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{og_description}">
    <meta name="twitter:image" content="{og_image}">
    <link rel="canonical" href="{canonical_url}">
    <link rel="alternate" hreflang="de" href="{canonical_url}">
    <link rel="alternate" hreflang="x-default" href="{canonical_url}">
    <link rel="alternate" type="application/rss+xml" title="Whisky Magazin RSS" href="{base_url}/feed.xml">
    <!-- Favicon / App-Icons -->
    <link rel="icon" type="image/svg+xml" href="/favicon.svg">
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
    <link rel="shortcut icon" href="/favicon.ico">
    <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
    <link rel="manifest" href="/site.webmanifest">
    <meta name="theme-color" content="#1C1108">
    {json_ld}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400;1,9..144,500;1,9..144,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #FAFAF7;
            --bg-surface: #F5F0E8;
            --bg-elevated: #FFFFFF;
            --text-primary: #1A1A1A;
            --text-secondary: #5C5C5C;
            --accent-amber: #C8963E;
            --accent-warm: #8B7355;
            --accent-sage: #4A7C5E;
            --accent-muted: #8B7355;
            --border: #E8DCC8;
            --shadow-sm: 0 2px 12px rgba(139,115,85,0.08);
            --shadow-hover: 0 4px 24px rgba(139,115,85,0.14);
            --radius-sm: 6px;
            --radius-pill: 24px;
            --max-width: 1200px;
            --article-max: 720px;
            --sidebar-width: 300px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-weight: 400;
            color: var(--text-primary);
            background-color: var(--bg-primary);
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.015'/%3E%3C/svg%3E");
            line-height: 1.7;
            font-size: 17px;
            margin: 0;
            -webkit-font-smoothing: antialiased;
        }}

        /* --- HEADER --- */
        .site-header {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: rgba(250,250,247,0.92);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 0 24px;
            height: 64px;
        }}
        .header-inner {{
            max-width: var(--max-width);
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
            height: 100%;
        }}
        .site-logo {{
            font-family: 'Fraunces', Georgia, serif;
            font-weight: 600;
            font-size: 22px;
            color: var(--text-primary);
            text-decoration: none;
            letter-spacing: -0.5px;
        }}
        .site-logo .logo-dot {{
            color: var(--accent-amber);
            font-size: 28px;
            line-height: 1;
        }}
        .site-logo .logo-magazin {{
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-left: 4px;
        }}
        .site-nav {{ display: flex; align-items: center; gap: 28px; }}
        .site-nav a {{
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 500;
            color: var(--text-secondary);
            text-decoration: none;
            transition: color 0.2s;
        }}
        .site-nav a:hover {{ color: var(--accent-amber); }}
        .site-nav a.active {{
            color: var(--accent-amber);
            position: relative;
        }}
        .site-nav a.active::after {{
            content: '';
            position: absolute;
            bottom: -20px;
            left: 0; right: 0;
            height: 2px;
            background: var(--accent-amber);
        }}
        .nav-toggle {{
            display: none;
            align-items: center;
            justify-content: center;
            min-width: 44px;
            min-height: 44px;
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: var(--text-primary);
            padding: 4px 8px;
            line-height: 1;
            touch-action: manipulation;
            -webkit-tap-highlight-color: transparent;
        }}

        /* --- HEADINGS --- */
        h1, h2, h3, h4 {{
            font-family: 'Fraunces', Georgia, serif;
            color: var(--text-primary);
            line-height: 1.3;
        }}
        h1 {{ font-size: 32px; font-weight: 700; }}
        h2 {{ font-size: 22px; font-weight: 600; position: relative; padding-left: 20px; margin-top: 40px; }}
        h2::before {{
            content: '';
            position: absolute;
            left: 0;
            top: 8px;
            width: 8px;
            height: 8px;
            background: var(--accent-warm);
        }}
        h3 {{ font-size: 18px; font-weight: 600; }}

        /* --- BUTTONS --- */
        .btn {{ display: inline-block; padding: 10px 24px; font-family: 'Inter', sans-serif; font-size: 14px; font-weight: 500; border-radius: var(--radius-sm); text-decoration: none; cursor: pointer; transition: all 0.2s; border: none; }}
        .btn-primary {{ background: var(--accent-amber); color: #fff; }}
        .btn-primary:hover {{ background: #A67A2E; }}
        .btn-ghost {{ background: transparent; border: 1.5px solid var(--accent-amber); color: var(--accent-amber); }}
        .btn-ghost:hover {{ background: var(--accent-amber); color: #fff; }}
        .btn-secondary {{ background: transparent; border: 1.5px solid var(--accent-sage); color: var(--accent-sage); }}
        .btn-secondary:hover {{ background: var(--accent-sage); color: #fff; }}

        /* --- BADGES --- */
        .badge {{ display: inline-block; padding: 4px 12px; font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; border-radius: var(--radius-pill); }}
        .badge-amber {{ background: var(--accent-amber); color: #fff; }}
        .badge-warm {{ background: var(--accent-warm); color: #fff; }}
        .badge-sage {{ background: var(--accent-sage); color: #fff; }}
        .badge-outline {{ background: transparent; border: 1px solid var(--border); color: var(--text-secondary); }}

        /* --- CARDS --- */
        .card {{
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow-sm);
            overflow: hidden;
            transition: box-shadow 0.2s, transform 0.2s;
        }}
        .card:hover {{
            box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }}
        .card-image {{ width: 100%; aspect-ratio: 3/2; object-fit: cover; background: linear-gradient(135deg, var(--bg-surface) 0%, var(--border) 100%); }}
        .card-body {{ padding: 20px; }}
        .card-body .badge {{ margin-bottom: 8px; }}
        .card-title {{ font-family: 'Fraunces', serif; font-size: 18px; font-weight: 600; margin: 0 0 8px; line-height: 1.3; }}
        .card-title a {{ color: var(--text-primary); text-decoration: none; }}
        .card-title a:hover {{ color: var(--accent-amber); }}
        .card-meta {{ font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }}
        .card-teaser {{ font-size: 15px; color: var(--text-secondary); line-height: 1.6; }}

        /* --- BLOCKQUOTE --- */
        blockquote {{
            font-family: 'Fraunces', serif;
            font-style: italic;
            font-size: 18px;
            color: var(--text-primary);
            border-left: 3px solid var(--accent-amber);
            padding: 4px 0 4px 24px;
            margin: 32px 0;
            background: none;
        }}

        /* --- HERO (nur Startseite) --- */
        .hero {{
            background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-primary) 50%, var(--accent-amber) 100%);
            color: #fff;
            text-align: center;
            padding: 80px 24px 70px;
        }}
        .hero h1 {{
            font-size: 2.8em;
            margin-bottom: 12px;
            letter-spacing: 3px;
            font-weight: 400;
        }}
        .hero p {{
            font-size: 1.15em;
            opacity: 0.85;
            max-width: 600px;
            margin: 0 auto;
        }}

        /* --- MAIN --- */
        .container {{
            max-width: var(--max-width);
            margin: 0 auto;
            padding: 40px 24px;
        }}
        .content-grid {{
            display: grid;
            grid-template-columns: 1fr var(--sidebar-width);
            gap: 40px;
        }}
        @media (max-width: 900px) {{
            .content-grid {{ grid-template-columns: 1fr; }}
        }}

        /* --- ARTIKELKARTEN (Startseite) --- */
        .article-card {{
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow-sm);
            overflow: hidden;
            margin-bottom: 28px;
            transition: box-shadow 0.2s, transform 0.2s;
        }}
        .article-card:hover {{
            box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }}
        .article-card .card-body {{
            padding: 20px;
        }}
        .article-card .card-meta {{
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 8px;
            display: flex;
            gap: 16px;
        }}
        .article-card .card-meta .cat {{
            background: var(--bg-surface);
            color: var(--text-primary);
            padding: 2px 10px;
            border-radius: var(--radius-pill);
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .article-card h2 {{
            font-family: 'Fraunces', serif;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 10px;
            line-height: 1.3;
            padding-left: 0;
        }}
        .article-card h2::before {{ display: none; }}
        .article-card h2 a {{
            color: var(--text-primary);
            text-decoration: none;
        }}
        .article-card h2 a:hover {{
            color: var(--accent-amber);
        }}
        .article-card .teaser {{
            color: var(--text-secondary);
            font-size: 15px;
            margin-bottom: 16px;
            line-height: 1.6;
        }}
        .read-more {{
            font-family: 'Inter', sans-serif;
            color: var(--accent-amber);
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
        }}
        .read-more:hover {{ text-decoration: underline; }}

        /* --- ARTIKEL-SEITE --- */
        .article-header {{
            background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-primary) 100%);
            color: #fff;
            padding: 60px 24px 50px;
            text-align: center;
        }}
        .article-header h1 {{
            font-size: 32px;
            max-width: 800px;
            margin: 0 auto 16px;
            line-height: 1.3;
        }}
        .article-header .meta-line {{
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            opacity: 0.75;
        }}
        .article-body {{
            background: var(--bg-elevated);
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow-sm);
            padding: 48px;
            margin-top: -30px;
            position: relative;
        }}
        .article-body h2 {{
            color: var(--text-primary);
            font-size: 22px;
            margin: 36px 0 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--bg-surface);
        }}
        .article-body h3 {{
            color: var(--accent-amber);
            font-size: 18px;
            margin: 28px 0 12px;
        }}
        .article-body p {{ margin-bottom: 18px; }}
        .article-body ul, .article-body ol {{
            margin: 16px 0;
            padding-left: 28px;
        }}
        .article-body li {{ margin-bottom: 8px; }}
        .article-body blockquote {{
            font-family: 'Fraunces', serif;
            font-style: italic;
            font-size: 18px;
            color: var(--text-primary);
            border-left: 3px solid var(--accent-amber);
            padding: 4px 0 4px 24px;
            margin: 32px 0;
            background: none;
        }}
        .article-body a {{
            color: var(--accent-amber);
            text-decoration: underline;
            text-decoration-color: var(--accent-amber);
        }}
        .article-body a:hover {{ color: var(--text-primary); }}
        .article-body a.btn-primary,
        .article-body a.btn-primary:hover {{
            color: #fff !important;
            text-decoration: none !important;
        }}
        .article-body a.btn-primary:hover {{
            background: #b8860b !important;
        }}

        .affiliate-link {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: var(--accent-amber);
            color: #fff !important;
            padding: 3px 10px 3px 8px;
            border-radius: var(--radius-sm);
            text-decoration: none !important;
            border-bottom: none !important;
            font-size: 14px;
            font-weight: 500;
            font-family: 'Inter', sans-serif;
            transition: background 0.2s, transform 0.1s;
            white-space: nowrap;
        }}
        .affiliate-link::before {{ content: "→"; font-size: 0.8em; }}
        .affiliate-link:hover {{
            background: #A67A2E;
            transform: translateY(-1px);
            color: #fff !important;
        }}

        /* Produktboxen */
        .product-box {{
            display: flex;
            align-items: center;
            gap: 20px;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            padding: 20px 24px;
            margin: 24px 0;
            transition: box-shadow 0.2s;
        }}
        .product-box:hover {{ box-shadow: var(--shadow-hover); }}
        .product-info {{ flex: 1; }}
        .product-name {{
            font-family: 'Fraunces', serif;
            font-size: 16px;
            font-weight: 600;
            margin: 0 0 4px;
            padding-left: 0;
            color: var(--text-primary);
        }}
        .product-name::before {{ display: none; }}
        .product-desc {{
            font-size: 13px;
            color: var(--text-secondary);
            margin: 0 0 6px;
            line-height: 1.4;
        }}
        .product-price {{
            font-size: 15px;
            font-weight: 700;
            color: var(--accent-amber);
        }}
        .product-btn {{
            flex-shrink: 0;
            font-size: 13px;
            padding: 10px 18px;
            white-space: nowrap;
            color: #fff !important;
            background: var(--accent-amber) !important;
        }}
        .product-btn:hover {{
            color: #fff !important;
            background: #b8860b !important;
        }}
        @media (max-width: 600px) {{
            .product-box {{ flex-direction: column; align-items: stretch; text-align: center; }}
            .product-btn {{ align-self: center; }}
        }}

        .related-box {{
            background: var(--bg-surface);
            border-radius: var(--radius-sm);
            padding: 24px;
            margin-top: 36px;
            border: 1px solid var(--border);
        }}
        .related-box h3 {{
            color: var(--text-primary);
            margin-bottom: 12px;
            border: none;
            padding-left: 0;
        }}
        .related-box h3::before {{ display: none; }}

        /* --- SIDEBAR --- */
        .sidebar {{
            font-family: 'Inter', sans-serif;
        }}
        .sidebar-box {{
            background: var(--bg-elevated);
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            box-shadow: var(--shadow-sm);
            padding: 24px;
            margin-bottom: 24px;
        }}
        .sidebar-box h3 {{
            color: var(--text-primary);
            font-size: 14px;
            margin-bottom: 14px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--bg-surface);
            font-family: 'Fraunces', Georgia, serif;
            padding-left: 0;
        }}
        .sidebar-box h3::before {{ display: none; }}
        .sidebar-box ul {{ list-style: none; padding: 0; }}
        .sidebar-box li {{ margin-bottom: 10px; }}
        .sidebar-box a {{
            color: var(--text-primary);
            text-decoration: none;
            font-size: 14px;
        }}
        .sidebar-box a:hover {{ color: var(--accent-amber); }}

        .tag-cloud {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .tag {{
            background: var(--bg-surface);
            color: var(--text-primary);
            padding: 4px 12px;
            border-radius: var(--radius-pill);
            font-size: 12px;
            text-decoration: none;
            transition: background 0.2s;
        }}
        .tag:hover {{
            background: var(--accent-amber);
            color: #fff;
        }}

        .cta-box {{
            background: var(--text-primary);
            color: var(--bg-surface);
            border-radius: var(--radius-sm);
            padding: 28px;
            text-align: center;
        }}
        .cta-box h3 {{ color: var(--accent-amber); border: none; padding-left: 0; }}
        .cta-box h3::before {{ display: none; }}
        .cta-box p {{ font-size: 14px; margin: 10px 0 16px; opacity: 0.85; }}
        .cta-box a {{
            display: inline-block;
            background: var(--accent-amber);
            color: #fff;
            padding: 10px 28px;
            border-radius: var(--radius-sm);
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
        }}
        .cta-box a:hover {{ background: #A67A2E; }}

        /* --- TAGS --- */
        .article-tags {{
            margin-top: 32px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}

        /* --- FOOTER --- */
        .site-footer {{
            background: var(--text-primary);
            color: var(--bg-surface);
            padding: 64px 24px 32px;
            margin-top: 80px;
        }}
        .footer-inner {{
            max-width: var(--max-width);
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 48px;
        }}
        .footer-logo {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 20px; color: var(--bg-primary); margin-bottom: 12px; }}
        .footer-tagline {{ font-size: 14px; color: var(--accent-muted); line-height: 1.6; }}
        .footer-nav h4 {{ font-family: 'Fraunces', serif; font-size: 14px; font-weight: 600; color: var(--bg-primary); margin-bottom: 16px; text-transform: uppercase; letter-spacing: 1px; padding-left: 0; }}
        .footer-nav h4::before {{ display: none; }}
        .footer-nav a {{ display: block; font-size: 14px; color: var(--accent-muted); text-decoration: none; margin-bottom: 8px; transition: color 0.2s; }}
        .footer-nav a:hover {{ color: var(--accent-amber); }}
        .footer-bottom {{
            max-width: var(--max-width);
            margin: 48px auto 0;
            padding-top: 24px;
            border-top: 1px solid rgba(221,213,200,0.2);
            display: flex;
            justify-content: space-between;
            font-size: 13px;
            color: var(--accent-muted);
        }}
        .footer-quote {{ font-family: 'Fraunces', serif; font-style: italic; font-size: 14px; color: var(--accent-muted); }}

        /* --- CARD IMAGE --- */
        .card-image-wrapper {{
            position: relative;
            overflow: hidden;
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
            height: 210px;
        }}
        .card-image {{
            width: 100%; height: 210px; object-fit: cover;
            display: block;
            transition: transform 0.5s ease;
        }}
        .article-card:hover .card-image {{
            transform: scale(1.04);
        }}
        .card-image-wrapper::after {{
            content: '';
            position: absolute; inset: 0;
            background: linear-gradient(
                to bottom,
                rgba(42, 37, 32, 0.02) 0%,
                rgba(42, 37, 32, 0.15) 100%
            );
            pointer-events: none;
        }}
        .card-image-placeholder {{
            width: 100%; height: 210px;
            background: linear-gradient(135deg, var(--bg-surface) 0%, var(--border) 100%);
            display: flex; align-items: center; justify-content: center;
            font-size: 3em; color: var(--accent-amber);
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
        }}

        /* --- ARTICLE HERO IMAGE --- */
        .article-hero-image {{
            width: 100%; max-height: 480px; object-fit: cover; display: block;
        }}
        .article-image-credit {{
            font-family: 'Inter', sans-serif;
            font-size: 12px; color: var(--text-secondary);
            text-align: right; padding: 4px 8px; background: var(--bg-surface);
        }}
        .article-image-credit a {{ color: var(--text-secondary); }}

        /* --- EMPFEHLUNG BOX --- */
        .empfehlung-box {{
            border-left: 4px solid var(--accent-amber);
            background: var(--bg-surface);
            border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
            padding: 24px 28px; margin: 32px 0;
            display: flex; align-items: flex-start; gap: 16px;
        }}
        .empfehlung-box h3 {{
            font-family: 'Fraunces', serif;
            font-size: 16px;
            margin: 0 0 8px;
            padding-left: 0;
        }}
        .empfehlung-box h3::before {{ display: none; }}
        .empfehlung-box .emp-icon {{ font-size: 2em; flex-shrink: 0; margin-top: 2px; }}
        .empfehlung-box .emp-content {{ flex: 1; }}
        .empfehlung-box .emp-title {{
            font-family: 'Fraunces', serif; font-weight: 600;
            color: var(--text-primary); font-size: 16px; margin-bottom: 6px;
        }}
        .empfehlung-box .emp-text {{
            font-size: 14px; color: var(--text-secondary); margin-bottom: 12px;
            font-family: 'Inter', sans-serif;
        }}
        .empfehlung-box .emp-cta {{
            display: inline-block; background: var(--accent-amber);
            color: #fff !important; padding: 8px 20px; border-radius: var(--radius-sm);
            text-decoration: none !important; font-weight: 500; font-size: 14px;
            font-family: 'Inter', sans-serif;
            transition: background 0.2s; margin-right: 8px; margin-bottom: 4px;
        }}
        .empfehlung-box .emp-cta:hover {{ background: #A67A2E; color: #fff !important; }}

        /* --- SHARE BUTTONS --- */
        .share-bar {{
            display: flex; gap: 10px; margin: 28px 0 20px;
            flex-wrap: wrap; align-items: center;
        }}
        .share-label {{
            font-size: 13px; color: var(--text-secondary);
            font-family: 'Inter', sans-serif;
        }}
        .share-btn {{
            display: inline-flex; align-items: center; gap: 6px;
            padding: 8px 16px; border-radius: var(--radius-pill);
            text-decoration: none !important; font-size: 12px;
            font-family: 'Inter', sans-serif;
            font-weight: 500; transition: opacity 0.2s; color: #fff !important;
        }}
        .share-btn:hover {{ opacity: 0.85; }}
        .share-btn-whatsapp {{ background: #25D366; }}
        .share-btn-x {{ background: #000; }}
        .share-btn-pinterest {{ background: #E60023; }}
        .share-btn-email {{ background: var(--text-primary); }}

        /* --- BREADCRUMB --- */
        .breadcrumb {{
            background: var(--bg-surface); padding: 10px 24px;
            font-family: 'Inter', sans-serif;
            font-size: 13px; color: var(--text-secondary);
        }}
        .breadcrumb-inner {{ max-width: var(--max-width); margin: 0 auto; }}
        .breadcrumb a {{ color: var(--text-secondary); text-decoration: none; }}
        .breadcrumb a:hover {{ color: var(--accent-amber); }}

        /* --- RELATED GRID --- */
        .related-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 12px; }}
        .related-item {{
            background: var(--bg-primary); border-radius: var(--radius-sm);
            padding: 12px 14px; text-decoration: none !important;
            border-left: 3px solid var(--accent-amber);
            color: var(--text-primary) !important; font-size: 14px;
            line-height: 1.4; transition: background 0.2s, border-color 0.2s; display: block;
        }}
        .related-item:hover {{ background: var(--bg-surface); border-left-color: var(--accent-warm); }}

        /* --- PERSONAL PHOTO BADGE --- */
        .personal-photo-wrapper {{ position: relative; display: block; }}
        .personal-photo-badge {{
            position: absolute; bottom: 8px; left: 8px;
            background: rgba(42,37,32,0.85); color: var(--accent-amber);
            font-size: 12px; padding: 2px 8px; border-radius: var(--radius-pill);
            font-family: 'Inter', sans-serif;
            pointer-events: none;
        }}

        /* --- HERO TEXTURE --- */
        .hero {{ position: relative; }}
        .hero::before {{
            content: "";
            position: absolute; inset: 0;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23noise)' opacity='0.07'/%3E%3C/svg%3E");
            opacity: 0.15; pointer-events: none;
        }}
        .hero > * {{ position: relative; }}

        /* --- TRUST BADGE --- */
        .trust-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(91,123,106,0.1);
            color: var(--accent-sage);
            padding: 4px 12px;
            border-radius: var(--radius-pill);
            font-size: 12px;
            font-weight: 500;
        }}

        /* --- NEWSLETTER CTA --- */
        .newsletter-section {{
            background: var(--bg-surface);
            padding: 56px 24px;
            text-align: center;
        }}
        .newsletter-inner {{
            max-width: 520px;
            margin: 0 auto;
        }}
        .newsletter-section h2 {{
            text-align: center;
            padding-left: 0;
        }}
        .newsletter-section h2::before {{ display: none; }}
        .newsletter-section p {{ color: var(--text-secondary); margin-bottom: 24px; }}
        .newsletter-form {{
            display: flex;
            gap: 12px;
            max-width: 440px;
            margin: 0 auto;
        }}
        .newsletter-form input[type="email"] {{
            flex: 1;
            padding: 10px 16px;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            background: var(--bg-elevated);
        }}
        .newsletter-form .btn-primary {{ white-space: nowrap; }}

        /* --- AUTHOR BOX --- */
        .author-box {{
            display: flex;
            gap: 20px;
            align-items: center;
            padding: 24px 0;
            border-top: 1px solid var(--border);
            border-bottom: 1px solid var(--border);
            margin: 40px 0;
        }}
        .author-avatar {{
            width: 72px;
            height: 72px;
            border-radius: 50%;
            background: url('/images/authors-steffen-elmar.jpg') center/cover;
            flex-shrink: 0;
        }}
        .author-info h4 {{ font-family: 'Fraunces', serif; margin: 0 0 4px; font-size: 16px; padding-left: 0; }}
        .author-info h4::before {{ display: none; }}
        .author-info p {{ font-size: 14px; color: var(--text-secondary); margin: 0; line-height: 1.5; }}

        /* --- ARTICLE 2-COL LAYOUT --- */
        .article-layout {{
            display: grid;
            grid-template-columns: 1fr var(--sidebar-width);
            gap: 48px;
            max-width: var(--max-width);
            margin: 0 auto;
            padding: 0 24px;
        }}
        .article-body {{ max-width: var(--article-max); min-width: 0; }}
        .article-sidebar {{ position: relative; min-width: 0; }}
        .sidebar-sticky {{ position: sticky; top: 88px; }}
        .tasting-panel {{
            background: var(--bg-surface);
            border-radius: var(--radius-sm);
            padding: 24px;
            margin-bottom: 24px;
        }}
        .tasting-panel h3 {{
            font-family: 'Inter', sans-serif;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--accent-amber);
            margin: 0 0 16px;
            padding-left: 0;
        }}
        .tasting-panel h3::before {{ display: none; }}
        .panel-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
            font-size: 14px;
        }}
        .panel-row:last-child {{ border-bottom: none; }}
        .panel-label {{ color: var(--text-secondary); }}
        .panel-value {{ font-weight: 500; color: var(--text-primary); }}

        @media (max-width: 900px) {{
            .article-layout {{ grid-template-columns: 1fr; }}
            .article-sidebar {{ order: -1; }}
        }}

        /* --- TRUST SECTION --- */
        .trust-section {{
            text-align: center;
            padding: 48px 24px;
            border-top: 1px solid var(--border);
            border-bottom: 1px solid var(--border);
        }}
        .trust-stats {{
            display: flex;
            justify-content: center;
            gap: 48px;
            flex-wrap: wrap;
        }}
        .trust-stat-number {{ font-family: 'Fraunces', serif; font-size: 32px; font-weight: 700; color: var(--accent-amber); }}
        .trust-stat-label {{ font-size: 14px; color: var(--text-secondary); margin-top: 4px; }}

        /* --- RESPONSIVE --- */
        @media (max-width: 768px) {{
            .footer-inner {{ grid-template-columns: 1fr; gap: 32px; }}
            .footer-bottom {{ flex-direction: column; gap: 8px; text-align: center; }}
            .site-nav {{ gap: 16px; }}
            .newsletter-form {{ flex-direction: column; }}
            .trust-stats {{ gap: 24px; }}
            /* Homepage grids: 2 columns on tablet */
            .home-cat-grid {{ grid-template-columns: repeat(2, 1fr) !important; }}
        }}
        @media (max-width: 600px) {{
            .hero h1 {{ font-size: 1.8em; }}
            .article-header h1 {{ font-size: 1.5em; }}
            /* Homepage article grid: single column */
            .articles-grid {{ grid-template-columns: 1fr !important; }}
            .featured-card {{
                grid-column: span 1 !important;
                grid-template-columns: 1fr !important;
            }}
            .featured-card-img {{ min-height: 200px !important; }}
            /* Homepage category grid: 2 columns */
            .home-cat-grid {{ grid-template-columns: repeat(2, 1fr) !important; }}
            /* WotM section: less vertical padding on mobile */
            .wotm-section {{ padding: 40px 16px !important; }}
            /* WotM card: single column, less padding */
            .wotm-card {{
                padding: 20px 16px !important;
                grid-template-columns: 1fr !important;
            }}
            .wotm-emoji-col {{ display: none !important; }}
            .article-body {{ padding: 24px; }}
            .nav-toggle {{ display: flex; }}
            .hero-content-inner {{ padding: 0 16px !important; bottom: 32px !important; }}
            .hero-content-inner > p:first-child {{ display: none; }}
            .hero-teaser {{ display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
            .header-inner {{ position: relative; }}
            .site-nav {{
                display: none;
                position: absolute;
                top: 64px;
                left: -24px;
                right: -24px;
                background: var(--bg-elevated);
                border-bottom: 1px solid var(--border);
                box-shadow: var(--shadow-sm);
                flex-direction: column;
                padding: 16px 24px;
                gap: 12px;
                z-index: 99;
            }}
            .site-nav.open {{ display: flex; }}
            .site-nav a {{ margin-left: 0; }}
            .site-nav a.active::after {{ display: none; }}
            .card-image-wrapper, .card-image, .card-image-placeholder {{ height: 160px; }}
            .article-hero-image {{ max-height: 240px; }}
            .related-grid {{ grid-template-columns: 1fr; }}
            .empfehlung-box {{ flex-direction: column; gap: 8px; }}
        }}

        /* --- ACCESSIBILITY --- */
        a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible {{
            outline: 2px solid var(--accent-amber);
            outline-offset: 2px;
        }}
        html {{ scroll-behavior: smooth; }}
        [id] {{ scroll-margin-top: 80px; }}
        .skip-link {{
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            clip-path: inset(50%);
            white-space: nowrap;
            border: 0;
            background: var(--accent-amber);
            color: #fff;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
            z-index: 9999;
            text-decoration: none;
        }}
        .skip-link:focus {{
            position: fixed;
            top: 12px;
            left: 12px;
            width: auto;
            height: auto;
            padding: 10px 20px;
            margin: 0;
            overflow: visible;
            clip: auto;
            clip-path: none;
            white-space: normal;
            border-radius: var(--radius-sm);
            box-shadow: 0 4px 16px rgba(0,0,0,0.2);
        }}

        /* --- CARD FADE-IN ANIMATION --- */
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(18px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .article-card, .card {{
            animation: fadeInUp 0.5s ease both;
        }}
        .article-card:nth-child(2), .card:nth-child(2) {{ animation-delay: 0.08s; }}
        .article-card:nth-child(3), .card:nth-child(3) {{ animation-delay: 0.16s; }}
        .article-card:nth-child(4), .card:nth-child(4) {{ animation-delay: 0.24s; }}
        .article-card:nth-child(5), .card:nth-child(5) {{ animation-delay: 0.32s; }}
        .article-card:nth-child(6), .card:nth-child(6) {{ animation-delay: 0.40s; }}
    </style>
</head>
<body>
    <a href="#main-content" class="skip-link">Zum Inhalt springen</a>
    <header class="site-header">
        <div class="header-inner">
            <a href="/" class="site-logo">whisky<span class="logo-dot">.</span><span class="logo-magazin">Magazin</span></a>
            <button class="nav-toggle" aria-label="Menu" aria-expanded="false">☰</button>
            <nav class="site-nav" role="navigation">
                <a href="/" data-i18n="nav_home">Startseite</a>
                <a href="/kategorie/whisky.html" data-i18n="nav_whisky">Whisky</a>
                <a href="/kategorie/reise.html" data-i18n="nav_travel">Reisen</a>
                <a href="/karte.html" data-i18n="nav_map">Karte</a>
                <a href="/whisky-glossar/" data-i18n="nav_glossar">Glossar</a>
                <a href="/ueber-uns.html" data-i18n="nav_about">Über uns</a>
            </nav>
        </div>
    </header>
    <main id="main-content">
    {content}
    </main>
    <script>
    (function(){{
        var path=location.pathname;
        var links=document.querySelectorAll('.site-nav a');
        links.forEach(function(a){{
            var href=a.getAttribute('href');
            if(path===href||(href!=='/'&&path.indexOf(href)===0)||(href==='/'&&(path==='/'||path==='/index.html')))
                a.classList.add('active');
        }});
    }})();
    (function(){{
        var toggle=document.querySelector('.nav-toggle');
        var nav=document.querySelector('.site-nav');
        if(toggle&&nav){{
            toggle.addEventListener('click',function(){{
                var isOpen=nav.classList.toggle('open');
                toggle.setAttribute('aria-expanded',isOpen);
                toggle.textContent=isOpen?'\u2715':'\u2630';
            }});
        }}
    }})();
    </script>
    <footer class="site-footer">
        <div class="footer-inner">
            <div>
                <div class="footer-logo">whisky<span style="color:var(--accent-amber)">.</span>Magazin</div>
                <p class="footer-tagline">Seit 2007 unterwegs durch Schottlands Whisky-Welt. Echte Reisen, echte Geschichten, ehrliche Empfehlungen.</p>
            </div>
            <div class="footer-nav">
                <h4>Magazin</h4>
                <a href="/">Startseite</a>
                <a href="/kategorie/whisky.html">Whisky</a>
                <a href="/kategorie/reise.html">Reisen</a>
                <a href="/karte.html">Karte</a>
            </div>
            <div class="footer-nav">
                <h4>Mehr</h4>
                <a href="/ueber-uns.html">Über uns</a>
                <a href="/suche.html">Suche</a>
                <a href="/feed.xml" title="RSS Feed abonnieren">RSS Feed</a>
                <a href="/whisky-glossar/">Whisky-Glossar</a>
                <a href="/datenschutz.html">Datenschutz</a>
                <a href="/impressum.html">Impressum</a>
            </div>
        </div>
        <div class="footer-bottom">
            <span>&copy; 2007–2026 Whisky Magazin</span>
            <span class="footer-quote">„Der beste Whisky ist der, den man mit Freunden teilt."</span>
        </div>
    </footer>
<script>
(function(){{
  document.addEventListener('submit',function(e){{
    var form=e.target;
    if(!form.classList.contains('newsletter-form'))return;
    e.preventDefault();
    var btn=form.querySelector('button[type="submit"]');
    var email=form.querySelector('input[type="email"]').value;
    if(!email)return;
    var origText=btn.textContent;
    btn.textContent='Wird gesendet\u2026';btn.disabled=true;
    fetch('/api/subscribe',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email:email}})}})
      .then(function(r){{return r.json()}})
      .then(function(d){{
        if(d.error){{btn.textContent=d.error;setTimeout(function(){{btn.textContent=origText;btn.disabled=false}},3000)}}
        else{{btn.textContent='\u2713 '+(d.message||'Check dein Postfach!');btn.style.background='var(--accent-sage)';form.querySelector('input[type="email"]').value=''}}
      }})
      .catch(function(){{btn.textContent='Fehler \u2013 bitte nochmal';setTimeout(function(){{btn.textContent=origText;btn.disabled=false}},3000)}});
  }});
}})();
</script>
<!-- Globale Sprachleiste (rechter Rand, fixed) -->
<style>
  #site-lang-rail {{ position:fixed; top:50%; right:0; transform:translateY(-50%); z-index:900; background:rgba(255,253,249,0.92); backdrop-filter:blur(8px); border:1px solid var(--border); border-right:none; border-radius:8px 0 0 8px; box-shadow:-2px 2px 12px rgba(42,32,21,0.08); padding:8px 4px; display:flex; flex-direction:column; gap:2px; font-family:'Inter',sans-serif; transition:padding 0.2s; }}
  #site-lang-rail:hover {{ padding:8px 8px; }}
  #site-lang-rail .rail-globe {{ text-align:center; font-size:14px; color:#C8963E; padding:4px 0 6px; border-bottom:1px solid var(--border); margin-bottom:4px; }}
  #site-lang-rail button {{ background:none; border:none; padding:6px 8px; border-radius:4px; font-size:11px; letter-spacing:0.08em; font-weight:600; color:#6B6B6B; cursor:pointer; font-family:'Inter',sans-serif; display:flex; align-items:center; gap:8px; white-space:nowrap; transition:all 0.15s; }}
  #site-lang-rail button:hover {{ background:rgba(200,150,62,0.12); color:#1A1A1A; }}
  #site-lang-rail button.site-lang-active {{ background:#C8963E; color:#FFFFFF; }}
  #site-lang-rail .full {{ display:none; font-weight:500; font-size:11px; text-transform:none; letter-spacing:0; }}
  #site-lang-rail:hover .full {{ display:inline; }}
  #site-lang-rail .code {{ min-width:18px; text-align:center; }}
  @media (max-width: 1023px) {{
    #site-lang-rail {{ top:auto; bottom:24px; right:16px; transform:none; border-radius:28px; padding:6px; border:1px solid var(--border); flex-direction:row; gap:0; backdrop-filter:none; -webkit-backdrop-filter:none; background:rgba(255,253,249,0.98); pointer-events:auto; z-index:9000; }}
    #site-lang-rail.mobile-collapsed button:not(.rail-fab) {{ display:none; }}
    #site-lang-rail .rail-globe {{ display:none; }}
    #site-lang-rail .rail-fab {{ display:inline-flex; width:52px; height:52px; justify-content:center; align-items:center; border-radius:50%; background:#C8963E; color:#fff; font-size:20px; padding:0; touch-action:manipulation; -webkit-tap-highlight-color:transparent; cursor:pointer; pointer-events:auto; }}
    #site-lang-rail:not(.mobile-collapsed) .rail-fab {{ display:none; }}
    #site-lang-rail:not(.mobile-collapsed) {{ flex-direction:row; padding:6px 8px; }}
    #site-lang-rail:not(.mobile-collapsed) .full {{ display:none; }}
    #site-lang-rail button {{ pointer-events:auto; touch-action:manipulation; }}
  }}
  @media (min-width: 1024px) {{
    #site-lang-rail .rail-fab {{ display:none; }}
  }}
</style>
<nav id="site-lang-rail" class="mobile-collapsed" aria-label="Sprache wählen">
  <button type="button" class="rail-fab" aria-label="Sprache wählen">&#127760;</button>
  <span class="rail-globe">&#127760;</span>
  <button type="button" class="site-lang-btn site-lang-active" data-sitelang="de"><span class="code">DE</span><span class="full">Deutsch</span></button>
  <button type="button" class="site-lang-btn" data-sitelang="en"><span class="code">EN</span><span class="full">English</span></button>
  <button type="button" class="site-lang-btn" data-sitelang="fr"><span class="code">FR</span><span class="full">Français</span></button>
  <button type="button" class="site-lang-btn" data-sitelang="nl"><span class="code">NL</span><span class="full">Nederlands</span></button>
  <button type="button" class="site-lang-btn" data-sitelang="es"><span class="code">ES</span><span class="full">Español</span></button>
  <button type="button" class="site-lang-btn" data-sitelang="ja"><span class="code">JA</span><span class="full">&#26085;&#26412;&#35486;</span></button>
</nav>
<script>
(function(){{
  var STORAGE='site_lang';
  var uiCache=null;
  function getLang(){{
    try{{ return localStorage.getItem(STORAGE)||'de'; }}catch(e){{ return 'de'; }}
  }}
  function setLang(l){{ try{{ localStorage.setItem(STORAGE,l); }}catch(e){{}} }}
  function loadUi(cb){{
    if(uiCache){{cb(uiCache);return;}}
    fetch('/data/translations.json').then(function(r){{return r.json();}}).then(function(d){{uiCache=d;cb(d);}}).catch(function(){{cb({{}});}});
  }}
  function applyUi(lang){{
    loadUi(function(ui){{
      var dict=ui[lang]||{{}};
      document.querySelectorAll('[data-i18n]').forEach(function(el){{
        var key=el.getAttribute('data-i18n');
        if(dict[key]) el.textContent=dict[key];
      }});
      document.documentElement.setAttribute('lang',lang);
    }});
  }}
  function updateRail(lang){{
    document.querySelectorAll('.site-lang-btn').forEach(function(b){{
      if(b.dataset.sitelang===lang) b.classList.add('site-lang-active'); else b.classList.remove('site-lang-active');
    }});
  }}
  function rewriteArticleLinks(lang){{
    if(lang==='de') return;
    document.querySelectorAll('a[href*="/artikel/"]').forEach(function(a){{
      try{{
        var u=new URL(a.getAttribute('href'), location.origin);
        if(u.pathname.indexOf('/artikel/')!==0 && u.pathname.indexOf('/artikel/')===-1) return;
        u.searchParams.set('lang',lang);
        a.setAttribute('href', u.pathname+u.search+u.hash);
      }}catch(e){{}}
    }});
  }}
  function pickLang(lang){{
    setLang(lang);
    updateRail(lang);
    if(typeof window.switchArticleLang==='function'){{
      window.switchArticleLang(lang);
    }}else{{
      applyUi(lang);
      rewriteArticleLinks(lang);
    }}
    var notice=document.getElementById('site-lang-notice');
    if(notice){{
      if(lang==='de'){{ notice.style.display='none'; }}
      else{{ notice.style.display=''; }}
    }}
    var rail=document.getElementById('site-lang-rail');
    if(rail){{ rail.classList.add('mobile-collapsed'); }}
  }}
  document.querySelectorAll('.site-lang-btn').forEach(function(b){{
    b.addEventListener('click',function(){{ pickLang(b.dataset.sitelang); }});
  }});
  var fab=document.querySelector('.rail-fab');
  if(fab){{
    var fabTouched=false;
    fab.addEventListener('touchend',function(e){{
      e.preventDefault();
      fabTouched=true;
      document.getElementById('site-lang-rail').classList.toggle('mobile-collapsed');
      setTimeout(function(){{fabTouched=false;}},600);
    }});
    fab.addEventListener('click',function(e){{
      e.stopPropagation();
      if(!fabTouched){{
        document.getElementById('site-lang-rail').classList.toggle('mobile-collapsed');
      }}
    }});
  }}
  function closeRailIfOutside(e){{
    var rail=document.getElementById('site-lang-rail');
    if(rail&&!rail.contains(e.target)){{ rail.classList.add('mobile-collapsed'); }}
  }}
  document.addEventListener('touchstart',closeRailIfOutside,{{passive:true}});
  document.addEventListener('click',closeRailIfOutside);
  var initial=getLang();
  updateRail(initial);
  if(initial!=='de'){{
    applyUi(initial);
    rewriteArticleLinks(initial);
    var notice=document.getElementById('site-lang-notice');
    if(notice) notice.style.display='';
  }}
  window.__siteLang={{get:getLang,set:setLang,applyUi:applyUi}};
}})();
</script>
<!-- Cookie Consent Banner -->
<div id="cookie-banner" style="display:none;position:fixed;bottom:0;left:0;right:0;z-index:19999;background:var(--text-primary);color:#fff;box-shadow:0 -4px 24px rgba(0,0,0,0.25);">
  <div style="max-width:960px;margin:0 auto;padding:20px 24px;display:flex;flex-wrap:wrap;align-items:center;gap:16px;">
    <div style="flex:1;min-width:280px;">
      <p style="margin:0 0 4px;font-size:15px;font-weight:600;font-family:'Fraunces',serif;">Cookie-Einstellungen</p>
      <p style="margin:0;font-size:13px;color:rgba(255,255,255,0.7);line-height:1.5;">Wir nutzen Cookies für Affiliate-Partner (Amazon, Booking.com) und Google Fonts. Details in unserer <a href="/datenschutz.html" style="color:var(--accent-amber);text-decoration:underline;">Datenschutzerklärung</a>.</p>
    </div>
    <div style="display:flex;gap:8px;flex-shrink:0;">
      <button onclick="cookieConsent('essential')" style="padding:10px 20px;border:1px solid rgba(255,255,255,0.3);background:transparent;color:#fff;border-radius:var(--radius-sm);cursor:pointer;font-size:13px;font-family:'Inter',sans-serif;">Nur notwendige</button>
      <button onclick="cookieConsent('all')" style="padding:10px 20px;border:none;background:var(--accent-amber);color:#fff;border-radius:var(--radius-sm);cursor:pointer;font-size:13px;font-weight:600;font-family:'Inter',sans-serif;">Alle akzeptieren</button>
    </div>
  </div>
</div>
<script>
(function(){{
  var consent=localStorage.getItem('cookie_consent');
  if(!consent){{document.getElementById('cookie-banner').style.display='block'}}
  window.cookieConsent=function(level){{
    localStorage.setItem('cookie_consent',level);
    localStorage.setItem('cookie_consent_date',new Date().toISOString());
    document.getElementById('cookie-banner').style.display='none';
  }};
}})();
</script>
</body>
</html>"""


# ============================================================
# Seiten generieren
# ============================================================

def load_all_articles():
    """Lädt alle gespeicherten Artikel aus dem articles-Ordner."""
    ARTICLES_DIR.mkdir(exist_ok=True)
    articles = []
    for json_file in sorted(ARTICLES_DIR.glob("*.json"), reverse=True):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                article = json.load(f)
            # Normalisierung: meta.slug aus Top-Level slug ableiten falls fehlend
            if not article.get("meta", {}).get("slug"):
                top_slug = article.get("slug", "")
                if top_slug:
                    article.setdefault("meta", {})["slug"] = top_slug
            articles.append(article)
        except Exception as e:
            print(f"  Warnung: Konnte {json_file.name} nicht laden: {e}")
    return articles


def _find_related_articles(current_article, all_articles, base_url, max_count=3):
    """Findet verwandte Artikel basierend auf Kategorie- und Tag-Übereinstimmung."""
    current_slug = current_article.get("meta", {}).get("slug", "")
    current_cats = set()
    if current_article.get("categories"):
        current_cats = set(c.lower() for c in current_article["categories"])
    elif current_article.get("category"):
        current_cats = {current_article["category"].lower()}
    current_tags = set(t.lower() for t in current_article.get("tags", []))

    scored = []
    for a in all_articles:
        slug = a.get("meta", {}).get("slug", "")
        if not slug or slug == current_slug:
            continue
        # Punkte für überlappende Kategorien
        a_cats = set()
        if a.get("categories"):
            a_cats = set(c.lower() for c in a["categories"])
        elif a.get("category"):
            a_cats = {a["category"].lower()}
        cat_score = len(current_cats & a_cats) * 2
        # Punkte für überlappende Tags
        a_tags = set(t.lower() for t in a.get("tags", []))
        tag_score = len(current_tags & a_tags)
        total = cat_score + tag_score
        if total > 0:
            scored.append((total, a))

    # Nach Score sortieren (höchster zuerst), bei Gleichstand nach Datum
    scored.sort(key=lambda x: (x[0], x[1].get("date", "")), reverse=True)

    items = []
    for _, a in scored[:max_count]:
        slug = a.get("meta", {}).get("slug", "")
        title = a["title"]
        cat = a.get("category", "Allgemein")
        img_url = a.get("image_url", "")
        img_bg = f"background-image:url({img_url});background-size:cover;background-position:center;" if img_url else "background:linear-gradient(135deg, var(--bg-surface) 0%, var(--border) 100%);"
        items.append(
            f'<div class="card">'
            f'<div class="card-image" style="{img_bg}height:160px;"></div>'
            f'<div class="card-body">'
            f'<span class="badge badge-outline">{cat}</span>'
            f'<h3 class="card-title"><a href="{base_url}/artikel/{slug}.html">{title}</a></h3>'
            f'</div></div>'
        )

    # Falls weniger als max_count gefunden, mit neuesten Artikeln auffüllen
    used_slugs = {current_slug} | {a.get("meta", {}).get("slug", "") for _, a in scored[:max_count]}
    if len(items) < max_count:
        for a in all_articles:
            slug = a.get("meta", {}).get("slug", "")
            if slug and slug not in used_slugs:
                title = a["title"]
                cat = a.get("category", "Allgemein")
                img_url = a.get("image_url", "")
                img_bg = f"background-image:url({img_url});background-size:cover;background-position:center;" if img_url else "background:linear-gradient(135deg, var(--bg-surface) 0%, var(--border) 100%);"
                items.append(
                    f'<div class="card">'
                    f'<div class="card-image" style="{img_bg}height:160px;"></div>'
                    f'<div class="card-body">'
                    f'<span class="badge badge-outline">{cat}</span>'
                    f'<h3 class="card-title"><a href="{base_url}/artikel/{slug}.html">{title}</a></h3>'
                    f'</div></div>'
                )
                used_slugs.add(slug)
                if len(items) >= max_count:
                    break

    if items:
        grid = '\n'.join(items)
        return grid
    return ""


def _replace_related_box(html_content, related_html):
    """Ersetzt die GPT-generierte related-box durch echte verlinkte Artikel."""
    # Entferne die bestehende related-box (verschiedene Formate)
    pattern = r'<div class=["\']related-box["\']>.*?</div>'
    cleaned = re.sub(pattern, '', html_content, flags=re.DOTALL)
    # Füge die neue related-box vor dem Ende ein
    if related_html:
        cleaned = cleaned.rstrip() + "\n\n" + related_html
    return cleaned


def _reading_time(html_content):
    """Schätzt die Lesezeit in Minuten aus HTML-Content."""
    text = re.sub(r'<[^>]+>', '', html_content)
    word_count = len(text.split())
    return max(1, round(word_count / 200))


def _inject_empfehlung_boxes(html_content, article, config):
    """Fügt nach dem 2. </h2> eine kategorie-spezifische Empfehlung-Box ein."""
    amazon_tag = config.get('affiliate_links', {}).get('amazon_tag', 'whiskyreise74-21')
    travel = config.get('affiliate_links', {}).get('travel_links', {})
    category = article.get('category', '').lower()
    categories = [c.lower() for c in article.get('categories', [])]

    if category in ('reise', 'urlaub') or 'reise' in categories or 'urlaub' in categories:
        faehre = travel.get('faehre', 'https://www.whisky.reise/reise')
        hotel = travel.get('hotel', 'https://www.whisky.reise/hotels')
        box = (
            '<div class="empfehlung-box">'
            '<h3 style="padding-left:0;">🏴󠁧󠁢󠁳󠁣󠁴󠁿 Reise planen</h3>'
            '<p>Fähre, Hotel und mehr für deine Schottland-Reise – alles auf einen Blick.</p>'
            f'<a href="{faehre}" class="btn btn-primary" style="margin-top:12px;margin-right:8px;" target="_blank" rel="nofollow noopener">Fähre buchen</a>'
            f'<a href="{hotel}" class="btn btn-primary" style="margin-top:12px;" target="_blank" rel="nofollow noopener">Hotels ansehen</a>'
            '</div>'
        )
    else:
        # Artikelspezifisches Keyword aus Titel + Tags
        tags = article.get('tags', [])
        title = article.get('title', '')
        # Generische Tags die NICHT als Produkt-Keyword taugen
        GENERIC_TAGS = {'tasting', 'single malt', 'whisky', 'scotch', 'reise', 'schottland',
                        'guide', 'listicle', 'einsteiger', 'tipps', 'review', 'artikel',
                        'lifestyle', 'natur', 'urlaub', 'highlands', 'islay', 'speyside'}
        # Bevorzuge spezifische Destillerie-/Produkt-Tags
        specific_tags = [t for t in tags if t.lower() not in GENERIC_TAGS]
        # Wenn spezifisches Tag vorhanden: verwende es als Kern-Keyword
        if specific_tags:
            primary = specific_tags[0]
        else:
            # Fallback: aus Titel das wichtigste Wort extrahieren
            title_words = [w for w in title.split() if len(w) > 4 and w[0].isupper()]
            primary = title_words[0] if title_words else 'Scotch+Whisky'
        keyword = primary.lower().replace(' ', '+')
        # Sekundärer Link: Zweites spezifisches Tag (wenn vorhanden)
        secondary_keyword = specific_tags[1].lower().replace(' ', '+') if len(specific_tags) > 1 else None
        secondary_btn = (
            f' <a href="https://www.amazon.de/s?k={secondary_keyword}&tag={amazon_tag}" '
            f'class="btn btn-secondary" style="margin-top:12px;" target="_blank" rel="nofollow noopener">'
            f'{specific_tags[1]} ansehen</a>'
        ) if secondary_keyword else ''
        box = (
            '<div class="empfehlung-box">'
            f'<span class="emp-icon">🥃</span>'
            '<div class="emp-content">'
            f'<p class="emp-title">{primary} bei Amazon</p>'
            f'<p class="emp-text">Den im Artikel besprochenen Whisky direkt bestellen – oft mit Prime-Lieferung.</p>'
            f'<a href="https://www.amazon.de/s?k={keyword}+whisky+single+malt&tag={amazon_tag}" '
            f'class="emp-cta" target="_blank" rel="nofollow noopener">{primary} bei Amazon ansehen</a>'
            f'{secondary_btn}'
            '</div>'
            '</div>'
        )

    # Nach dem 2. </h2> einfügen
    count = [0]
    def insert_after_second_h2(m):
        count[0] += 1
        if count[0] == 2:
            return m.group(0) + box
        return m.group(0)

    result = re.sub(r'</h2>', insert_after_second_h2, html_content)
    # Falls weniger als 2 h2 vorhanden, nach dem 1. einfügen
    if count[0] < 2:
        count[0] = 0
        result = re.sub(r'</h2>', insert_after_second_h2, html_content)
    return result


def _has_map_locations(article):
    """Prüft ob ein Artikel Karten-Locations hat (explizit oder per Reisebericht-Typ)."""
    if article.get("locations"):
        return True
    if article.get("type") == "reisebericht":
        return True
    # Tag-basiert: Artikel mit Orts-/Destillerie-Tags
    geo_tags = {'islay', 'glasgow', 'edinburgh', 'speyside', 'highlands', 'skye',
                'orkney', 'campbeltown', 'arran', 'kentucky', 'dublin', 'oban',
                'lagavulin', 'ardbeg', 'laphroaig', 'talisker', 'springbank'}
    article_tags = {t.lower() for t in article.get("tags", [])}
    return bool(article_tags & geo_tags)


def _build_mini_map_html(article, base_url):
    """Erzeugt Mini-Map HTML für Artikel mit Ortsbezug."""
    slug = article.get("meta", {}).get("slug", "")

    return f"""
    <div class="article-mini-map" style="margin: 20px 0;">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <span style="font-size:1.2em;">📍</span>
            <a href="{base_url}/karte.html?highlight={slug}"
               style="color:var(--accent-amber); text-decoration:none; font-size:0.9em;
                      font-family:'Inter',sans-serif;">
                Auf der Karte anzeigen &rarr;
            </a>
        </div>
        <div id="mini-map" style="height:220px; border-radius:10px; box-shadow:var(--shadow-sm);"></div>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script>
        (function() {{
            var localBase = window.location.origin;
            fetch(localBase + '/data/map-data.json')
                .then(r => r.json())
                .then(data => {{
                    var locs = data.locations.filter(function(l) {{
                        return l.articles && l.articles.indexOf('{slug}') !== -1;
                    }});
                    if (locs.length === 0) return;
                    var m = L.map('mini-map', {{ scrollWheelZoom: false, zoomControl: true }});
                    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                        attribution: '&copy; OSM', maxZoom: 16
                    }}).addTo(m);
                    var bounds = [];
                    locs.forEach(function(loc) {{
                        var icon = loc.type === 'distillery'
                            ? L.divIcon({{ className:'', html:'<div style="font-size:20px">🥃</div>', iconSize:[24,24], iconAnchor:[12,12] }})
                            : L.divIcon({{ className:'', html:'<div style="font-size:18px">📍</div>', iconSize:[24,24], iconAnchor:[12,12] }});
                        L.marker([loc.lat, loc.lon], {{ icon: icon }})
                            .bindTooltip(loc.name, {{ permanent: locs.length <= 5 }})
                            .addTo(m);
                        bounds.push([loc.lat, loc.lon]);
                    }});
                    if (bounds.length === 1) {{
                        m.setView(bounds[0], 10);
                    }} else {{
                        m.fitBounds(bounds, {{ padding: [30, 30] }});
                    }}
                }});
        }})();
        </script>
    </div>"""


def _build_tasting_panel(article):
    """Build sidebar tasting panel for whisky articles."""
    if article.get('category', '').lower() != 'whisky':
        return ''

    # Try to extract region from tags
    regions = ['Islay', 'Speyside', 'Highlands', 'Highland', 'Lowlands', 'Campbeltown', 'Islands', 'Skye']
    found_region = 'Schottland'
    for tag in article.get('tags', []):
        for region in regions:
            if region.lower() in tag.lower():
                found_region = tag
                break

    return f'''
    <div class="tasting-panel">
        <h3>Auf einen Blick</h3>
        <div class="panel-row">
            <span class="panel-label">Region</span>
            <span class="panel-value">{found_region}</span>
        </div>
        <div class="panel-row">
            <span class="panel-label">Kategorie</span>
            <span class="panel-value">Single Malt</span>
        </div>
        <div class="panel-row">
            <span class="panel-label">Erfahrung</span>
            <span class="panel-value">Persönlich besucht</span>
        </div>
        <a href="https://www.amazon.de/s?k=Scotch+Whisky+{found_region}&tag=whiskyreise74-21" class="btn btn-primary" style="width:100%;text-align:center;margin-top:16px;" target="_blank" rel="nofollow noopener">Whiskys entdecken</a>
    </div>
    '''


def build_article_page(article, config, all_articles=None):
    """Erstellt die HTML-Seite für einen einzelnen Artikel."""
    from urllib.parse import quote
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    meta = article.get("meta", {})
    slug = meta.get("slug", "")
    date_display = _german_date(article.get("date", ""))
    category = article.get('category', 'Allgemein')
    cat_lower = category.lower()
    reading_time = _reading_time(article['html_content'])

    # Tags als badge-outline
    tags_html = ""
    if article.get("tags"):
        tag_badges = " ".join(
            f'<span class="badge badge-outline">{tag}</span>' for tag in article["tags"]
        )
        tags_html = f'<div style="margin:32px 0;">{tag_badges}</div>'

    # Sidebar mit neuesten Artikeln (kept for data, used in sidebar CTA)
    if all_articles is None:
        all_articles = load_all_articles()

    # Related-Box + Empfehlung-Box
    related_html = _find_related_articles(article, all_articles, base_url, max_count=3)
    article_html = _replace_related_box(article['html_content'], "")
    article_html = _inject_empfehlung_boxes(article_html, article, config)

    # Amazon-Links auf ASINs umstellen + Produktboxen einfügen
    amazon_tag = config.get("affiliate_links", {}).get("amazon_tag", "whiskyreise74-21")
    article_html = _enhance_amazon_links(article_html, amazon_tag)
    article_html = _inject_product_boxes(article_html, amazon_tag)

    # Hero-Bild
    hero_img_html = ""
    if article.get("image_url"):
        img_alt = article.get("image_alt", article["title"])
        hero_img_html = f'<img src="{article["image_url"]}" alt="{img_alt}" style="width:100%;aspect-ratio:16/9;object-fit:cover;border-radius:var(--radius-sm);display:block;" loading="lazy">'
        if article.get("image_credit"):
            hero_img_html += f'<div class="article-image-credit">{article["image_credit"]}</div>'

    # OG-Image
    og_image = article.get("image_url", f"{base_url}/images/default.jpg")

    # Trust badge (only if personal photos or map locations)
    trust_badge_html = ""
    is_personal = article.get("image_source") == "personal_cartoon"
    has_locations = _has_map_locations(article)
    if is_personal or has_locations:
        trust_badge_html = '<div style="margin-top:12px;"><span class="trust-badge">&#10003; Persönlich besucht</span></div>'

    # Share-Buttons
    article_url = f"{base_url}/artikel/{slug}.html"
    share_title = quote(article["title"])
    share_url = quote(article_url)
    whatsapp_url = f"https://wa.me/?text={share_title}%20{share_url}"
    twitter_url = f"https://x.com/intent/tweet?text={share_title}&url={share_url}"
    pinterest_url = f"https://pinterest.com/pin/create/button/?url={share_url}&description={share_title}"
    email_url = f"mailto:?subject={share_title}&body={share_url}"
    share_html = f'''<div style="display:flex;gap:8px;margin:32px 0;flex-wrap:wrap;">
        <a href="{whatsapp_url}" class="btn btn-ghost" style="font-size:12px;padding:6px 14px;" target="_blank">WhatsApp</a>
        <a href="{twitter_url}" class="btn btn-ghost" style="font-size:12px;padding:6px 14px;" target="_blank">Twitter</a>
        <a href="{pinterest_url}" class="btn btn-ghost" style="font-size:12px;padding:6px 14px;" target="_blank">Pinterest</a>
        <a href="{email_url}" class="btn btn-ghost" style="font-size:12px;padding:6px 14px;">E-Mail</a>
    </div>'''

    # Sidebar CTAs (Reise-Artikel bekommen Reise-CTAs zuerst)
    amazon_tag = config.get('affiliate_links', {}).get('amazon_tag', 'whiskyreise74-21')
    travel = config.get('affiliate_links', {}).get('travel_links', {})
    faehre_url = travel.get('faehre', '#')
    is_travel = cat_lower in ('reise', 'urlaub')

    if is_travel:
        sidebar_cta_html = f"""<div class="cta-box">
                    <h3>Schottland-Reise planen</h3>
                    <p>Fähren, Flüge & Hotels auf einen Blick</p>
                    <a href="{faehre_url}" target="_blank" rel="nofollow noopener">Fähre buchen &#8594;</a>
                </div>
                <div class="cta-box" style="margin-top: 20px;">
                    <h3>Whisky entdecken</h3>
                    <p>Die besten Single Malts bei Amazon</p>
                    <a href="https://www.amazon.de/s?k=single+malt+whisky&tag={amazon_tag}" target="_blank" rel="nofollow noopener">Whisky shoppen &#8594;</a>
                </div>"""
    else:
        sidebar_cta_html = f"""<div class="cta-box">
                    <h3>Whisky entdecken</h3>
                    <p>Finde deinen nächsten Lieblings-Dram</p>
                    <a href="https://www.amazon.de/s?k=single+malt+whisky&tag={amazon_tag}" target="_blank" rel="nofollow noopener">Whisky bei Amazon &#8594;</a>
                </div>
                <div class="cta-box" style="margin-top: 20px;">
                    <h3>Schottland-Reise planen</h3>
                    <p>Fähren, Flüge & Hotels</p>
                    <a href="{faehre_url}" target="_blank" rel="nofollow noopener">Fähre buchen &#8594;</a>
                </div>"""

    # Mini-Map für Artikel mit Ortsbezug
    mini_map_html = ""
    if has_locations:
        mini_map_html = _build_mini_map_html(article, base_url)

    # Tasting panel (only for Whisky category)
    tasting_panel_html = _build_tasting_panel(article)

    # Mid-article newsletter CTA
    mid_newsletter_html = '''<div style="background:var(--bg-surface);border-radius:var(--radius-sm);padding:32px;text-align:center;margin:40px 0;">
        <p style="font-size:28px;margin:0 0 8px;">🥃</p>
        <h3 style="font-family:'Fraunces',serif;font-size:20px;margin:0 0 8px;padding-left:0;">Kostenloser Whisky-Guide</h3>
        <p style="font-size:14px;color:var(--text-secondary);margin:0 0 16px;">Melde dich an und erhalte unseren Einsteiger-Guide mit Tasting-Tipps, Empfehlungen und Reise-Insiderwissen.</p>
        <form class="newsletter-form" style="justify-content:center;">
            <input type="email" placeholder="Deine E-Mail" required>
            <button type="submit" class="btn btn-primary">Guide sichern</button>
        </form>
    </div>'''

    # Title truncation for breadcrumb
    title_breadcrumb = article['title'][:50] + '...' if len(article['title']) > 50 else article['title']

    # Related articles section
    related_section_html = ""
    if related_html:
        related_section_html = f'''<div style="margin-top:48px;">
            <h2 style="text-align:center;padding-left:0;">Weiterlesen</h2>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-top:24px;">
                {related_html}
            </div>
        </div>'''

    content = f"""
    <nav style="max-width:var(--max-width);margin:0 auto;padding:16px 24px;font-size:13px;color:var(--text-secondary);">
        <a href="/" style="color:var(--accent-amber);text-decoration:none;">Startseite</a>
        <span style="margin:0 8px;">&#8250;</span>
        <a href="/kategorie/{cat_lower}.html" style="color:var(--accent-amber);text-decoration:none;">{category}</a>
        <span style="margin:0 8px;">&#8250;</span>
        <span>{title_breadcrumb}</span>
    </nav>
    <div style="max-width:var(--article-max);margin:0 auto;padding:16px 24px 24px;text-align:center;">
        <span class="badge badge-amber">{category}</span>
        <h1 id="article-title" style="font-size:34px;margin:16px 0 12px;padding-left:0;">{article['title']}</h1>
        <p style="color:var(--text-secondary);font-size:14px;">Von Steffen &amp; Elmar &#183; {date_display} &#183; {reading_time} Min. Lesezeit</p>
        {trust_badge_html}
    </div>
    <div style="max-width:var(--max-width);margin:0 auto;padding:0 24px;">
        {hero_img_html}
    </div>
    <div id="lang-switcher" style="max-width:var(--max-width);margin:18px auto 0;padding:0 24px;display:flex;align-items:center;justify-content:flex-end;gap:6px;font-family:'Inter',sans-serif;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;">
        <span style="margin-right:4px;font-size:14px;">&#127760;</span>
        <button class="lang-btn lang-active" data-lang="de" style="background:#C8963E;border:none;padding:3px 8px;border-radius:3px;font:inherit;letter-spacing:inherit;text-transform:inherit;cursor:pointer;color:#FFFFFF;font-weight:700;transition:all 0.15s;">DE</button>
        <button class="lang-btn" data-lang="en" style="background:none;border:none;padding:3px 8px;border-radius:3px;font:inherit;letter-spacing:inherit;text-transform:inherit;cursor:pointer;color:#6B6B6B;font-weight:500;transition:all 0.15s;">EN</button>
        <button class="lang-btn" data-lang="fr" style="background:none;border:none;padding:3px 8px;border-radius:3px;font:inherit;letter-spacing:inherit;text-transform:inherit;cursor:pointer;color:#6B6B6B;font-weight:500;transition:all 0.15s;">FR</button>
        <button class="lang-btn" data-lang="nl" style="background:none;border:none;padding:3px 8px;border-radius:3px;font:inherit;letter-spacing:inherit;text-transform:inherit;cursor:pointer;color:#6B6B6B;font-weight:500;transition:all 0.15s;">NL</button>
        <button class="lang-btn" data-lang="es" style="background:none;border:none;padding:3px 8px;border-radius:3px;font:inherit;letter-spacing:inherit;text-transform:inherit;cursor:pointer;color:#6B6B6B;font-weight:500;transition:all 0.15s;">ES</button>
        <button class="lang-btn" data-lang="ja" style="background:none;border:none;padding:3px 8px;border-radius:3px;font:inherit;letter-spacing:inherit;text-transform:inherit;cursor:pointer;color:#6B6B6B;font-weight:500;transition:all 0.15s;">JA</button>
    </div>
    <div id="lang-notice" style="max-width:var(--max-width);margin:2px auto 0;padding:0 24px;font-size:12px;color:#1A1A1A;text-align:right;display:none;font-family:'Inter',sans-serif;font-weight:500;"></div>
    <div class="article-layout">
        <article class="article-body" data-slug="{slug}">
            {article_html}

            {mini_map_html}

            {mid_newsletter_html}

            {share_html}

            {tags_html}

            <div style="border-left:3px solid var(--accent-sage);background:rgba(91,123,106,0.05);padding:16px 20px;border-radius:0 var(--radius-sm) var(--radius-sm) 0;margin:32px 0;font-size:13px;color:var(--text-secondary);">
                <strong style="color:var(--accent-sage);">Hinweis:</strong> Dieser Artikel enthält Affiliate-Links. Wenn du über diese Links einkaufst, erhalten wir eine kleine Provision — für dich ändert sich nichts am Preis.
            </div>

            <div class="author-box">
                <div class="author-avatar"></div>
                <div class="author-info">
                    <h4>Steffen &amp; Elmar</h4>
                    <p>Seit 2007 reisen wir durch Schottland und besuchen Destillerien. Was als Hobby begann, ist heute unsere Leidenschaft: echte Geschichten von echten Orten.</p>
                </div>
            </div>

            {related_section_html}
        </article>
        <aside class="article-sidebar">
            <div class="sidebar-sticky">
                {tasting_panel_html}
                <div style="background:var(--bg-surface);border-radius:var(--radius-sm);padding:24px;margin-bottom:24px;text-align:center;">
                    <h4 style="font-family:'Fraunces',serif;font-size:16px;margin:0 0 8px;padding-left:0;">Schottland-Post</h4>
                    <p style="font-size:13px;color:var(--text-secondary);margin:0 0 16px;">Einmal im Monat die besten Stories.</p>
                    <form class="newsletter-form" style="display:flex;flex-direction:column;gap:8px;">
                        <input type="email" placeholder="E-Mail" style="padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:13px;font-family:'Inter',sans-serif;" required>
                        <button type="submit" class="btn btn-primary" style="font-size:13px;padding:8px 16px;">Anmelden</button>
                    </form>
                </div>
                {sidebar_cta_html}
            </div>
        </aside>
    </div>
    <script>
    (function(){{
      var article=document.querySelector('article[data-slug]');
      if(!article)return;
      var slug=article.dataset.slug;
      var uiCache=null;
      var currentLang='de';
      var TTL=86400000;
      function cacheKey(l){{return'tr_'+slug+'_'+l;}}
      function fromCache(l){{try{{var r=localStorage.getItem(cacheKey(l));if(!r)return null;var o=JSON.parse(r);if(Date.now()-o.ts>TTL){{localStorage.removeItem(cacheKey(l));return null;}}return o.d;}}catch(e){{return null;}}}}
      function toCache(l,d){{try{{localStorage.setItem(cacheKey(l),JSON.stringify({{ts:Date.now(),d:d}}));}}catch(e){{}}}}
      function loadUi(cb){{if(uiCache){{cb(uiCache);return;}}fetch('/data/translations.json').then(function(r){{return r.json();}}).then(function(d){{uiCache=d;cb(d);}}).catch(function(){{cb({{}})}});}}
      var langNames={{en:'English',fr:'Français',nl:'Nederlands',es:'Español',ja:'日本語'}};
      function applyTranslation(lang,data){{
        var h1=document.getElementById('article-title');
        if(data.title&&h1)h1.textContent=data.title;
        if(data.html_content)article.innerHTML=data.html_content;
        var notice=document.getElementById('lang-notice');
        if(notice){{
          if(lang==='de'){{notice.style.display='none';notice.textContent='';}}
          else{{
            notice.textContent=langNames[lang]||lang.toUpperCase();
            notice.style.display='';
          }}
        }}
        var url=new URL(location.href);
        if(lang==='de'){{url.searchParams.delete('lang');}}else{{url.searchParams.set('lang',lang);}}
        history.pushState(null,'',url.toString());
        document.querySelectorAll('.lang-btn').forEach(function(b){{
          var active=b.dataset.lang===lang;
          b.style.color=active?'#FFFFFF':'#6B6B6B';
          b.style.background=active?'#C8963E':'none';
          b.style.fontWeight=active?'700':'500';
        }});
        currentLang=lang;
      }}
      function switchLang(lang){{
        try{{ localStorage.setItem('site_lang',lang); }}catch(e){{}}
        document.querySelectorAll('.site-lang-btn').forEach(function(b){{
          if(b.dataset.sitelang===lang)b.classList.add('site-lang-active');else b.classList.remove('site-lang-active');
        }});
        if(lang===currentLang)return;
        if(lang==='de'){{
          var url=new URL(location.href);url.searchParams.delete('lang');
          history.pushState(null,'',url.toString());
          location.reload();return;
        }}
        var cached=fromCache(lang);
        if(cached){{applyTranslation(lang,cached);return;}}
        var btn=document.querySelector('.lang-btn[data-lang="'+lang+'"]');
        var orig=btn?btn.textContent:lang.toUpperCase();
        if(btn){{btn.textContent='\u2026';btn.disabled=true;}}
        fetch('/api/translate?slug='+encodeURIComponent(slug)+'&lang='+lang)
          .then(function(r){{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}})
          .then(function(d){{toCache(lang,d);applyTranslation(lang,d);}})
          .catch(function(){{
            loadUi(function(ui){{
              var notice=document.getElementById('lang-notice');
              if(notice){{notice.textContent=(ui[lang]&&ui[lang].lang_error)||'Translation unavailable.';notice.style.display='';}}
            }});
          }})
          .finally(function(){{if(btn){{btn.textContent=orig;btn.disabled=false;}}}});
      }}
      document.querySelectorAll('.lang-btn').forEach(function(b){{
        b.addEventListener('click',function(){{switchLang(b.dataset.lang);}});
      }});
      window.switchArticleLang=switchLang;
      var urlLang=new URLSearchParams(location.search).get('lang');
      var storedLang=null;try{{storedLang=localStorage.getItem('site_lang');}}catch(e){{}}
      var initLang=urlLang||storedLang;
      if(initLang&&initLang!=='de'){{switchLang(initLang);}}
    }})();
    </script>"""

    article_ld = _json_ld_article(article, base_url)
    breadcrumb_ld = _json_ld_breadcrumb([
        ("Startseite", "/"),
        (category, f"/kategorie/{cat_lower}.html"),
        (article["title"], f"/artikel/{slug}.html"),
    ], base_url)
    return _base_template().format(
        title=article["title"],
        site_name=site_name,
        meta_description=meta.get("meta_description", article["title"]),
        keywords=meta.get("keywords", ""),
        og_description=meta.get("og_description", meta.get("meta_description", "")),
        og_image=og_image,
        canonical_url=f"{base_url}/artikel/{slug}.html",
        base_url=base_url,
        content=content,
        json_ld=article_ld + "\n    " + breadcrumb_ld,
    )


def build_index_page(articles, config):
    """Erstellt die Startseite mit Artikelübersicht."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    tagline = config["site"]["tagline"]

    cat_emoji = {"Whisky": "🥃", "Reise": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Lifestyle": "✨", "Natur": "🌿", "Urlaub": "🌄"}

    # Collect categories + tags (needed for region cards)
    categories = {}
    all_tags = set()
    for a in articles:
        cat = a.get("category", "Allgemein")
        categories[cat] = categories.get(cat, 0) + 1
        for tag in a.get("tags", []):
            all_tags.add(tag)

    # --- 1. Hero: Featured Article Overlay (neuester Artikel) ---
    hero_article = articles[0] if articles else None
    hero_html = ""
    if hero_article:
        h_meta  = hero_article.get("meta", {})
        h_slug  = h_meta.get("slug", "")
        h_teaser = h_meta.get("teaser", h_meta.get("meta_description", ""))[:180]
        h_cat   = hero_article.get("category", "Whisky")
        h_date  = _german_date(hero_article.get("date", ""))
        h_rt    = _reading_time(hero_article.get("html_content", "")) if hero_article.get("html_content") else 5
        h_img   = hero_article.get("image_url", "")
        h_bg    = f"url({h_img})" if h_img else "linear-gradient(135deg,#2A2015 0%,#4A3828 100%)"
        hero_html = f"""
    <style>
    @keyframes bounce-arrow {{
        0%, 100% {{ transform: translateY(0); opacity:0.7; }}
        50% {{ transform: translateY(8px); opacity:1; }}
    }}
    .hero-scroll-arrow {{
        position:absolute; bottom:20px; left:50%; transform:translateX(-50%);
        display:flex; flex-direction:column; align-items:center; gap:4px;
        cursor:pointer; animation: bounce-arrow 1.8s ease-in-out infinite;
        text-decoration:none;
    }}
    .hero-scroll-arrow svg {{ width:28px; height:28px; fill:none; stroke:rgba(255,255,255,0.75); stroke-width:2.5; }}
    .hero-scroll-arrow span {{ font-size:11px; color:rgba(255,255,255,0.6); font-family:'Inter',sans-serif; letter-spacing:1.5px; text-transform:uppercase; }}
    .hero-label-bar {{ background:var(--bg-surface); border-bottom:1px solid var(--border); }}
    .hero-label-bar-inner {{ max-width:var(--max-width); margin:0 auto; padding:10px 24px; display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
    .hero-featured-label {{ font-size:11px; background:var(--accent-amber); color:#fff; padding:2px 10px; border-radius:20px; font-weight:600; letter-spacing:1px; text-transform:uppercase; font-family:'Inter',sans-serif; }}
    </style>
    <section style="position:relative;width:100%;height:62vh;min-height:380px;max-height:560px;overflow:hidden;background:{h_bg} center/cover no-repeat;">
        <div style="position:absolute;inset:0;background:linear-gradient(to top,rgba(10,8,5,0.88) 0%,rgba(10,8,5,0.5) 40%,rgba(10,8,5,0.12) 100%);"></div>
        <div class="hero-content-inner" style="position:absolute;bottom:60px;left:0;right:0;padding:0 48px;max-width:calc(var(--max-width) + 96px);margin:0 auto;">
            <p style="font-size:11px;color:rgba(255,255,255,0.55);letter-spacing:2px;text-transform:uppercase;font-family:'Inter',sans-serif;margin:0 0 10px;">Aktuell im Magazin</p>
            <span class="badge badge-amber" style="margin-bottom:12px;">{h_cat}</span>
            <h1 style="font-family:'Fraunces',Georgia,serif;font-weight:600;font-size:clamp(24px,3.2vw,40px);color:#fff;margin:0 0 12px;line-height:1.25;max-width:660px;text-shadow:0 2px 8px rgba(0,0,0,0.4);">{hero_article['title']}</h1>
            <p class="hero-teaser" style="font-size:15px;color:rgba(255,255,255,0.80);margin:0 0 20px;max-width:560px;line-height:1.6;">{h_teaser}</p>
            <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
                <a href="{base_url}/artikel/{h_slug}.html" class="btn btn-primary" style="background:var(--accent-amber);border:none;">Weiterlesen</a>
                <span style="font-size:13px;color:rgba(255,255,255,0.55);">{h_date} · {h_rt} Min.</span>
            </div>
        </div>
        <a class="hero-scroll-arrow" href="#article-grid" onclick="document.getElementById('article-grid').scrollIntoView({{behavior:'smooth'}});return false;">
            <svg viewBox="0 0 24 24"><polyline points="6 9 12 15 18 9"/></svg>
            <span>Mehr entdecken</span>
        </a>
    </section>
    <div class="hero-label-bar">
        <div class="hero-label-bar-inner">
            <span class="hero-featured-label">Featured</span>
            <span style="font-size:12px;color:var(--accent-muted);text-transform:uppercase;letter-spacing:1.5px;font-weight:600;">Von Steffen &amp; Elmar</span>
            <span style="color:var(--border);">·</span>
            <span style="font-size:12px;color:var(--accent-muted);">Schottland-Reisende &amp; Whisky-Enthusiasten seit 2007</span>
        </div>
    </div>
    <div style="max-width:var(--max-width);margin:0 auto;padding:14px 24px 0;text-align:center;font-family:'Inter',sans-serif;">
        <p style="margin:0;font-size:13px;color:var(--text-secondary);letter-spacing:0.02em;">
            <span style="color:#C8963E;font-size:15px;">&#127760;</span>
            <span style="margin:0 6px;">Articles available in</span>
            <strong style="color:var(--text-primary);font-weight:600;">English &middot; Fran&ccedil;ais &middot; Nederlands &middot; Espa&ntilde;ol &middot; &#26085;&#26412;&#35486;</strong>
            <span style="color:var(--text-secondary);"> &mdash; open any story to switch language</span>
        </p>
    </div>
    <div id="site-lang-notice" style="display:none;max-width:var(--max-width);margin:14px auto 0;padding:12px 18px;background:rgba(200,150,62,0.12);border-left:3px solid #C8963E;border-radius:3px;font-family:'Inter',sans-serif;font-size:13px;color:#1A1A1A;text-align:left;">
        <strong>Hinweis / Note:</strong> Die Startseite ist nur auf Deutsch verf&uuml;gbar. &Ouml;ffne einen Artikel, um die gew&auml;hlte Sprache zu sehen. <em>Open any article to read it in your chosen language.</em>
    </div>"""

    # --- 2. Featured Stories Grid (Artikel 2-6) ---
    featured_cards_html = ""
    for idx, article in enumerate(articles[1:6]):
        meta = article.get("meta", {})
        slug = meta.get("slug", "")
        teaser = meta.get("teaser", meta.get("meta_description", ""))
        date_display = _german_date(article.get("date", ""))
        category = article.get("category", "Allgemein")
        reading_time = _reading_time(article.get("html_content", "")) if article.get("html_content") else 3
        img_url = article.get("image_url", "")
        img_bg = f"background-image:url({img_url});" if img_url else "background:linear-gradient(135deg, var(--bg-surface) 0%, var(--border) 100%);"

        if idx == 0:
            # Zweiter Artikel als großes Landscape-Card (span 2)
            teaser_short = teaser[:160] + "..." if len(teaser) > 160 else teaser
            featured_cards_html += f"""
        <div class="card featured-card" style="grid-column:span 2;display:grid;grid-template-columns:1.2fr 1fr;overflow:hidden;">
            <div class="featured-card-img" style="{img_bg}background-size:cover;background-position:center;min-height:280px;"></div>
            <div class="card-body" style="padding:28px 32px;display:flex;flex-direction:column;justify-content:center;">
                <span class="badge badge-amber" style="margin-bottom:10px;">{category}</span>
                <h3 class="card-title" style="font-family:'Fraunces',serif;font-size:22px;font-weight:600;margin:0 0 10px;line-height:1.3;"><a href="{base_url}/artikel/{slug}.html" style="color:var(--text-primary);text-decoration:none;">{article['title']}</a></h3>
                <p class="card-meta" style="font-size:13px;color:var(--text-secondary);margin-bottom:10px;">{date_display} · {reading_time} Min. Lesezeit</p>
                <p class="card-teaser" style="font-size:15px;color:var(--text-secondary);line-height:1.6;margin-bottom:16px;">{teaser_short}</p>
                <a href="{base_url}/artikel/{slug}.html" class="btn btn-ghost" style="align-self:flex-start;">Weiterlesen →</a>
            </div>
        </div>"""
        else:
            teaser_short = teaser[:100] + "..." if len(teaser) > 100 else teaser
            featured_cards_html += f"""
        <div class="card">
            <div style="{img_bg}background-size:cover;background-position:center;height:180px;"></div>
            <div class="card-body" style="padding:18px 20px;">
                <span class="badge badge-outline" style="margin-bottom:8px;">{category}</span>
                <h3 class="card-title" style="font-family:'Fraunces',serif;font-size:17px;margin:0 0 8px;line-height:1.3;"><a href="{base_url}/artikel/{slug}.html" style="color:var(--text-primary);text-decoration:none;">{article['title']}</a></h3>
                <p class="card-meta" style="font-size:12px;color:var(--text-secondary);margin-bottom:6px;">{date_display} · {reading_time} Min.</p>
                <p class="card-teaser" style="font-size:14px;color:var(--text-secondary);line-height:1.5;">{teaser_short}</p>
            </div>
        </div>"""

    stories_html = f"""
    <section id="article-grid" style="max-width:var(--max-width);margin:0 auto;padding:48px 24px 64px;">
        <div style="display:flex;align-items:baseline;justify-content:space-between;margin-bottom:28px;">
            <h2 style="font-family:'Fraunces',serif;font-size:24px;font-weight:600;padding-left:0;margin:0;">Aktuelle Geschichten</h2>
            <a href="{base_url}/kategorie/whisky.html" style="font-size:14px;color:var(--accent-amber);text-decoration:none;font-weight:500;">Alle ansehen →</a>
        </div>
        <div class="articles-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
            {featured_cards_html}
        </div>
    </section>"""

    # --- 3. Whisky des Monats ---
    # Try to load wotm.json first
    wotm_data = None
    wotm_path = PROJECT_DIR / "data" / "wotm.json"
    try:
        if wotm_path.exists():
            with open(wotm_path, "r", encoding="utf-8") as _f:
                wotm_data = json.load(_f)
    except Exception:
        wotm_data = None

    whisky_section_html = ""

    wotm_current = wotm_data.get("current", {}) if wotm_data else {}
    if wotm_current.get("approved") is True:
        # Build section from wotm.json
        wotm_name = wotm_current.get("name", "")
        wotm_month = wotm_current.get("month", "")
        wotm_region = wotm_current.get("region", "")
        wotm_age = wotm_current.get("age", "")
        wotm_abv = wotm_current.get("abv", "")
        wotm_price = wotm_current.get("price_eur", "")
        wotm_affiliate = wotm_current.get("affiliate_url", "#")
        wotm_distillery = wotm_current.get("distillery", "")
        wotm_tasting = wotm_current.get("tasting", {})
        wotm_aroma = wotm_tasting.get("aroma", "")
        wotm_geschmack = wotm_tasting.get("geschmack", "")
        wotm_abgang = wotm_tasting.get("abgang", "")
        wotm_wertung = wotm_tasting.get("wertung", 0)

        # Build star rating (1-5 copper stars out of 100)
        stars_out_of_5 = round(wotm_wertung / 20) if wotm_wertung else 0
        stars_html = ""
        for _s in range(5):
            if _s < stars_out_of_5:
                stars_html += '<span style="color:var(--accent-amber);font-size:18px;">&#9733;</span>'
            else:
                stars_html += '<span style="color:var(--border);font-size:18px;">&#9733;</span>'

        # Find matching article link by distillery name
        wotm_article_link = ""
        if wotm_distillery:
            for _a in articles:
                _title = _a.get("title", "").lower()
                _slug = _a.get("meta", {}).get("slug", "")
                if wotm_distillery.lower() in _title and _slug:
                    wotm_article_link = f"{base_url}/artikel/{_slug}.html"
                    break

        # Build sub-info line
        sub_parts = []
        if wotm_region:
            sub_parts.append(wotm_region)
        if wotm_age:
            sub_parts.append(f"{wotm_age} Jahre")
        if wotm_abv:
            sub_parts.append(f"{wotm_abv}% ABV")
        sub_line = " · ".join(sub_parts)

        # CTAs
        cta_html = f'<a href="{wotm_affiliate}" class="btn btn-primary" style="margin-right:12px;" target="_blank" rel="noopener nofollow">Jetzt entdecken</a>'
        if wotm_article_link:
            cta_html += f'<a href="{wotm_article_link}" class="btn btn-ghost">Mehr erfahren</a>'

        whisky_section_html = f"""
    <section class="wotm-section" style="background:var(--bg-surface);padding:64px 24px;border-top:1px solid var(--border);border-bottom:1px solid var(--border);">
        <div style="max-width:var(--max-width);margin:0 auto;">
            <div style="text-align:center;margin-bottom:32px;">
                <p style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:2.5px;color:var(--accent-amber);margin:0 0 6px;">&#9733; Whisky des Monats &#9733;</p>
                <p style="font-size:14px;color:var(--text-secondary);margin:0;">{wotm_month}</p>
            </div>
            <div class="card wotm-card" style="max-width:760px;margin:0 auto;border-left:4px solid var(--accent-amber);padding:32px 36px;display:grid;grid-template-columns:1fr auto;gap:24px;align-items:start;">
                <div>
                    <h3 style="font-family:'Fraunces',serif;font-size:30px;font-weight:600;margin:0 0 4px;line-height:1.2;">{wotm_name}</h3>
                    <p style="font-size:13px;color:var(--accent-muted);margin:0 0 20px;letter-spacing:0.5px;text-transform:uppercase;">{sub_line}</p>
                    <div style="display:grid;gap:12px;margin:0 0 20px;">
                        <div style="display:flex;gap:12px;align-items:flex-start;">
                            <span style="font-size:18px;flex-shrink:0;">👃</span>
                            <div><strong style="display:block;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--accent-amber);margin-bottom:3px;">Aroma</strong><span style="font-size:14px;color:var(--text-secondary);line-height:1.5;">{wotm_aroma}</span></div>
                        </div>
                        <div style="display:flex;gap:12px;align-items:flex-start;">
                            <span style="font-size:18px;flex-shrink:0;">👅</span>
                            <div><strong style="display:block;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--accent-amber);margin-bottom:3px;">Geschmack</strong><span style="font-size:14px;color:var(--text-secondary);line-height:1.5;">{wotm_geschmack}</span></div>
                        </div>
                        <div style="display:flex;gap:12px;align-items:flex-start;">
                            <span style="font-size:18px;flex-shrink:0;">✨</span>
                            <div><strong style="display:block;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--accent-amber);margin-bottom:3px;">Abgang</strong><span style="font-size:14px;color:var(--text-secondary);line-height:1.5;">{wotm_abgang}</span></div>
                        </div>
                    </div>
                    <div style="display:flex;align-items:center;gap:12px;margin:0 0 16px;">
                        <div>{stars_html}</div>
                        <span style="font-size:14px;font-weight:600;color:var(--text-primary);">{wotm_wertung}/100</span>
                    </div>
                    {f'<p style="font-size:15px;font-weight:600;color:var(--accent-amber);margin:0 0 20px;">Ab ca. {wotm_price} €</p>' if wotm_price else ""}
                    <div style="display:flex;flex-wrap:wrap;gap:12px;">{cta_html}</div>
                </div>
                <div class="wotm-emoji-col" style="text-align:center;min-width:80px;">
                    <div style="font-size:48px;line-height:1;">🥃</div>
                    <p style="font-size:11px;color:var(--accent-muted);margin-top:8px;text-transform:uppercase;letter-spacing:1px;">Steffens<br>Empfehlung</p>
                </div>
            </div>
        </div>
    </section>"""
    else:
        # Fallback: first whisky category article
        whisky_article = None
        for a in articles:
            if a.get("category", "").lower() == "whisky":
                whisky_article = a
                break

        if whisky_article:
            w_meta = whisky_article.get("meta", {})
            w_slug = w_meta.get("slug", "")
            w_teaser = w_meta.get("teaser", w_meta.get("meta_description", ""))
            w_img_url = whisky_article.get("image_url", "")
            w_img_bg = f"background-image:url({w_img_url});" if w_img_url else "background:linear-gradient(135deg, var(--bg-surface) 0%, var(--border) 100%);"

            whisky_section_html = f"""
    <section class="wotm-section" style="background:var(--bg-surface);padding:64px 24px;border-top:1px solid var(--border);border-bottom:1px solid var(--border);">
        <div style="max-width:var(--max-width);margin:0 auto;">
            <p style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:2.5px;color:var(--accent-amber);margin:0 0 24px;text-align:center;">&#9733; Whisky des Monats &#9733;</p>
            <div class="card wotm-card" style="max-width:760px;margin:0 auto;display:grid;grid-template-columns:220px 1fr;border-left:4px solid var(--accent-amber);overflow:hidden;">
                <div style="{w_img_bg}background-size:cover;background-position:center;min-height:220px;"></div>
                <div class="card-body" style="padding:28px 32px;">
                    <h3 style="font-family:'Fraunces',serif;font-size:22px;font-weight:600;margin:0 0 12px;">{whisky_article['title']}</h3>
                    <p style="font-size:15px;color:var(--text-secondary);line-height:1.6;margin-bottom:20px;">{w_teaser}</p>
                    <a href="{base_url}/artikel/{w_slug}.html" class="btn btn-primary">Jetzt entdecken</a>
                </div>
            </div>
        </div>
    </section>"""

    # --- 4. Newsletter CTA ---
    newsletter_html = """
    <section class="newsletter-section">
        <div class="newsletter-inner">
            <h2 style="font-family:'Fraunces',serif;font-size:24px;padding-left:0;">Schottland-Post</h2>
            <p>Die besten Whisky-Geschichten und Reise-Tipps, einmal im Monat. Kostenlos.</p>
            <form class="newsletter-form">
                <input type="email" placeholder="Deine E-Mail-Adresse" required>
                <button type="submit" class="btn btn-primary">Anmelden</button>
            </form>
            <p style="font-size:12px;color:var(--accent-muted);margin-top:12px;">Kein Spam, jederzeit abmeldbar. Versprochen.</p>
        </div>
    </section>"""

    # --- 5. Region Cards ---
    region_cards_html = ""
    for cat_name, count in sorted(categories.items()):
        cat_slug = cat_name.lower()
        emoji = cat_emoji.get(cat_name, "🥃")
        region_cards_html += f"""
            <a href="{base_url}/kategorie/{cat_slug}.html" class="card" style="text-decoration:none;text-align:center;">
                <div style="font-size:2.5em;padding:24px 0 8px;">{emoji}</div>
                <div class="card-body" style="padding:0 20px 20px;">
                    <h3 style="font-family:'Fraunces',serif;font-size:16px;margin:0 0 4px;">{cat_name}</h3>
                    <p style="font-size:13px;color:var(--text-secondary);margin:0;">{count} Artikel</p>
                </div>
            </a>"""

    regions_html = f"""
    <section style="max-width:var(--max-width);margin:0 auto;padding:64px 24px;">
        <h2 style="text-align:center;padding-left:0;font-size:22px;font-weight:600;">Regionen entdecken</h2>
        <div class="home-cat-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-top:32px;">
            {region_cards_html}
        </div>
    </section>"""

    # --- 6. Trust Section ---
    trust_html = f"""
    <section class="trust-section">
        <div class="trust-stats">
            <div>
                <div class="trust-stat-number">18+</div>
                <div class="trust-stat-label">Jahre unterwegs</div>
            </div>
            <div>
                <div class="trust-stat-number">{len(articles)}</div>
                <div class="trust-stat-label">Geschichten</div>
            </div>
            <div>
                <div class="trust-stat-number">110+</div>
                <div class="trust-stat-label">Destillerien besucht</div>
            </div>
            <div>
                <div class="trust-stat-number">seit 2007</div>
                <div class="trust-stat-label">auf Whisky-Reise</div>
            </div>
        </div>
    </section>"""

    # --- Assemble full page content (no sidebar) ---
    content = hero_html + stories_html + whisky_section_html + newsletter_html + regions_html + trust_html

    return _base_template().format(
        title="Start",
        site_name=site_name,
        meta_description=tagline,
        keywords="Whisky, Scotch, Single Malt, Reise, Schottland, Destillerien",
        og_description=tagline,
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/",
        base_url=base_url,
        content=content,
        json_ld=_json_ld_website(base_url),
    )


def build_category_page(category_name, articles, config):
    """Erstellt eine Kategorieseite."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    # Funktion zum Prüfen, ob ein Artikel zu dieser Kategorie gehört
    def belongs_to_category(article, cat_name):
        # Prüfe altes single-category Format
        if article.get("category", "").lower() == cat_name.lower():
            return True
        # Prüfe neues multi-category Format
        categories = article.get("categories", [])
        if isinstance(categories, list):
            return any(c.lower() == cat_name.lower() for c in categories)
        return False

    cat_emoji_map = {"Whisky": "🥃", "Reise": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Lifestyle": "✨", "Natur": "🌿", "Urlaub": "🌄"}

    filtered = [a for a in articles if belongs_to_category(a, category_name)]
    cards_html = ""
    for article in filtered:
        meta = article.get("meta", {})
        slug = meta.get("slug", "")
        teaser = meta.get("teaser", meta.get("meta_description", ""))
        date_display = _german_date(article.get("date", ""))
        cat = article.get("category", category_name)
        reading_time = _reading_time(article.get("html_content", "")) if article.get("html_content") else 3
        img_url = article.get("image_url", "")
        img_bg = f"background-image:url({img_url});" if img_url else "background:linear-gradient(135deg, var(--bg-surface) 0%, var(--border) 100%);"
        teaser_short = teaser[:120] + "..." if len(teaser) > 120 else teaser

        cards_html += f"""
            <div class="card">
                <div class="card-image" style="{img_bg}background-size:cover;background-position:center;height:200px;"></div>
                <div class="card-body">
                    <span class="badge badge-outline">{cat}</span>
                    <h3 class="card-title"><a href="{base_url}/artikel/{slug}.html">{article['title']}</a></h3>
                    <p class="card-meta">{date_display} · {reading_time} Min. Lesezeit</p>
                    <p class="card-teaser">{teaser_short}</p>
                </div>
            </div>"""

    if not cards_html:
        cards_html = '<p style="color: var(--text-secondary);">Noch keine Artikel in dieser Kategorie.</p>'

    content = f"""
    <style>
        @media (max-width: 900px) {{
            .cat-grid {{ grid-template-columns: repeat(2, 1fr) !important; }}
        }}
        @media (max-width: 600px) {{
            .cat-grid {{ grid-template-columns: 1fr !important; }}
        }}
    </style>
    <div style="max-width:var(--max-width);margin:0 auto;padding:48px 24px 32px;">
        <nav style="font-size:13px;color:var(--text-secondary);margin-bottom:16px;">
            <a href="/" style="color:var(--accent-amber);text-decoration:none;">Startseite</a>
            <span style="margin:0 8px;">›</span>
            <span>{category_name}</span>
        </nav>
        <h1 style="font-size:28px;margin:0;">{category_name}</h1>
        <p style="color:var(--text-secondary);margin-top:8px;">{len(filtered)} Artikel</p>
    </div>
    <div style="max-width:var(--max-width);margin:0 auto;padding:0 24px 64px;">
        <div class="cat-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:24px;">
            {cards_html}
        </div>
    </div>"""

    _category_descriptions = {
        "whisky": "Whisky-Wissen, Destillerie-Porträts und Verkostungsnotizen – alles rund um Scotch, Single Malt und mehr im Whisky Magazin.",
        "reise": "Reiseberichte und Insider-Tipps für Schottland, Whisky-Regionen und Destillerie-Besuche – direkt von Steffen & Elmar.",
        "lifestyle": "Whisky-Kultur, Geschenkideen und Genuss-Tipps für Enthusiasten – Lifestyle rund ums Thema Scotch im Whisky Magazin.",
        "natur": "Schottlands wilde Natur: Highlands, Inseln und Küsten – Naturerlebnisse aus dem Whisky Magazin.",
        "urlaub": "Urlaub mit Whisky: Reisepläne, Destillerie-Touren und Insidertipps für Schottland-Reisende.",
    }
    cat_description = _category_descriptions.get(
        category_name.lower(),
        f"Alle Artikel und Berichte rund um das Thema {category_name} im Whisky Magazin.",
    )

    breadcrumb_ld = _json_ld_breadcrumb([
        ("Startseite", "/"),
        (category_name, f"/kategorie/{category_name.lower()}.html"),
    ], base_url)
    return _base_template().format(
        title=f"Kategorie: {category_name}",
        site_name=site_name,
        meta_description=cat_description,
        keywords=category_name,
        og_description=cat_description,
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/kategorie/{category_name.lower()}.html",
        base_url=base_url,
        content=content,
        json_ld=breadcrumb_ld,
    )


def build_map_page(config):
    """Erstellt die interaktive Karten-Seite mit Leaflet.js."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    map_config = config.get("map", {})
    center_lat, center_lon = map_config.get("default_center", [57.0, -4.5])
    default_zoom = map_config.get("default_zoom", 6)

    content = f"""
    <!-- Map Hero (editorial, matching site design) -->
    <section class="map-hero" style="background:var(--text-primary);color:#fff;padding:56px 24px 48px;text-align:center;position:relative;overflow:hidden;">
        <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 60% 40%,rgba(200,150,62,0.18) 0%,transparent 65%);pointer-events:none;"></div>
        <div style="position:relative;max-width:760px;margin:0 auto;">
            <p style="font-size:12px;letter-spacing:3px;text-transform:uppercase;color:var(--accent-amber);margin:0 0 16px;font-weight:600;">Interaktive Reisekarte</p>
            <h1 style="font-family:'Fraunces',Georgia,serif;font-size:clamp(28px,4vw,42px);font-weight:600;line-height:1.2;margin:0 0 12px;color:#fff;">Unsere Whisky-Reisekarte</h1>
            <p style="font-size:17px;color:rgba(255,255,255,0.75);margin:0;">18+ Jahre, 110+ Destillerien, 201 Orte &mdash; von Schottland &uuml;ber Irland bis Kentucky</p>
        </div>
    </section>
    <nav class="breadcrumb"><div class="breadcrumb-inner"><a href="/">Startseite</a> &rsaquo; Karte</div></nav>

    <div class="map-page">
        <!-- Prominente Suchleiste -->
        <div class="map-search-bar" id="map-search-bar">
            <div class="search-inner">
                <span class="search-icon">🔍</span>
                <div style="position:relative;flex:1;">
                    <input type="text" id="search-input"
                        placeholder="Destillerie oder Ort suchen … z.B. Bowmore, Lagavulin, Orkney"
                        autocomplete="off"
                        oninput="handleSearchInput(this.value)"
                        onkeydown="handleSearchKey(event)">
                    <button id="search-clear" onclick="clearSearch()" title="Suche löschen"
                        style="display:none;position:absolute;right:8px;top:50%;transform:translateY(-50%);
                               background:none;border:none;cursor:pointer;font-size:18px;color:var(--text-secondary);
                               line-height:1;padding:0 4px;">×</button>
                    <div id="search-suggestions" style="display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;
                        background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius-sm);
                        box-shadow:var(--shadow-hover);z-index:1000;max-height:280px;overflow-y:auto;">
                    </div>
                </div>
                <button class="btn btn-primary" onclick="applyFilters()" style="white-space:nowrap;padding:10px 20px;font-size:14px;">Suchen</button>
            </div>
        </div>
        <!-- Filter-Leiste -->
        <div class="map-controls" id="map-controls">
            <div class="filter-group">
                <label for="filter-year">Jahr:</label>
                <select id="filter-year"><option value="">Alle Jahre</option></select>
            </div>
            <div class="filter-group">
                <label for="filter-region">Region:</label>
                <select id="filter-region"><option value="">Alle Regionen</option></select>
            </div>
            <div class="filter-group">
                <label for="filter-country">Land:</label>
                <select id="filter-country"><option value="">Alle Länder</option></select>
            </div>
            <div class="filter-group filter-toggles">
                <label class="toggle-label"><input type="checkbox" id="toggle-distillery" checked> Destillerien</label>
                <label class="toggle-label"><input type="checkbox" id="toggle-poi" checked> Sehenswürdigkeiten</label>
            </div>
            <div class="map-stats" id="map-stats"></div>
        </div>
        <div id="map" style="height: 65vh; min-height: 400px; border-radius: 12px; box-shadow: 0 4px 32px rgba(139,115,85,0.15); border: 1px solid var(--border); z-index: 1;"></div>
        <div class="location-directory" id="location-cards"></div>
    </div>

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

    <style>
        .map-page {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
        /* Prominente Suchleiste */
        .map-search-bar {{
            background: var(--bg-elevated);
            border: 2px solid var(--accent-amber);
            border-radius: var(--radius-sm);
            padding: 12px 16px;
            margin-bottom: 12px;
            box-shadow: var(--shadow-hover);
        }}
        .search-inner {{
            display: flex; align-items: center; gap: 10px;
        }}
        .search-icon {{ font-size: 20px; flex-shrink: 0; }}
        #search-input {{
            width: 100%; padding: 10px 36px 10px 12px;
            border: 1.5px solid var(--border); border-radius: var(--radius-sm);
            font-size: 15px; font-family: 'Inter', sans-serif;
            color: var(--text-primary); background: var(--bg-primary);
            transition: border-color 0.2s; outline: none;
        }}
        #search-input:focus {{ border-color: var(--accent-amber); }}
        #search-input::placeholder {{ color: var(--text-secondary); }}
        .suggestion-item {{
            display: flex; align-items: center; gap: 10px;
            padding: 10px 14px; cursor: pointer;
            border-bottom: 1px solid var(--border);
            transition: background 0.15s;
        }}
        .suggestion-item:last-child {{ border-bottom: none; }}
        .suggestion-item:hover {{ background: var(--bg-surface); }}
        .suggestion-item.active {{ background: var(--bg-surface); }}
        .suggestion-name {{ font-weight: 600; font-size: 14px; color: var(--text-primary); font-family: 'Fraunces', serif; }}
        .suggestion-meta {{ font-size: 12px; color: var(--text-secondary); font-family: 'Inter', sans-serif; }}
        .suggestion-type {{ font-size: 18px; flex-shrink: 0; }}
        .breadcrumb {{
            font-family: 'Inter', sans-serif; font-size: 13px;
            color: var(--text-secondary); margin-bottom: 12px;
        }}
        .breadcrumb a {{ color: var(--accent-amber); text-decoration: none; }}
        .breadcrumb a:hover {{ text-decoration: underline; }}
        /* Map tile warm filter – Editorial Whisky-Palette */
        #map .leaflet-tile-pane {{
            filter: saturate(0.7) sepia(0.18) brightness(1.04) contrast(0.95) hue-rotate(-5deg);
        }}
        #map .leaflet-control-attribution {{
            background: rgba(245,240,232,0.9) !important;
            font-family: 'Inter', sans-serif !important;
            font-size: 11px !important;
            color: var(--text-secondary) !important;
        }}
        #map .leaflet-control-attribution a {{
            color: var(--accent-amber) !important;
        }}
        .leaflet-popup-content-wrapper {{
            border-radius: 10px !important;
            box-shadow: 0 8px 32px rgba(139,115,85,0.18) !important;
            border: 1px solid var(--border);
            font-family: 'Inter', sans-serif;
            padding: 4px !important;
        }}
        .leaflet-popup-tip {{
            border-top-color: var(--bg-elevated) !important;
            box-shadow: 0 4px 12px rgba(139,115,85,0.1);
        }}
        .leaflet-control-zoom a {{
            background: var(--bg-elevated) !important;
            color: var(--text-primary) !important;
            border-color: var(--border) !important;
            font-family: 'Inter', sans-serif !important;
            width: 34px !important;
            height: 34px !important;
            line-height: 34px !important;
            border-radius: var(--radius-sm) !important;
        }}
        .leaflet-control-zoom a:hover {{
            background: var(--bg-surface) !important;
            color: var(--accent-amber) !important;
        }}
        .leaflet-control-zoom {{
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-sm) !important;
            box-shadow: var(--shadow-sm) !important;
            overflow: hidden;
        }}
        .map-controls {{
            display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
            padding: 16px; background: var(--bg-surface); border-radius: var(--radius-sm);
            border: 1px solid var(--border); margin-bottom: 16px;
        }}
        .filter-group {{ display: flex; align-items: center; gap: 6px; }}
        .filter-group label {{ font-size: 0.85em; color: var(--text-secondary);
            font-family: 'Inter', sans-serif; }}
        .filter-group select {{
            padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm);
            background: var(--bg-primary); font-size: 0.85em; cursor: pointer;
            font-family: 'Inter', sans-serif; color: var(--text-primary);
            transition: border-color 0.2s;
        }}
        .filter-group select:focus {{
            outline: none; border-color: var(--accent-amber);
        }}
        .filter-toggles {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .toggle-label {{
            display: flex; align-items: center; gap: 4px; cursor: pointer;
            font-size: 0.82em !important; white-space: nowrap;
            font-family: 'Inter', sans-serif; color: var(--text-secondary);
        }}
        .toggle-label input {{ accent-color: var(--accent-amber); }}
        .map-stats {{
            margin-left: auto; font-size: 0.82em; color: var(--text-secondary);
            font-family: 'Inter', sans-serif;
        }}
        /* Verzeichnis-Styles */
        .location-directory {{ margin-top: 32px; }}
        .dir-section {{
            background: var(--bg-elevated); border-radius: var(--radius-sm);
            box-shadow: var(--shadow-sm); padding: 20px 24px; margin-bottom: 20px;
        }}
        .dir-section-header {{
            display: flex; align-items: center; gap: 10px; margin-bottom: 16px;
            padding-bottom: 10px; border-bottom: 2px solid var(--bg-primary);
        }}
        .dir-section-icon {{ font-size: 1.4em; }}
        .dir-section-title {{
            font-family: 'Fraunces', serif;
            font-size: 1.1em; font-weight: 600; color: var(--text-primary);
            margin: 0;
        }}
        .dir-section-count {{
            background: var(--accent-amber); color: #fff; font-size: 0.75em;
            padding: 2px 8px; border-radius: 12px; font-weight: bold;
            font-family: 'Inter', sans-serif;
        }}
        .dir-items {{
            display: flex; flex-wrap: wrap; gap: 10px;
        }}
        .dir-item {{
            display: flex; flex-direction: column; gap: 3px;
            background: var(--bg-primary); border-radius: 10px;
            padding: 10px 14px; cursor: pointer; text-decoration: none;
            border: 1px solid transparent;
            transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;
            min-width: 150px; max-width: 250px;
        }}
        .dir-item:hover {{
            border-color: var(--accent-amber); box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }}
        .dir-item.type-distillery {{ border-left: 3px solid var(--accent-amber); }}
        .dir-item.type-city {{ border-left: 3px solid var(--accent-sage); }}
        .dir-item.type-nature {{ border-left: 3px solid #5B8C5A; }}
        .dir-item.type-poi {{ border-left: 3px solid var(--accent-warm); }}
        .dir-item.type-travel_stop {{ border-left: 3px solid var(--accent-muted); }}
        .dir-item-name {{
            font-family: 'Fraunces', serif;
            font-weight: 600; font-size: 0.92em; color: var(--text-primary);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .dir-item-region {{
            font-size: 0.75em; color: var(--text-secondary);
            font-family: 'Inter', sans-serif;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .dir-item-footer {{
            display: flex; align-items: center; gap: 6px; margin-top: 2px;
        }}
        .dir-item-years {{
            font-size: 0.7em; color: var(--accent-amber); font-weight: 500;
            font-family: 'Inter', sans-serif;
        }}
        .dir-item-arts {{
            font-size: 0.7em; color: var(--text-secondary);
            font-family: 'Inter', sans-serif;
            margin-left: auto;
        }}
        .dir-empty {{
            color: var(--text-secondary); font-size: 0.9em; font-style: italic;
            padding: 8px 0;
        }}
        .type-distillery {{ background: var(--bg-surface); color: var(--accent-amber); }}
        .type-city {{ background: rgba(91,123,106,0.12); color: var(--accent-sage); }}
        .type-nature {{ background: rgba(91,140,90,0.12); color: #5B8C5A; }}
        .type-poi {{ background: rgba(196,88,58,0.12); color: var(--accent-warm); }}
        .type-travel_stop {{ background: rgba(138,125,107,0.12); color: var(--accent-muted); }}

        /* Popup-Styles */
        .map-popup {{ min-width: 220px; max-width: 300px; font-family: 'Inter', sans-serif; }}
        .map-popup h3 {{ font-family: 'Fraunces', serif; font-size: 1em; font-weight: 600; margin: 0 0 6px; color: var(--text-primary); }}
        .map-popup .popup-type {{
            font-family: 'Inter', sans-serif;
            font-size: 0.75em; display: inline-block; padding: 1px 6px;
            border-radius: var(--radius-pill); margin-bottom: 6px;
        }}
        .map-popup .popup-photos {{ display: flex; gap: 4px; margin: 8px 0; overflow-x: auto; }}
        .map-popup .popup-photos img {{
            width: 90px; height: 65px; object-fit: cover; border-radius: var(--radius-sm); cursor: pointer;
        }}
        .map-popup .popup-years {{ font-size: 0.8em; color: var(--text-secondary); margin: 4px 0; }}
        .map-popup .popup-articles {{ margin-top: 6px; }}
        .map-popup .popup-articles a {{
            display: block; font-size: 0.82em; color: var(--accent-amber);
            text-decoration: none; padding: 3px 0; border-top: 1px solid var(--border);
        }}
        .map-popup .popup-articles a:hover {{ color: var(--text-primary); }}

        /* Leaflet-Anpassungen */
        .leaflet-popup-content-wrapper {{ border-radius: var(--radius-sm); box-shadow: var(--shadow-hover); }}
        .marker-cluster-small {{ background-color: rgba(200, 150, 62, 0.3); }}
        .marker-cluster-small div {{
            background-color: var(--accent-amber); color: #fff;
            font-family: 'Inter', sans-serif; font-weight: 600; font-size: 13px;
            width: 32px; height: 32px; line-height: 32px; border-radius: 50%;
            box-shadow: 0 2px 8px rgba(200,150,62,0.35);
        }}
        .marker-cluster-medium {{ background-color: rgba(200, 150, 62, 0.35); }}
        .marker-cluster-medium div {{
            background-color: var(--accent-warm); color: #fff;
            font-family: 'Inter', sans-serif; font-weight: 600; font-size: 14px;
            width: 36px; height: 36px; line-height: 36px; border-radius: 50%;
            box-shadow: 0 2px 12px rgba(139,115,85,0.4);
        }}
        .marker-cluster-large {{ background-color: rgba(139, 115, 85, 0.35); }}
        .marker-cluster-large div {{
            background-color: var(--text-primary); color: var(--accent-amber);
            font-family: 'Inter', sans-serif; font-weight: 700; font-size: 15px;
            width: 40px; height: 40px; line-height: 40px; border-radius: 50%;
            box-shadow: 0 3px 16px rgba(26,26,26,0.3);
        }}

        @media (max-width: 768px) {{
            .map-controls {{ flex-direction: column; align-items: flex-start; }}
            .map-stats {{ margin-left: 0; }}
            .dir-items {{ flex-direction: column; }}
            #map {{ height: 50vh !important; }}
            .search-inner {{ flex-wrap: wrap; }}
            .search-inner .btn {{ width: 100%; }}
        }}
    </style>

    <script>
    (function() {{
        const BASE_URL = '{base_url}';
        // Für lokales Testen: Daten und Bilder relativ laden
        const LOCAL_BASE = window.location.origin;
        const CENTER = [{center_lat}, {center_lon}];
        const ZOOM = {default_zoom};

        // Icons
        const ICONS = {{
            distillery: L.divIcon({{ className: 'custom-marker', html: '<div style="font-size:22px">🥃</div>', iconSize: [28, 28], iconAnchor: [14, 14] }}),
            city: L.divIcon({{ className: 'custom-marker', html: '<div style="font-size:20px">🏙️</div>', iconSize: [28, 28], iconAnchor: [14, 14] }}),
            nature: L.divIcon({{ className: 'custom-marker', html: '<div style="font-size:20px">🌿</div>', iconSize: [28, 28], iconAnchor: [14, 14] }}),
            poi: L.divIcon({{ className: 'custom-marker', html: '<div style="font-size:20px">📍</div>', iconSize: [28, 28], iconAnchor: [14, 14] }}),
            travel_stop: L.divIcon({{ className: 'custom-marker', html: '<div style="font-size:18px">✈️</div>', iconSize: [28, 28], iconAnchor: [14, 14] }})
        }};

        // Routen-Farben pro Jahr
        const ROUTE_COLORS = [
            '#e6194B', '#3cb44b', '#4363d8', '#f58231', '#911eb4',
            '#42d4f4', '#f032e6', '#bfef45', '#fabed4', '#469990',
            '#dcbeff', '#9A6324', '#800000', '#aaffc3', '#808000',
            '#000075', '#a9a9a9', '#e6beff'
        ];

        const TYPE_LABELS = {{
            distillery: 'Destillerie', city: 'Stadt', nature: 'Natur',
            poi: 'Sehenswürdigkeit', travel_stop: 'Reisestopp'
        }};

        let mapData = null;
        let map = null;
        let markerCluster = null;
        let allMarkers = [];
        let routeLayers = [];

        // Karte initialisieren
        map = L.map('map').setView(CENTER, ZOOM);
        // CartoDB Voyager: eleganter, minimalistischer Kartenstil
        L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }}).addTo(map);

        markerCluster = L.markerClusterGroup({{
            maxClusterRadius: 40,
            spiderfyOnMaxZoom: true,
            showCoverageOnHover: false,
            disableClusteringAtZoom: 13
        }});
        map.addLayer(markerCluster);

        // Daten laden
        fetch(LOCAL_BASE + '/data/map-data.json')
            .then(r => r.json())
            .then(data => {{
                mapData = data;
                populateFilters(data);
                renderMarkers(data.locations);

                renderCards(data.locations);
                updateStats(data.locations);
                handleUrlParams();
            }})
            .catch(err => console.error('Karten-Daten konnten nicht geladen werden:', err));

        function populateFilters(data) {{
            const yearSel = document.getElementById('filter-year');
            data.years.forEach(y => {{
                const opt = document.createElement('option');
                opt.value = y; opt.textContent = y;
                yearSel.appendChild(opt);
            }});
            const regionSel = document.getElementById('filter-region');
            data.regions.forEach(r => {{
                const opt = document.createElement('option');
                opt.value = r; opt.textContent = r;
                regionSel.appendChild(opt);
            }});
            const countrySel = document.getElementById('filter-country');
            (data.countries || []).forEach(c => {{
                const opt = document.createElement('option');
                opt.value = c; opt.textContent = c;
                countrySel.appendChild(opt);
            }});
        }}

        function createPopup(loc) {{
            let html = '<div class="map-popup">';
            html += '<h3>' + loc.name + '</h3>';
            html += '<span class="popup-type type-' + loc.type + '">' + (TYPE_LABELS[loc.type] || loc.type) + '</span>';
            html += ' <span style="font-size:0.75em;color:var(--text-secondary)">' + loc.region + ', ' + loc.country + '</span>';

            // Fotos
            if (loc.photos && loc.photos.length > 0) {{
                html += '<div class="popup-photos">';
                loc.photos.slice(0, 4).forEach(p => {{
                    html += '<img src="' + LOCAL_BASE + p.src + '" alt="' + p.caption + '" loading="lazy">';
                }});
                html += '</div>';
            }}

            // Besuchsjahre
            if (loc.years_visited && loc.years_visited.length > 0) {{
                html += '<div class="popup-years">Besucht: ' + loc.years_visited.join(', ') + '</div>';
            }}

            // Verlinkte Artikel
            if (loc.articles && loc.articles.length > 0 && mapData && mapData.articles) {{
                html += '<div class="popup-articles">';
                loc.articles.forEach(slug => {{
                    const meta = mapData.articles[slug];
                    if (meta) {{
                        html += '<a href="' + LOCAL_BASE + '/artikel/' + slug + '.html">' + meta.title + '</a>';
                    }}
                }});
                html += '</div>';
            }}

            html += '</div>';
            return html;
        }}

        function renderMarkers(locations) {{
            markerCluster.clearLayers();
            allMarkers = [];
            // Duplikat-Schutz: gleicher Name + gleicher Typ = nur 1 Marker
            const seenMarkers = new Set();
            locations.forEach(loc => {{
                const dedupeKey = loc.name.toLowerCase() + '|' + loc.type;
                if (seenMarkers.has(dedupeKey)) return;
                seenMarkers.add(dedupeKey);
                const icon = ICONS[loc.type] || ICONS.poi;
                const marker = L.marker([loc.lat, loc.lon], {{ icon: icon }});
                marker.bindPopup(createPopup(loc), {{ maxWidth: 320 }});
                marker._locData = loc;
                allMarkers.push(marker);
                markerCluster.addLayer(marker);
            }});
        }}

        function renderRoutes(routes) {{
            routeLayers.forEach(l => map.removeLayer(l));
            routeLayers = [];
            routes.forEach((route, i) => {{
                const color = ROUTE_COLORS[i % ROUTE_COLORS.length];
                const layer = L.geoJSON(route.geojson, {{
                    style: {{ color: color, weight: 3, opacity: 0.7, dashArray: '8 4' }}
                }});
                layer.bindTooltip(route.label, {{ sticky: true, className: 'route-tooltip' }});
                layer._routeData = route;
                layer.addTo(map);
                routeLayers.push(layer);
            }});
        }}

        function renderCards(locations) {{
            const container = document.getElementById('location-cards');

            const SECTIONS = [
                {{ key: 'distillery', icon: '🥃', label: 'Destillerien' }},
                {{ key: 'poi',        icon: '📍', label: 'Sehenswürdigkeiten' }},
            ];

            let html = '';
            SECTIONS.forEach(sec => {{
                // Deduplizierung: gleicher Name innerhalb derselben Sektion = nur einmal zeigen
                const seenNames = new Set();
                const items = locations
                    .filter(l => {{
                        if (l.type !== sec.key) return false;
                        const key = l.name.toLowerCase();
                        if (seenNames.has(key)) return false;
                        seenNames.add(key);
                        return true;
                    }})
                    .sort((a, b) => a.name.localeCompare(b.name, 'de'));
                if (items.length === 0) return;

                html += '<div class="dir-section">'
                    + '<div class="dir-section-header">'
                    + '<span class="dir-section-icon">' + sec.icon + '</span>'
                    + '<h3 class="dir-section-title">' + sec.label + '</h3>'
                    + '<span class="dir-section-count">' + items.length + '</span>'
                    + '</div>'
                    + '<div class="dir-items">';

                items.forEach(loc => {{
                    const years = loc.years_visited && loc.years_visited.length
                        ? loc.years_visited.sort().join(', ') : '';
                    const artCount = loc.articles ? loc.articles.length : 0;
                    const artLabel = artCount === 1 ? '1 Artikel' : (artCount > 1 ? artCount + ' Artikel' : '');
                    const firstArticle = (artCount > 0 && mapData && mapData.articles)
                        ? (mapData.articles[loc.articles[0]] || null) : null;
                    const href = firstArticle
                        ? LOCAL_BASE + '/artikel/' + loc.articles[0] + '.html'
                        : '#';

                    html += '<a class="dir-item type-' + loc.type + '" data-loc-id="' + loc.id + '" href="' + href + '">'
                        + '<span class="dir-item-name">' + loc.name + '</span>'
                        + '<span class="dir-item-region">' + loc.region + (loc.country && loc.country !== 'Schottland' ? ', ' + loc.country : '') + '</span>'
                        + '<div class="dir-item-footer">'
                        + (years ? '<span class="dir-item-years">' + years + '</span>' : '')
                        + (artLabel ? '<span class="dir-item-arts">📖 ' + artLabel + '</span>' : '')
                        + '</div>'
                        + '</a>';
                }});

                html += '</div></div>';
            }});

            container.innerHTML = html || '<p class="dir-empty">Keine Orte für die gewählten Filter gefunden.</p>';

            // Klick auf Karte -> Location auf Karte zentrieren
            container.querySelectorAll('.dir-item').forEach(item => {{
                item.addEventListener('click', (e) => {{
                    const locId = item.dataset.locId;
                    const marker = allMarkers.find(m => m._locData.id === locId);
                    if (marker) {{
                        e.preventDefault();
                        map.setView(marker.getLatLng(), 13);
                        markerCluster.zoomToShowLayer(marker, () => {{
                            marker.openPopup();
                        }});
                        window.scrollTo({{ top: 0, behavior: 'smooth' }});
                    }}
                }});
            }});
        }}

        function updateStats(locations) {{
            const visible = getVisibleLocations(locations);
            const distCount = visible.filter(l => l.type === 'distillery').length;
            document.getElementById('map-stats').textContent =
                visible.length + ' Orte, davon ' + distCount + ' Destillerien';
        }}

        function getVisibleLocations(locations) {{
            const year    = document.getElementById('filter-year').value;
            const region  = document.getElementById('filter-region').value;
            const country = document.getElementById('filter-country').value;
            const searchEl = document.getElementById('search-input');
            const query   = searchEl ? searchEl.value.trim().toLowerCase() : '';
            // Nur Destillerien und Sehenswürdigkeiten (poi) anzeigen
            const types = ['distillery', 'poi']
                .filter(t => document.getElementById('toggle-' + t) && document.getElementById('toggle-' + t).checked);

            // Deduplizierung: Locations mit gleicher lat/lon+name werden zusammengeführt
            const seen = new Set();
            return locations.filter(loc => {{
                if (year && !loc.years_visited.includes(parseInt(year))) return false;
                if (region && loc.region !== region) return false;
                if (country && loc.country !== country) return false;
                if (!types.includes(loc.type)) return false;
                if (query) {{
                    const nameMatch = loc.name.toLowerCase().includes(query);
                    const regionMatch = (loc.region || '').toLowerCase().includes(query);
                    if (!nameMatch && !regionMatch) return false;
                }}
                // Duplikat-Schutz: gleicher Name + gleicher Typ = nur einmal zeigen
                const key = loc.name.toLowerCase() + '|' + loc.type;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            }});
        }}

        function applyFilters() {{
            if (!mapData) return;
            const visible = getVisibleLocations(mapData.locations);
            // Sichtbare Orte als Set (Name|Typ) für schnellen Vergleich
            const visibleKeys = new Set(visible.map(l => l.name.toLowerCase() + '|' + l.type));
            markerCluster.clearLayers();
            allMarkers.forEach(m => {{
                const key = m._locData.name.toLowerCase() + '|' + m._locData.type;
                if (visibleKeys.has(key)) {{
                    markerCluster.addLayer(m);
                }}
            }});

            renderCards(visible);
            updateStats(mapData.locations);
        }}

        // ---- AUTOCOMPLETE SUCHE ----
        const TYPE_ICONS = {{
            distillery: '🥃', city: '🏙️', nature: '🌿', poi: '📍', travel_stop: '✈️'
        }};
        let suggestionIndex = -1;

        function handleSearchInput(val) {{
            document.getElementById('search-clear').style.display = val ? 'block' : 'none';
            applyFilters();
            showSuggestions(val.trim());
        }}

        function clearSearch() {{
            document.getElementById('search-input').value = '';
            document.getElementById('search-clear').style.display = 'none';
            document.getElementById('search-suggestions').style.display = 'none';
            suggestionIndex = -1;
            applyFilters();
        }}

        function showSuggestions(query) {{
            const box = document.getElementById('search-suggestions');
            if (!mapData || query.length < 1) {{ box.style.display = 'none'; return; }}
            const q = query.toLowerCase();
            // Deduplizierte Vorschlagsliste
            const seen = new Set();
            const matches = mapData.locations.filter(l => {{
                const key = l.name.toLowerCase() + '|' + l.type;
                if (seen.has(key)) return false;
                if (!l.name.toLowerCase().includes(q) && !(l.region || '').toLowerCase().includes(q)) return false;
                seen.add(key);
                return true;
            }}).slice(0, 10);

            if (matches.length === 0) {{ box.style.display = 'none'; return; }}

            box.innerHTML = matches.map((l, i) => `
                <div class="suggestion-item" data-index="${{i}}" data-name="${{l.name}}" data-lat="${{l.lat}}" data-lon="${{l.lon}}" data-type="${{l.type}}">
                    <span class="suggestion-type">${{TYPE_ICONS[l.type] || '📍'}}</span>
                    <div>
                        <div class="suggestion-name">${{l.name}}</div>
                        <div class="suggestion-meta">${{TYPE_LABELS[l.type] || l.type}} · ${{l.region}}${{l.country && l.country !== 'Schottland' ? ', ' + l.country : ''}}</div>
                    </div>
                </div>
            `).join('');
            box.style.display = 'block';
            suggestionIndex = -1;

            box.querySelectorAll('.suggestion-item').forEach(item => {{
                item.addEventListener('click', () => selectSuggestion(item));
                item.addEventListener('mouseenter', () => {{
                    box.querySelectorAll('.suggestion-item').forEach(s => s.classList.remove('active'));
                    item.classList.add('active');
                    suggestionIndex = parseInt(item.dataset.index);
                }});
            }});
        }}

        function selectSuggestion(item) {{
            const name = item.dataset.name;
            const lat = parseFloat(item.dataset.lat);
            const lon = parseFloat(item.dataset.lon);
            document.getElementById('search-input').value = name;
            document.getElementById('search-clear').style.display = 'block';
            document.getElementById('search-suggestions').style.display = 'none';
            suggestionIndex = -1;
            applyFilters();
            // Karte auf Location zoomen
            map.setView([lat, lon], 13);
            setTimeout(() => {{
                const marker = allMarkers.find(m => m._locData.name.toLowerCase() === name.toLowerCase());
                if (marker) markerCluster.zoomToShowLayer(marker, () => marker.openPopup());
            }}, 300);
        }}

        function handleSearchKey(e) {{
            const box = document.getElementById('search-suggestions');
            const items = box.querySelectorAll('.suggestion-item');
            if (!items.length || box.style.display === 'none') return;
            if (e.key === 'ArrowDown') {{
                e.preventDefault();
                suggestionIndex = Math.min(suggestionIndex + 1, items.length - 1);
            }} else if (e.key === 'ArrowUp') {{
                e.preventDefault();
                suggestionIndex = Math.max(suggestionIndex - 1, 0);
            }} else if (e.key === 'Enter' && suggestionIndex >= 0) {{
                e.preventDefault();
                selectSuggestion(items[suggestionIndex]);
                return;
            }} else if (e.key === 'Escape') {{
                box.style.display = 'none'; return;
            }}
            items.forEach((it, i) => it.classList.toggle('active', i === suggestionIndex));
        }}

        // Klick außerhalb schließt Vorschläge
        document.addEventListener('click', e => {{
            const inp = document.getElementById('search-input');
            const box = document.getElementById('search-suggestions');
            if (box && inp && !box.contains(e.target) && e.target !== inp) {{
                box.style.display = 'none';
            }}
        }});

        // Filter-Events
        ['filter-year', 'filter-region', 'filter-country'].forEach(id => {{
            document.getElementById(id).addEventListener('change', applyFilters);
        }});
        ['toggle-distillery', 'toggle-poi'].forEach(id => {{
            document.getElementById(id).addEventListener('change', applyFilters);
        }});

        // URL-Parameter verarbeiten
        // Funktionen global verfügbar machen (für inline onclick/oninput)
        window.handleSearchInput = handleSearchInput;
        window.handleSearchKey = handleSearchKey;
        window.clearSearch = clearSearch;
        window.applyFilters = applyFilters;

        function handleUrlParams() {{
            const params = new URLSearchParams(window.location.search);
            if (params.get('year')) {{
                document.getElementById('filter-year').value = params.get('year');
                applyFilters();
            }}
            if (params.get('region')) {{
                document.getElementById('filter-region').value = params.get('region');
                applyFilters();
            }}
            if (params.get('loc')) {{
                const locId = params.get('loc');
                const marker = allMarkers.find(m => m._locData.id === locId);
                if (marker) {{
                    map.setView(marker.getLatLng(), 13);
                    setTimeout(() => {{
                        markerCluster.zoomToShowLayer(marker, () => marker.openPopup());
                    }}, 500);
                }}
            }}
            if (params.get('highlight')) {{
                const slug = params.get('highlight');
                const locs = mapData.locations.filter(l => l.articles && l.articles.includes(slug));
                if (locs.length > 0) {{
                    const bounds = L.latLngBounds(locs.map(l => [l.lat, l.lon]));
                    map.fitBounds(bounds.pad(0.3));
                    setTimeout(() => {{
                        locs.forEach(l => {{
                            const m = allMarkers.find(mk => mk._locData.id === l.id);
                            if (m) m.openPopup();
                        }});
                    }}, 500);
                }}
            }}
        }}
    }})();
    </script>"""

    breadcrumb_ld = _json_ld_breadcrumb([
        ("Startseite", "/"),
        ("Karte", "/karte.html"),
    ], base_url)
    return _base_template().format(
        title="Karte",
        site_name=site_name,
        meta_description="Interaktive Karte aller Destillerien, Reiseziele und Orte aus dem Whisky Magazin",
        keywords="Whisky Karte, Destillerien Schottland, Reisekarte, Whisky Trail",
        og_description="18 Jahre Whisky-Reisen auf einer interaktiven Karte: Destillerien, Städte und Routen",
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/karte.html",
        base_url=base_url,
        content=content,
        json_ld=breadcrumb_ld,
    )


def _push_to_v2_repo(project_dir):
    """Pusht die gebaute site-v2/ direkt aus dem Projektverzeichnis nach GitHub."""
    try:
        repo_str = str(project_dir)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        subprocess.run(
            ["git", "-C", repo_str, "add", "site-v2/"],
            check=True, capture_output=True
        )
        result = subprocess.run(
            ["git", "-C", repo_str, "commit", "-m", f"build: Site-Rebuild {timestamp}"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            subprocess.run(["git", "-C", repo_str, "push"], check=True, capture_output=True)
            print(f"  V2 gepusht nach GitHub ({timestamp})")
        else:
            print("  V2: Keine Änderungen zum Pushen.")
    except Exception as e:
        print(f"  WARNUNG: V2 Push fehlgeschlagen: {e}")


def build_about_page(config):
    """Erstellt die Über-uns-Seite."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    content = f"""
    <!-- Über-uns-Seite: h2::before deaktivieren (wird global gesetzt, stört hier) -->
    <style>
        .about-page-wrapper h2::before {{ display: none !important; }}
        .about-page-wrapper h2 {{ padding-left: 0 !important; }}
    </style>
    <div class="about-page-wrapper">

    <!-- ===== HERO ===== -->
    <section style="background:var(--text-primary);color:#fff;padding:80px 24px 64px;text-align:center;position:relative;overflow:hidden;">
        <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 60% 40%,rgba(200,150,62,0.18) 0%,transparent 65%);pointer-events:none;"></div>
        <div style="position:relative;max-width:760px;margin:0 auto;">
            <p style="font-size:12px;letter-spacing:3px;text-transform:uppercase;color:var(--accent-amber);margin:0 0 20px;font-weight:600;">Zwei Freunde. Eine Obsession.</p>
            <h1 style="font-family:'Fraunces',Georgia,serif;font-size:clamp(32px,5vw,52px);font-weight:600;line-height:1.2;margin:0 0 24px;color:#fff;">Irgendwas mit Schottland<span style="color:var(--accent-amber);">.</span></h1>
            <p style="font-size:18px;color:rgba(255,255,255,0.78);line-height:1.7;max-width:620px;margin:0 auto 28px;">
                Steffen &amp; Elmar. Seit 2007 unterwegs zwischen Nebel, Torfrauch und dem besten Whisky der Welt.
                Alles begann mit einem Flug nach Glasgow — und hat seitdem nie wirklich aufgehört.
            </p>
            <div style="display:flex;justify-content:center;gap:16px;flex-wrap:wrap;">
                <a href="{base_url}/karte.html" class="btn btn-primary" style="background:var(--accent-amber);border:none;">Unsere Reisekarte entdecken</a>
                <a href="{base_url}/" class="btn btn-ghost" style="border-color:rgba(255,255,255,0.3);color:rgba(255,255,255,0.85);">Zum Magazin</a>
            </div>
        </div>
    </section>

    <!-- ===== STATS BAND ===== -->
    <section style="background:var(--accent-amber);padding:28px 24px;">
        <div style="max-width:var(--max-width);margin:0 auto;display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:16px;text-align:center;">
            <div>
                <div style="font-family:'Fraunces',serif;font-size:36px;font-weight:600;color:#fff;line-height:1;">18+</div>
                <div style="font-size:12px;color:rgba(255,255,255,0.82);text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Jahre Schottland</div>
            </div>
            <div>
                <div style="font-family:'Fraunces',serif;font-size:36px;font-weight:600;color:#fff;line-height:1;">110</div>
                <div style="font-size:12px;color:rgba(255,255,255,0.82);text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Destillerien besucht</div>
            </div>
            <div>
                <div style="font-family:'Fraunces',serif;font-size:36px;font-weight:600;color:#fff;line-height:1;">201</div>
                <div style="font-size:12px;color:rgba(255,255,255,0.82);text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Orte auf der Karte</div>
            </div>
            <div>
                <div style="font-family:'Fraunces',serif;font-size:36px;font-weight:600;color:#fff;line-height:1;">1</div>
                <div style="font-size:12px;color:rgba(255,255,255,0.82);text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Eigenes Fass</div>
                <div style="font-size:11px;color:rgba(255,255,255,0.65);letter-spacing:0.5px;margin-top:2px;">Glasgow Distillery</div>
            </div>
            <div>
                <div style="font-family:'Fraunces',serif;font-size:36px;font-weight:600;color:#fff;line-height:1;">∞</div>
                <div style="font-size:12px;color:rgba(255,255,255,0.82);text-transform:uppercase;letter-spacing:1px;margin-top:4px;">geleerte Gläser</div>
            </div>
        </div>
    </section>

    <!-- ===== DIE KURZFASSUNG ===== -->
    <section style="max-width:760px;margin:80px auto;padding:0 24px;">
        <p style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent-amber);font-weight:600;margin-bottom:12px;">Die ehrliche Kurzfassung</p>
        <h2 style="font-family:'Fraunces',serif;font-size:32px;font-weight:600;padding-left:0;margin:0 0 24px;line-height:1.3;">
            Wir sind nicht objektiv.<br>
            <span style="color:var(--accent-amber);">Und wir sind stolz drauf.</span>
        </h2>
        <p style="font-size:17px;line-height:1.8;color:var(--text-secondary);margin-bottom:20px;">
            Wenn jemand sagt „Schottland ist kalt und verregnet, was willst du da?", dann wissen wir:
            Der war noch nie auf Islay, wenn die Abendsonne über dem Atlantik versinkt und
            man ein Glas Lagavulin in der Hand hält. Manche Dinge lassen sich nicht erklären.
            Man muss sie einfach erlebt haben.
        </p>
        <p style="font-size:17px;line-height:1.8;color:var(--text-secondary);margin-bottom:20px;">
            Wir schreiben über Schottland, weil wir keine andere Wahl haben. Weil es in uns steckt,
            wie Torf im Whisky — unsichtbar, aber man schmeckt es in jedem Schluck.
            Und weil dieses Land so viel mehr ist als der nächste Bestseller-Reiseführer
            je erahnen könnte.
        </p>
        <blockquote style="font-family:'Fraunces',serif;font-style:italic;font-size:20px;color:var(--text-primary);border-left:4px solid var(--accent-amber);padding:8px 0 8px 24px;margin:32px 0;">
            „Wir kommen jedes Jahr wieder. Nicht trotz des Wetters, sondern — wir würden lügen,
            wenn wir sagten, es liegt nur am Whisky."
        </blockquote>
    </section>

    <!-- ===== WIE ES BEGANN ===== -->
    <section style="background:var(--bg-surface);border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:72px 24px;">
        <div style="max-width:900px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:56px;align-items:start;">
            <div>
                <p style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent-amber);font-weight:600;margin-bottom:12px;">2007 — Der Anfang</p>
                <h2 style="font-family:'Fraunces',serif;font-size:26px;font-weight:600;padding-left:0;margin:0 0 20px;line-height:1.3;">Ein Flug nach Glasgow.<br>Eigentlich wollten wir nur kurz schauen.</h2>
                <p style="font-size:16px;line-height:1.8;color:var(--text-secondary);margin-bottom:16px;">
                    Es war nicht geplant, eine Leidenschaft zu werden. Es war ein Wochenendtrip.
                    Glasgow, ein bisschen Highlands, vielleicht eine Destillerie auf dem Weg.
                    Was dann passierte, nennt man in Fachkreisen „Verliebt sein auf den ersten Dram".
                </p>
                <p style="font-size:16px;line-height:1.8;color:var(--text-secondary);">
                    Seitdem sind wir nicht mehr losgekommen. Jedes Jahr eine neue Route,
                    neue Destillerien, neue Orte — und jedes Jahr das gleiche Gefühl:
                    Schottland ist noch nicht fertig mit uns.
                </p>
            </div>
            <div>
                <p style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent-amber);font-weight:600;margin-bottom:12px;">Heute</p>
                <h2 style="font-family:'Fraunces',serif;font-size:26px;font-weight:600;padding-left:0;margin:0 0 20px;line-height:1.3;">18 Reisen später.<br>Kein Ende in Sicht.</h2>
                <p style="font-size:16px;line-height:1.8;color:var(--text-secondary);margin-bottom:16px;">
                    Islay. Speyside. Orkney. Campbeltown. Highlands. Kentucky.
                    Dublin. Berlin. Manchmal hört eine Reise mit Whisky-Bezug
                    nicht an der Landesgrenze auf.
                </p>
                <p style="font-size:16px;line-height:1.8;color:var(--text-secondary);">
                    110+ besuchte Destillerien, 201 Orte auf unserer interaktiven Karte,
                    über {len(load_all_articles())} Artikel und ein absolut nicht behandelbares Verlangen nach dem
                    nächsten Trip. Die Ärzte sagen, es gibt keine Heilung.
                    Wir sagen: Gut so.
                </p>
            </div>
        </div>
    </section>

    <!-- ===== DIE PERSONEN ===== -->
    <section style="max-width:900px;margin:80px auto;padding:0 24px;">
        <p style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent-amber);font-weight:600;margin-bottom:12px;text-align:center;">Wer steckt dahinter</p>
        <h2 style="font-family:'Fraunces',serif;font-size:28px;font-weight:600;padding-left:0;margin:0 0 48px;text-align:center;line-height:1.3;">Zwei Charaktere.<br>Völlig unterschiedlich. Perfekt ergänzend.</h2>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:40px;">
            <!-- Steffen -->
            <div style="background:var(--bg-elevated);border:1px solid var(--border);border-top:3px solid var(--accent-amber);border-radius:var(--radius-sm);padding:32px;box-shadow:var(--shadow-sm);display:flex;flex-direction:column;">
                <div style="width:56px;height:56px;background:var(--bg-surface);border:2px solid var(--accent-amber);border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:20px;flex-shrink:0;">
                    <span style="font-family:'Fraunces',serif;font-size:22px;font-weight:600;color:var(--accent-amber);line-height:1;">S</span>
                </div>
                <h3 style="font-family:'Fraunces',serif;font-size:22px;font-weight:600;margin:0 0 4px;padding-left:0;">Steffen</h3>
                <p style="font-size:12px;color:var(--accent-amber);text-transform:uppercase;letter-spacing:1.5px;font-weight:600;margin:0 0 16px;">Der Geschichtenerzähler</p>
                <p style="font-size:15px;line-height:1.7;color:var(--text-secondary);margin-bottom:14px;">
                    Steffen schreibt. Fotografiert. Denkt zu lange über Tasting Notes nach.
                    Hat mindestens dreimal pro Jahr den gleichen Streit: „Lagavulin 16 oder Ardbeg Uigeadail?"
                    — und beides schon zu oft verloren.
                </p>
                <p style="font-size:15px;line-height:1.7;color:var(--text-secondary);margin-bottom:20px;">
                    Hinter dem Blog steckt sein Bedürfnis, Erlebnisse nicht zu vergessen.
                    Das Notizbuch war zu klein, die Fotos zu viele — also wurde es ein Magazin.
                    Persönlich, ehrlich, und manchmal etwas zu ausführlich. Aber das liegt am Whisky.
                </p>
                <div style="margin-top:auto;padding-top:20px;border-top:1px solid var(--border);">
                    <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;margin:0 0 12px;">
                        Willst du mehr Stories direkt in dein Postfach? Dann ist unser Newsletter genau das Richtige.
                    </p>
                    <a href="#newsletter" onclick="document.querySelector('[data-newsletter]').scrollIntoView({{behavior:'smooth'}});return false;"
                       style="display:inline-block;font-size:13px;font-weight:600;color:var(--accent-amber);text-decoration:none;border:1.5px solid var(--accent-amber);border-radius:var(--radius-sm);padding:8px 16px;">
                        Newsletter abonnieren →
                    </a>
                </div>
            </div>

            <!-- Elmar -->
            <div style="background:var(--bg-elevated);border:1px solid var(--border);border-top:3px solid var(--accent-sage);border-radius:var(--radius-sm);padding:32px;box-shadow:var(--shadow-sm);display:flex;flex-direction:column;">
                <div style="width:56px;height:56px;background:var(--bg-surface);border:2px solid var(--accent-sage);border-radius:50%;display:flex;align-items:center;justify-content:center;margin-bottom:20px;flex-shrink:0;">
                    <span style="font-family:'Fraunces',serif;font-size:22px;font-weight:600;color:var(--accent-sage);line-height:1;">E</span>
                </div>
                <h3 style="font-family:'Fraunces',serif;font-size:22px;font-weight:600;margin:0 0 4px;padding-left:0;">Elmar</h3>
                <p style="font-size:12px;color:var(--accent-sage);text-transform:uppercase;letter-spacing:1.5px;font-weight:600;margin:0 0 16px;">Der Reiseprofi · Reisekaufmann</p>
                <p style="font-size:15px;line-height:1.7;color:var(--text-secondary);margin-bottom:14px;">
                    Elmars Leidenschaft für Schottland ist genauso groß wie Steffens —
                    aber er hat sie professionalisiert. Als ausgebildeter Reisekaufmann
                    weiß er nicht nur, <em>wo</em> es hingeht, sondern auch <em>wie</em>
                    man dort ankommt, ohne dreimal umzusteigen und die Fähre zu verpassen.
                </p>
                <p style="font-size:15px;line-height:1.7;color:var(--text-secondary);margin-bottom:20px;">
                    Ob Fähre nach Islay, Mietwagen für die NC500 oder das abgelegene B&amp;B
                    auf Jura, von dem kein Algorithmus je gehört hat — Elmar findet es.
                    Und wenn es irgendwo Probleme gibt, löst er die, bevor der erste
                    Tasting Dram eiskalt wird.
                </p>
                <div style="margin-top:auto;padding-top:20px;border-top:1px solid var(--border);">
                    <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;margin:0 0 12px;">
                        Du planst eine Schottland-Reise und willst mehr als 08/15? Elmar hilft dir,
                        die Route zu finden, die kein Reisebüro kennt.
                    </p>
                    <a href="mailto:rosenhefter@gmail.com?subject=Schottland-Reiseplanung"
                       style="display:inline-block;font-size:13px;font-weight:600;color:var(--accent-sage);text-decoration:none;border:1.5px solid var(--accent-sage);border-radius:var(--radius-sm);padding:8px 16px;">
                        Kontakt für Reiseplanung →
                    </a>
                </div>
            </div>
        </div>
    </section>

    <!-- ===== FOTO: FETTERCAIRN ===== -->
    <section style="max-width:900px;margin:0 auto 80px;padding:0 24px;">
        <figure style="margin:0;border-radius:var(--radius-sm);overflow:hidden;box-shadow:var(--shadow-hover);position:relative;">
            <img src="/images/steffen-elmar-fettercairn.jpg"
                 alt="Steffen und Elmar bei der Fettercairn Destillerie – Tasting mit dem Master Distiller"
                 style="width:100%;max-height:480px;object-fit:cover;display:block;">
            <figcaption style="background:rgba(26,26,26,0.82);color:rgba(255,255,255,0.85);font-size:13px;padding:10px 16px;font-family:'Inter',sans-serif;display:flex;justify-content:space-between;align-items:center;">
                <span>🥃 Tasting im Lagerhaus der Fettercairn Distillery — eines dieser unvergesslichen Momente.</span>
                <span style="color:var(--accent-amber);font-weight:500;">Fettercairn, Highlands</span>
            </figcaption>
        </figure>
        <p style="font-size:15px;color:var(--text-secondary);line-height:1.7;margin-top:20px;font-style:italic;">
            Das ist der Moment, für den wir reisen: direkt vor Ort, gemeinsam mit dem Master Distiller,
            einem Blender oder dem Destillery Manager. Nicht durch eine Glasscheibe, nicht auf einem
            Gruppenrundgang. Sondern echte Gespräche, echte Einblicke — und natürlich: der beste
            Whisky aus dem Fass. Fettercairn ist nur ein Beispiel. Unsere Karte zeigt 110 weitere.
        </p>
    </section>

    <!-- ===== MEHR ALS NUR WHISKY ===== -->
    <section style="background:var(--text-primary);padding:72px 24px;color:#fff;">
        <div style="max-width:900px;margin:0 auto;">
            <p style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent-amber);font-weight:600;margin-bottom:12px;text-align:center;">Das Größere Bild</p>
            <h2 style="font-family:'Fraunces',serif;font-size:30px;font-weight:600;color:#fff;padding-left:0;margin:0 0 20px;text-align:center;line-height:1.3;">
                Schottland ist mehr als Whisky.<br>
                <span style="color:var(--accent-amber);">Aber Whisky macht es perfekt.</span>
            </h2>
            <p style="font-size:17px;line-height:1.8;color:rgba(255,255,255,0.75);max-width:680px;margin:0 auto 40px;text-align:center;">
                Natürlich. Der Whisky ist das Herz. Aber Schottland hat noch vieles mehr,
                das man nicht im Reiseführer findet.
            </p>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:24px;">
                <div style="background:rgba(255,255,255,0.06);border-radius:var(--radius-sm);padding:24px;border:1px solid rgba(255,255,255,0.1);">
                    <div style="font-size:28px;margin-bottom:12px;">🏰</div>
                    <h4 style="font-family:'Fraunces',serif;font-size:16px;color:#fff;margin:0 0 8px;padding-left:0;">Geschichte &amp; Burgen</h4>
                    <p style="font-size:14px;color:rgba(255,255,255,0.65);line-height:1.6;margin:0;">Eilean Donan im Morgengrauen. Stirling Castle ohne Touristenmassen. Die Orte, bei denen man plötzlich versteht, warum Schotten so sind wie sie sind.</p>
                </div>
                <div style="background:rgba(255,255,255,0.06);border-radius:var(--radius-sm);padding:24px;border:1px solid rgba(255,255,255,0.1);">
                    <div style="font-size:28px;margin-bottom:12px;">🌊</div>
                    <h4 style="font-family:'Fraunces',serif;font-size:16px;color:#fff;margin:0 0 8px;padding-left:0;">Küsten &amp; Natur</h4>
                    <p style="font-size:14px;color:rgba(255,255,255,0.65);line-height:1.6;margin:0;">Die NC500 in Herbstfarben. Islay bei Sturm. Orkney, wo die Welt aufhört. Momente, die man nicht fotografieren kann — aber trotzdem versucht.</p>
                </div>
                <div style="background:rgba(255,255,255,0.06);border-radius:var(--radius-sm);padding:24px;border:1px solid rgba(255,255,255,0.1);">
                    <div style="font-size:28px;margin-bottom:12px;">🍺</div>
                    <h4 style="font-family:'Fraunces',serif;font-size:16px;color:#fff;margin:0 0 8px;padding-left:0;">Pub-Kultur &amp; Menschen</h4>
                    <p style="font-size:14px;color:rgba(255,255,255,0.65);line-height:1.6;margin:0;">Im Pub in Bowmore um 22 Uhr mit Einheimischen über Football diskutieren. Das ist Schottland. Das kann kein Reiseführer ersetzen.</p>
                </div>
                <div style="background:rgba(255,255,255,0.06);border-radius:var(--radius-sm);padding:24px;border:1px solid rgba(255,255,255,0.1);">
                    <div style="font-size:28px;margin-bottom:12px;">⚽</div>
                    <h4 style="font-family:'Fraunces',serif;font-size:16px;color:#fff;margin:0 0 8px;padding-left:0;">Football &amp; Highland Games</h4>
                    <p style="font-size:14px;color:rgba(255,255,255,0.65);line-height:1.6;margin:0;">Celtic Park. Schottische Highland Games. Wir haben beides erlebt — mit dem gebührenden Respekt vor allem, was dazugehört. Und dem richtigen Dram danach.</p>
                </div>
                <div style="background:rgba(255,255,255,0.06);border-radius:var(--radius-sm);padding:24px;border:1px solid rgba(255,255,255,0.1);">
                    <div style="font-size:28px;margin-bottom:12px;">🍽️</div>
                    <h4 style="font-family:'Fraunces',serif;font-size:16px;color:#fff;margin:0 0 8px;padding-left:0;">Küche &amp; Kulinarik</h4>
                    <p style="font-size:14px;color:rgba(255,255,255,0.65);line-height:1.6;margin:0;">Schottische Küche ist mehr als Haggis. Seafood auf Islay. Frühstück im B&amp;B. Käse vom Markt. Wir haben uns durch das Land gegessen — mit Hingabe.</p>
                </div>
                <div style="background:rgba(255,255,255,0.06);border-radius:var(--radius-sm);padding:24px;border:1px solid rgba(255,255,255,0.1);">
                    <div style="font-size:28px;margin-bottom:12px;">🗺️</div>
                    <h4 style="font-family:'Fraunces',serif;font-size:16px;color:#fff;margin:0 0 8px;padding-left:0;">Abseits der Touristenpfade</h4>
                    <p style="font-size:14px;color:rgba(255,255,255,0.65);line-height:1.6;margin:0;">Das B&amp;B auf Jura mit drei Zimmern. Die Destillerie, die keiner kennt. Das Tal ohne Namen auf Google Maps. Das sind die Momente, für die wir reisen.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- ===== WAS WIR ANBIETEN ===== -->
    <section style="max-width:900px;margin:80px auto;padding:0 24px;">
        <p style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent-amber);font-weight:600;margin-bottom:12px;text-align:center;">Was du von uns bekommst</p>
        <h2 style="font-family:'Fraunces',serif;font-size:28px;font-weight:600;padding-left:0;margin:0 0 40px;text-align:center;line-height:1.3;">Leidenschaft plus Professionalität.<br>Kein Standard. Keine Copy-Paste-Routen.</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:32px;">
            <div style="display:flex;gap:16px;">
                <div style="font-size:24px;flex-shrink:0;">📖</div>
                <div>
                    <h4 style="font-family:'Fraunces',serif;font-size:17px;margin:0 0 8px;padding-left:0;">Ehrliche Reiseberichte</h4>
                    <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;margin:0;">Keine Pressereisen, keine gesponserten Touren. Was wir schreiben, haben wir selbst erlebt — mit eigenem Geld, eigenem Rucksack und eigenem Urteil.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;">
                <div style="font-size:24px;flex-shrink:0;">🥃</div>
                <div>
                    <h4 style="font-family:'Fraunces',serif;font-size:17px;margin:0 0 8px;padding-left:0;">Whisky-Wissen ohne Schnickschnack</h4>
                    <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;margin:0;">Tasting Notes für Menschen, die Whisky trinken — nicht für Weinprüfer-Imitate. Destillerie-Portraits, die zeigen was dahinter steckt. Empfehlungen, die wir selbst kaufen würden.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;">
                <div style="font-size:24px;flex-shrink:0;">🧭</div>
                <div>
                    <h4 style="font-family:'Fraunces',serif;font-size:17px;margin:0 0 8px;padding-left:0;">Reiseplanung mit Tiefgang</h4>
                    <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;margin:0;">Dank Elmars professionellem Hintergrund als Reisekaufmann bekommst du hier nicht nur Inspiration, sondern auch fundiertes Wissen über Routen, Logistik und die kleinen Dinge, die den Unterschied machen.</p>
                </div>
            </div>
            <div style="display:flex;gap:16px;">
                <div style="font-size:24px;flex-shrink:0;">💡</div>
                <div>
                    <h4 style="font-family:'Fraunces',serif;font-size:17px;margin:0 0 8px;padding-left:0;">Für jede Idee eine Lösung</h4>
                    <p style="font-size:14px;color:var(--text-secondary);line-height:1.6;margin:0;">„Geht nicht" kommt uns selten über die Lippen. Schottland bietet für jeden Typ Reisenden etwas — ob Whisky-Pilgrim, Naturfreund, Geschichts-Nerd oder Foodie. Wir finden den passenden Weg.</p>
                </div>
            </div>
        </div>
    </section>

    <!-- ===== CTA SECTION ===== -->
    <section id="newsletter" style="background:var(--bg-surface);border-top:1px solid var(--border);padding:72px 24px;text-align:center;">
        <div style="max-width:600px;margin:0 auto;">
            <div style="font-size:48px;margin-bottom:20px;">🥃</div>
            <h2 style="font-family:'Fraunces',serif;font-size:28px;font-weight:600;padding-left:0;margin:0 0 16px;line-height:1.3;">Komm mit auf die Reise.</h2>
            <p style="font-size:17px;color:var(--text-secondary);line-height:1.7;margin:0 0 32px;">
                Einmal im Monat teilen wir unsere besten Geschichten, Tipps und Empfehlungen.
                Kein Spam. Kein Algorithmus. Nur zwei Typen, die zu viel über Schottland nachgedacht haben.
            </p>
            <div style="display:flex;flex-direction:column;gap:16px;align-items:center;">
                <form class="newsletter-form" style="display:flex;gap:8px;width:100%;max-width:420px;">
                    <input type="email" placeholder="Deine E-Mail-Adresse" required
                        style="flex:1;padding:12px 16px;border:1.5px solid var(--border);border-radius:var(--radius-sm);font-size:15px;font-family:'Inter',sans-serif;background:var(--bg-elevated);">
                    <button type="submit" class="btn btn-primary">Dabei sein</button>
                </form>
                <p style="font-size:13px;color:var(--accent-muted);">Jederzeit abbestellbar. Versprochen.</p>
            </div>
            <div style="display:flex;justify-content:center;gap:20px;margin-top:32px;flex-wrap:wrap;">
                <a href="{base_url}/karte.html" style="font-size:14px;color:var(--accent-amber);text-decoration:none;font-weight:500;">🗺️ Unsere Reisekarte →</a>
                <a href="{base_url}/kategorie/whisky.html" style="font-size:14px;color:var(--accent-amber);text-decoration:none;font-weight:500;">🥃 Alle Whisky-Artikel →</a>
                <a href="{base_url}/kategorie/reise.html" style="font-size:14px;color:var(--accent-amber);text-decoration:none;font-weight:500;">✈️ Alle Reise-Artikel →</a>
            </div>
        </div>
    </section>

    </div><!-- /.about-page-wrapper -->
    """

    return _base_template().format(
        title="Über uns",
        site_name=site_name,
        meta_description="Steffen & Elmar – zwei Freunde, eine Obsession. Seit 2007 unterwegs in Schottland, 110 besuchte Destillerien und kein Ende in Sicht.",
        keywords="Über uns, Steffen, Elmar, Schottland, Whisky, Reise",
        og_description="Wer hinter dem Whisky Magazin steckt – und warum Schottland uns nie wieder losgelassen hat.",
        og_image="",
        canonical_url=f"{base_url}/ueber-uns.html",
        base_url=base_url,
        content=content,
        json_ld="",
    )


def build_impressum_page(config):
    """Erstellt die Impressum-Seite (gesetzlich vorgeschrieben in DE)."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    content = """
    <style>
        .legal-page h2::before { display: none !important; }
        .legal-page h2 { padding-left: 0 !important; font-size: 22px; margin-top: 40px; }
        .legal-page h3 { padding-left: 0; font-size: 18px; margin-top: 28px; }
    </style>
    <nav class="breadcrumb"><div class="breadcrumb-inner"><a href="/">Startseite</a> &rsaquo; Impressum</div></nav>
    <div class="legal-page" style="max-width:var(--article-max);margin:48px auto;padding:0 24px 64px;">
        <h1 style="font-family:'Fraunces',serif;font-size:32px;font-weight:600;margin:0 0 32px;">Impressum</h1>

        <h2>Angaben gem&auml;&szlig; &sect; 5 TMG</h2>
        <p>
            Steffen Hefter<br>
            Wilhelm-Schrader-Stra&szlig;e 27A<br>
            06120 Halle (Saale)
        </p>

        <h2>Kontakt</h2>
        <p>
            E-Mail: rosenhefter@gmail.com
        </p>

        <h2>Verantwortlich f&uuml;r den Inhalt nach &sect; 55 Abs. 2 RSt V</h2>
        <p>
            Steffen Hefter<br>
            Wilhelm-Schrader-Stra&szlig;e 27A, 06120 Halle (Saale)
        </p>

        <h2>Haftung f&uuml;r Inhalte</h2>
        <p>Als Diensteanbieter sind wir gem&auml;&szlig; &sect; 7 Abs.1 TMG f&uuml;r eigene Inhalte auf diesen
        Seiten nach den allgemeinen Gesetzen verantwortlich. Nach &sect;&sect; 8 bis 10 TMG sind wir als
        Diensteanbieter jedoch nicht verpflichtet, &uuml;bermittelte oder gespeicherte fremde Informationen
        zu &uuml;berwachen oder nach Umst&auml;nden zu forschen, die auf eine rechtswidrige T&auml;tigkeit hinweisen.</p>
        <p>Verpflichtungen zur Entfernung oder Sperrung der Nutzung von Informationen nach den allgemeinen
        Gesetzen bleiben hiervon unber&uuml;hrt. Eine diesbez&uuml;gliche Haftung ist jedoch erst ab dem
        Zeitpunkt der Kenntnis einer konkreten Rechtsverletzung m&ouml;glich. Bei Bekanntwerden von
        entsprechenden Rechtsverletzungen werden wir diese Inhalte umgehend entfernen.</p>

        <h2>Haftung f&uuml;r Links</h2>
        <p>Unser Angebot enth&auml;lt Links zu externen Websites Dritter, auf deren Inhalte wir keinen
        Einfluss haben. Deshalb k&ouml;nnen wir f&uuml;r diese fremden Inhalte auch keine Gew&auml;hr
        &uuml;bernehmen. F&uuml;r die Inhalte der verlinkten Seiten ist stets der jeweilige Anbieter oder
        Betreiber der Seiten verantwortlich. Die verlinkten Seiten wurden zum Zeitpunkt der Verlinkung
        auf m&ouml;gliche Rechtsverst&ouml;&szlig;e &uuml;berpr&uuml;ft. Rechtswidrige Inhalte waren zum
        Zeitpunkt der Verlinkung nicht erkennbar.</p>

        <h2>Urheberrecht</h2>
        <p>Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen dem
        deutschen Urheberrecht. Die Vervielf&auml;ltigung, Bearbeitung, Verbreitung und jede Art der
        Verwertung au&szlig;erhalb der Grenzen des Urheberrechtes bed&uuml;rfen der schriftlichen Zustimmung
        des jeweiligen Autors bzw. Erstellers.</p>

        <h2>Affiliate-Hinweis</h2>
        <p>Diese Website enth&auml;lt sogenannte Affiliate-Links. Wenn du &uuml;ber einen solchen Link ein
        Produkt kaufst oder eine Dienstleistung buchst, erhalten wir eine kleine Provision. F&uuml;r dich
        entstehen dabei keine Mehrkosten. Wir empfehlen ausschlie&szlig;lich Produkte und Services, von
        denen wir selbst &uuml;berzeugt sind.</p>
        <p>Wir nehmen am Amazon Associates Partnerprogramm teil (Tag: whiskyreise74-21).</p>
    </div>
    """

    html = _base_template().format(
        title="Impressum",
        site_name=site_name,
        meta_description="Impressum des Whisky Magazin – Angaben gemäß § 5 TMG.",
        keywords="Impressum, Whisky Magazin, Kontakt",
        og_description="Impressum des Whisky Magazin",
        og_image="",
        canonical_url=f"{base_url}/impressum.html",
        base_url=base_url,
        content=content,
        json_ld="",
    )
    # Impressum soll nicht indexiert werden
    return html.replace(
        '<meta name="viewport"',
        '<meta name="robots" content="noindex, follow">\n    <meta name="viewport"',
        1,
    )


def build_datenschutz_page(config):
    """Erstellt die Datenschutz-Seite (DSGVO-konform)."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    content = """
    <style>
        .legal-page h2::before { display: none !important; }
        .legal-page h2 { padding-left: 0 !important; font-size: 22px; margin-top: 40px; }
        .legal-page h3 { padding-left: 0; font-size: 18px; margin-top: 28px; }
    </style>
    <nav class="breadcrumb"><div class="breadcrumb-inner"><a href="/">Startseite</a> &rsaquo; Datenschutz</div></nav>
    <div class="legal-page" style="max-width:var(--article-max);margin:48px auto;padding:0 24px 64px;">
        <h1 style="font-family:'Fraunces',serif;font-size:32px;font-weight:600;margin:0 0 32px;">Datenschutzerkl&auml;rung</h1>

        <h2>1. Datenschutz auf einen Blick</h2>
        <h3>Allgemeine Hinweise</h3>
        <p>Die folgenden Hinweise geben einen einfachen &Uuml;berblick dar&uuml;ber, was mit deinen
        personenbezogenen Daten passiert, wenn du diese Website besuchst. Personenbezogene Daten sind
        alle Daten, mit denen du pers&ouml;nlich identifiziert werden kannst.</p>

        <h3>Datenerfassung auf dieser Website</h3>
        <p><strong>Wer ist verantwortlich f&uuml;r die Datenerfassung auf dieser Website?</strong><br>
        Die Datenverarbeitung auf dieser Website erfolgt durch den Websitebetreiber. Dessen Kontaktdaten
        kannst du dem <a href="/impressum.html">Impressum</a> dieser Website entnehmen.</p>

        <h2>2. Hosting</h2>
        <p>Diese Website wird bei <strong>Vercel Inc.</strong> (340 S Lemon Ave #4133, Walnut, CA 91789, USA) gehostet.
        Wenn du unsere Website besuchst, werden deine Daten auf Servern von Vercel verarbeitet.
        Hierbei k&ouml;nnen insbesondere deine IP-Adresse und der Zeitpunkt des Seitenaufrufs
        gespeichert werden.</p>
        <p>Der Einsatz von Vercel erfolgt im Interesse einer sicheren, schnellen und effizienten
        Bereitstellung unseres Online-Angebots (Art. 6 Abs. 1 lit. f DSGVO). Vercel hat
        Standardvertragsklauseln (Standard Contractual Clauses, SCC) der EU-Kommission als Grundlage
        f&uuml;r die Daten&uuml;bertragung in Drittl&auml;nder implementiert.</p>

        <h2>3. Google Fonts</h2>
        <p>Diese Seite nutzt zur einheitlichen Darstellung von Schriftarten sogenannte Google Fonts,
        die von <strong>Google LLC</strong> (1600 Amphitheatre Parkway, Mountain View, CA 94043, USA) bereitgestellt werden.
        Beim Aufruf einer Seite l&auml;dt dein Browser die ben&ouml;tigten Schriftarten (Fraunces und Inter)
        direkt von Google-Servern in deinen Browser-Cache.</p>
        <p>Dabei wird deine IP-Adresse an Google &uuml;bermittelt. Es ist nicht auszuschlie&szlig;en,
        dass Google diese Daten auch an Server in den USA &uuml;bertr&auml;gt.</p>
        <p>Die Nutzung von Google Fonts erfolgt auf Grundlage von Art. 6 Abs. 1 lit. f DSGVO.
        Wir haben ein berechtigtes Interesse an der einheitlichen Darstellung der Schriftarten
        auf unserer Website.</p>
        <p>Weitere Informationen findest du in der
        <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Datenschutzerkl&auml;rung von Google</a>.</p>

        <h2>4. Newsletter (Brevo)</h2>
        <p>Wenn du unseren Newsletter abonnierst, wird deine E-Mail-Adresse bei <strong>Brevo (ehemals Sendinblue)</strong>
        gespeichert und verarbeitet. Brevo ist ein Dienst der Sendinblue GmbH, K&ouml;penicker Stra&szlig;e 126,
        10179 Berlin, Deutschland.</p>
        <p>Rechtsgrundlage f&uuml;r die Verarbeitung deiner Daten ist deine Einwilligung (Art. 6 Abs. 1
        lit. a DSGVO). Du kannst deine Einwilligung jederzeit widerrufen, indem du dich vom Newsletter
        abmeldest. Die Rechtm&auml;&szlig;igkeit der bis zum Widerruf erfolgten Datenverarbeitung bleibt
        vom Widerruf unber&uuml;hrt.</p>

        <h2>5. Affiliate-Links und Cookies</h2>
        <p>Diese Website enth&auml;lt Affiliate-Links zu folgenden Partnerprogrammen:</p>
        <ul style="margin:12px 0;padding-left:24px;">
            <li><strong>Amazon Associates</strong> (Amazon EU S.&agrave;r.l., 38 Avenue John F. Kennedy, L-1855 Luxemburg) &ndash;
            Beim Klick auf Amazon-Links wird ein Cookie gesetzt, das deine Eink&auml;ufe unserem
            Partnerkonto zuordnet.</li>
            <li><strong>Tradedoubler</strong> (Tradedoubler AB, Birger Jarlsgatan 57A, 113 56 Stockholm, Schweden) &ndash;
            F&uuml;r Reise-Affiliate-Links (F&auml;hren, Fl&uuml;ge etc.).</li>
            <li><strong>Booking.com</strong> (Booking.com B.V., Herengracht 597, 1017 CE Amsterdam, Niederlande) &ndash;
            F&uuml;r Hotel- und Unterkunfts-Empfehlungen (via whisky.reise).</li>
        </ul>
        <p>Durch das Anklicken dieser Links k&ouml;nnen Cookies der jeweiligen Anbieter gesetzt werden.
        Die Cookies dienen der Zuordnung einer Provision. F&uuml;r dich entstehen keine Mehrkosten.</p>

        <h2>6. Externe Inhalte</h2>
        <h3>Leaflet / OpenStreetMap</h3>
        <p>Unsere Kartenseite nutzt <strong>Leaflet.js</strong> und Kartenkacheln von <strong>OpenStreetMap</strong>
        (OpenStreetMap Foundation, St John&rsquo;s Innovation Centre, Cowley Road, Cambridge, CB4 0WS, UK).
        Beim Laden der Karte werden Kartendaten von OSM-Servern abgerufen. Dabei wird deine IP-Adresse
        &uuml;bermittelt.</p>

        <h2>7. Deine Rechte</h2>
        <p>Du hast jederzeit das Recht auf unentgeltliche Auskunft &uuml;ber deine gespeicherten
        personenbezogenen Daten, deren Herkunft und Empf&auml;nger und den Zweck der Datenverarbeitung
        sowie ein Recht auf Berichtigung oder L&ouml;schung dieser Daten. Hierzu sowie zu weiteren
        Fragen zum Thema Datenschutz kannst du dich jederzeit an uns wenden:</p>
        <p>E-Mail: <a href="mailto:rosenhefter@gmail.com">rosenhefter@gmail.com</a></p>
        <p>Dar&uuml;ber hinaus steht dir ein Beschwerderecht bei der zust&auml;ndigen Aufsichtsbeh&ouml;rde zu.</p>

        <p style="margin-top:40px;font-size:14px;color:var(--text-secondary);">Stand: M&auml;rz 2026</p>
    </div>
    """

    html = _base_template().format(
        title="Datenschutz",
        site_name=site_name,
        meta_description="Datenschutzerklärung des Whisky Magazin – Informationen zur Datenverarbeitung, Google Fonts, Newsletter und Affiliate-Links.",
        keywords="Datenschutz, DSGVO, Whisky Magazin, Datenschutzerklärung",
        og_description="Datenschutzerklärung des Whisky Magazin",
        og_image="",
        canonical_url=f"{base_url}/datenschutz.html",
        base_url=base_url,
        content=content,
        json_ld="",
    )
    # Datenschutz soll nicht indexiert werden
    return html.replace(
        '<meta name="viewport"',
        '<meta name="robots" content="noindex, follow">\n    <meta name="viewport"',
        1,
    )


def build_rss_feed(articles, config):
    """Erstellt einen RSS 2.0 Feed für Content-Distribution."""
    from xml.sax.saxutils import escape
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    tagline = config["site"].get("tagline", "")
    today = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0100")

    items = ""
    for article in articles[:20]:
        slug = article.get("meta", {}).get("slug", "")
        if not slug:
            continue
        title = escape(article.get("title", ""))
        desc = escape(article.get("meta", {}).get("meta_description", ""))
        date = article.get("date", "")
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            pub_date = dt.strftime("%a, %d %b %Y 08:00:00 +0100")
        except Exception:
            pub_date = today
        cat = escape(article.get("category", "Allgemein"))
        link = f"{base_url}/artikel/{slug}.html"
        items += f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <description>{desc}</description>
      <pubDate>{pub_date}</pubDate>
      <category>{cat}</category>
      <guid isPermaLink="true">{link}</guid>
    </item>
"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(site_name)}</title>
    <link>{base_url}</link>
    <description>{escape(tagline)}</description>
    <language>de-de</language>
    <lastBuildDate>{today}</lastBuildDate>
    <atom:link href="{base_url}/feed.xml" rel="self" type="application/rss+xml"/>
{items}  </channel>
</rss>"""


def build_danke_page(config):
    """Erstellt die Danke-Seite nach Newsletter-Bestätigung."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    content = """
    <div style="text-align:center;padding:80px 24px 120px;max-width:600px;margin:0 auto;">
        <div style="margin-bottom:28px;">
            <img src="/images/authors-steffen-elmar.jpg"
                 alt="Steffen und Elmar – Whisky Magazin"
                 style="width:160px;height:160px;border-radius:50%;object-fit:cover;border:4px solid var(--accent-amber);box-shadow:0 4px 16px rgba(0,0,0,0.12);">
        </div>
        <h1 style="font-family:'Fraunces',serif;font-size:36px;font-weight:700;margin-bottom:16px;color:var(--text-primary);">
            Willkommen an Bord!
        </h1>
        <h2 style="display:none;"></h2>
        <p style="font-size:18px;color:var(--text-secondary);line-height:1.8;margin-bottom:12px;">
            Danke f&uuml;r deine Anmeldung zum Whisky Magazin Newsletter.
        </p>
        <p style="font-size:16px;color:var(--text-secondary);line-height:1.7;margin-bottom:40px;">
            Ab sofort erh&auml;ltst du einmal im Monat die besten Whisky-Geschichten,
            Reise-Tipps und Destillerie-Empfehlungen direkt in dein Postfach.
            Kein Spam &ndash; versprochen.
        </p>
        <div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;">
            <a href="/" class="btn btn-primary" style="font-size:16px;padding:14px 32px;">Magazin entdecken</a>
            <a href="/karte.html" class="btn btn-ghost" style="font-size:16px;padding:14px 32px;">Whisky-Karte</a>
        </div>
        <p style="font-size:13px;color:var(--accent-muted);margin-top:48px;">
            Du kannst dich jederzeit &uuml;ber den Link in jeder E-Mail abmelden.
        </p>
    </div>
    <script>
    /* Pinterest Lead-Event: Newsletter-Anmeldung als Conversion tracken */
    if (window.pintrk) { pintrk('track', 'lead'); }
    </script>
    """

    return _base_template().format(
        title="Danke f\u00fcr deine Anmeldung",
        site_name=site_name,
        meta_description="Danke f\u00fcr deine Newsletter-Anmeldung beim Whisky Magazin.",
        keywords="Newsletter, Anmeldung, Danke",
        og_description="Danke f\u00fcr deine Newsletter-Anmeldung beim Whisky Magazin.",
        og_image="",
        canonical_url=f"{base_url}/danke.html",
        base_url=base_url,
        content=content,
        json_ld="",
    )


def build_404_page(config):
    """Erstellt eine benutzerdefinierte 404-Fehlerseite."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    content = """
    <div style="text-align:center;padding:80px 24px 120px;max-width:600px;margin:0 auto;">
        <div style="font-size:96px;margin-bottom:16px;opacity:0.8;">🥃</div>
        <h1 style="font-family:'Fraunces',serif;font-size:48px;font-weight:700;margin-bottom:16px;">404</h1>
        <h2 style="font-family:'Fraunces',serif;font-size:22px;font-weight:500;color:var(--text-secondary);margin-bottom:24px;padding-left:0;">
            Dieser Dram wurde leider schon ausgetrunken.
        </h2>
        <h2 style="display:none;"></h2>
        <p style="font-size:16px;color:var(--text-secondary);line-height:1.7;margin-bottom:32px;">
            Die Seite, die du suchst, existiert nicht mehr oder wurde verschoben.
            Aber keine Sorge &ndash; es gibt noch genug Whisky zu entdecken!
        </p>
        <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
            <a href="/" class="btn btn-primary">Zur Startseite</a>
            <a href="/karte.html" class="btn btn-ghost">Zur Whisky-Karte</a>
            <a href="/suche.html" class="btn btn-secondary">Suche</a>
        </div>
    </div>
    """

    return _base_template().format(
        title="Seite nicht gefunden",
        site_name=site_name,
        meta_description="Die angeforderte Seite wurde nicht gefunden.",
        keywords="404, Seite nicht gefunden",
        og_description="Die angeforderte Seite wurde nicht gefunden.",
        og_image="",
        canonical_url=f"{base_url}/404.html",
        base_url=base_url,
        content=content,
        json_ld="",
    )


def build_search_index(articles, config):
    """Erstellt einen JSON-Suchindex für die clientseitige Suche (Lunr.js)."""
    index = []
    for article in articles:
        slug = article.get("meta", {}).get("slug", "")
        if not slug:
            continue
        # Einfachen Text aus HTML extrahieren
        html = article.get("html_content", "")
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()[:500]

        index.append({
            "slug": slug,
            "title": article.get("title", ""),
            "category": article.get("category", "Allgemein"),
            "date": article.get("date", ""),
            "teaser": article.get("meta", {}).get("meta_description", ""),
            "tags": article.get("tags", []),
            "text": text,
            "image": article.get("image_url", ""),
        })
    return json.dumps(index, ensure_ascii=False, indent=None)


def build_search_page(config):
    """Erstellt die Suchseite mit clientseitigem Lunr.js-Index."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    content = """
    <nav class="breadcrumb"><div class="breadcrumb-inner"><a href="/">Startseite</a> &rsaquo; Suche</div></nav>
    <div style="max-width:720px;margin:48px auto;padding:0 24px 64px;">
        <h1 style="font-family:'Fraunces',serif;font-size:32px;font-weight:600;margin:0 0 24px;text-align:center;">Artikel durchsuchen</h1>
        <div style="position:relative;margin-bottom:32px;">
            <input type="text" id="search-input" placeholder="Whisky, Destillerie, Reiseziel…"
                   style="width:100%;padding:14px 20px 14px 48px;border:2px solid var(--border);border-radius:var(--radius-sm);font-family:'Inter',sans-serif;font-size:16px;background:var(--bg-elevated);transition:border-color 0.2s;"
                   onfocus="this.style.borderColor='var(--accent-amber)'" onblur="this.style.borderColor='var(--border)'">
            <span style="position:absolute;left:16px;top:50%;transform:translateY(-50%);font-size:20px;color:var(--text-secondary);pointer-events:none;">&#128269;</span>
        </div>
        <div id="search-results" style="min-height:200px;"></div>
    </div>
    <script>
    (function(){
        var idx=null, docs=[];
        fetch('/data/search-index.json')
            .then(function(r){return r.json()})
            .then(function(data){
                docs=data;
            });

        var input=document.getElementById('search-input');
        var results=document.getElementById('search-results');

        function esc(t){var d=document.createElement('div');d.textContent=t;return d.innerHTML;}

        function render(matches){
            if(!matches.length){
                results.innerHTML='<p style="text-align:center;color:var(--text-secondary);padding:40px 0;">Keine Ergebnisse gefunden. Versuche einen anderen Suchbegriff.</p>';
                return;
            }
            var html='';
            matches.forEach(function(doc){
                var safeSlug=esc(doc.slug),safeTitle=esc(doc.title),safeCat=esc(doc.category),safeTeaser=esc(doc.teaser),safeDate=esc(doc.date);
                var imgHtml=doc.image?'<img src="'+esc(doc.image)+'" alt="" style="width:100%;height:160px;object-fit:cover;border-radius:var(--radius-sm) var(--radius-sm) 0 0;">':'';
                html+='<article class="article-card" style="margin-bottom:20px;">'+imgHtml+'<div class="card-body"><div class="card-meta"><span class="cat">'+safeCat+'</span><span>'+safeDate+'</span></div><h2 style="padding-left:0;"><a href="/artikel/'+safeSlug+'.html">'+safeTitle+'</a></h2><p class="teaser">'+safeTeaser+'</p><a href="/artikel/'+safeSlug+'.html" class="read-more">Weiterlesen &rarr;</a></div></article>';
            });
            results.innerHTML=html;
        }

        var timer=null;
        input.addEventListener('input',function(){
            clearTimeout(timer);
            timer=setTimeout(function(){
                var q=input.value.trim().toLowerCase();
                if(q.length<2){results.innerHTML='';return;}
                var matches=docs.filter(function(d){
                    return d.title.toLowerCase().indexOf(q)>=0
                        || d.teaser.toLowerCase().indexOf(q)>=0
                        || d.text.toLowerCase().indexOf(q)>=0
                        || d.category.toLowerCase().indexOf(q)>=0
                        || (d.tags||[]).join(' ').toLowerCase().indexOf(q)>=0;
                });
                render(matches);
            },250);
        });

        // URL-Parameter ?q= auswerten
        var params=new URLSearchParams(location.search);
        var initQ=params.get('q');
        if(initQ){input.value=initQ;input.dispatchEvent(new Event('input'));}
    })();
    </script>
    """

    html = _base_template().format(
        title="Suche",
        site_name=site_name,
        meta_description="Durchsuche alle Whisky-Artikel, Reiseberichte und Destillerie-Empfehlungen im Whisky Magazin.",
        keywords="Suche, Whisky Magazin, Artikel finden",
        og_description="Durchsuche alle Artikel im Whisky Magazin",
        og_image="",
        canonical_url=f"{base_url}/suche.html",
        base_url=base_url,
        content=content,
        json_ld="",
    )
    # Suchergebnisseite soll nicht indexiert werden
    return html.replace(
        '<meta name="viewport"',
        '<meta name="robots" content="noindex, follow">\n    <meta name="viewport"',
        1,
    )


def build_guide_page(config):
    """Erstellt die Lead-Magnet Whisky-Guide Seite."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    content = """
    <div class="hero" style="padding:60px 24px 50px;">
        <h1 style="font-size:2.2em;">Dein kostenloser Whisky-Guide</h1>
        <p>18+ Jahre Erfahrung, 110+ Destillerien &ndash; kompakt für deinen Einstieg in die Welt des Whiskys.</p>
    </div>

    <div style="max-width:720px;margin:48px auto;padding:0 24px 64px;">
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:40px;">
            <div style="background:var(--bg-surface);border-radius:var(--radius-sm);padding:24px;text-align:center;">
                <div style="font-size:32px;margin-bottom:8px;">&#127867;</div>
                <h3 style="font-family:'Fraunces',serif;font-size:16px;margin-bottom:8px;padding-left:0;">Richtig verkosten</h3>
                <p style="font-size:14px;color:var(--text-secondary);">Schritt-für-Schritt-Anleitung: So schmeckst du jeden Tropfen richtig.</p>
            </div>
            <div style="background:var(--bg-surface);border-radius:var(--radius-sm);padding:24px;text-align:center;">
                <div style="font-size:32px;margin-bottom:8px;">&#127759;</div>
                <h3 style="font-family:'Fraunces',serif;font-size:16px;margin-bottom:8px;padding-left:0;">Regionen-Guide</h3>
                <p style="font-size:14px;color:var(--text-secondary);">Von Islay bis Speyside: Was macht jede Region besonders?</p>
            </div>
            <div style="background:var(--bg-surface);border-radius:var(--radius-sm);padding:24px;text-align:center;">
                <div style="font-size:32px;margin-bottom:8px;">&#128176;</div>
                <h3 style="font-family:'Fraunces',serif;font-size:16px;margin-bottom:8px;padding-left:0;">10 Top-Malts unter 50&euro;</h3>
                <p style="font-size:14px;color:var(--text-secondary);">Unsere besten Empfehlungen für Einsteiger und Genießer.</p>
            </div>
            <div style="background:var(--bg-surface);border-radius:var(--radius-sm);padding:24px;text-align:center;">
                <div style="font-size:32px;margin-bottom:8px;">&#9992;&#65039;</div>
                <h3 style="font-family:'Fraunces',serif;font-size:16px;margin-bottom:8px;padding-left:0;">Reise-Checkliste</h3>
                <p style="font-size:14px;color:var(--text-secondary);">Unsere Packliste und Tipps für deine erste Schottland-Whiskytour.</p>
            </div>
        </div>

        <div style="background:var(--text-primary);color:#fff;border-radius:var(--radius-sm);padding:40px;text-align:center;">
            <h2 style="font-family:'Fraunces',serif;font-size:24px;color:var(--accent-amber);padding-left:0;margin-top:0;">Jetzt kostenlos erhalten</h2>
            <p style="font-size:15px;opacity:0.85;margin-bottom:24px;">Melde dich für unseren Newsletter an und erhalte den Guide direkt in dein Postfach.</p>
            <form class="newsletter-form" style="justify-content:center;">
                <input type="email" name="email" placeholder="Deine E-Mail-Adresse" required>
                <button type="submit" class="btn btn-primary">Guide anfordern</button>
            </form>
            <p style="font-size:12px;opacity:0.5;margin-top:12px;">Kein Spam. Jederzeit abbestellbar. <a href="/datenschutz.html" style="color:var(--accent-amber);">Datenschutz</a></p>
        </div>

        <div style="margin-top:40px;">
            <h2 style="font-family:'Fraunces',serif;font-size:22px;text-align:center;padding-left:0;">Was unsere Leser sagen</h2>
            <div style="display:grid;gap:16px;margin-top:24px;">
                <blockquote style="background:var(--bg-surface);padding:20px 24px;border-radius:var(--radius-sm);border-left:3px solid var(--accent-amber);margin:0;">
                    <p style="font-size:15px;margin-bottom:8px;">&bdquo;Der Guide hat mir bei meiner ersten Schottlandreise enorm geholfen. Kompakt, ehrlich, auf den Punkt.&ldquo;</p>
                    <cite style="font-size:13px;color:var(--text-secondary);font-style:normal;">&ndash; Markus, Hamburg</cite>
                </blockquote>
                <blockquote style="background:var(--bg-surface);padding:20px 24px;border-radius:var(--radius-sm);border-left:3px solid var(--accent-amber);margin:0;">
                    <p style="font-size:15px;margin-bottom:8px;">&bdquo;Endlich ein Guide, der nicht nur Marketing ist, sondern echte Erfahrung teilt.&ldquo;</p>
                    <cite style="font-size:13px;color:var(--text-secondary);font-style:normal;">&ndash; Sandra, Wien</cite>
                </blockquote>
            </div>
        </div>
    </div>
    """

    return _base_template().format(
        title="Kostenloser Whisky-Guide",
        site_name=site_name,
        meta_description="Hol dir unseren kostenlosen Whisky-Guide: Verkostungstipps, Regionen-Guide, Top-10 Malts unter 50 EUR und Reise-Checkliste für Schottland.",
        keywords="Whisky Guide, kostenlos, Tasting, Schottland Reise, Single Malt Empfehlungen",
        og_description="Kostenloser Whisky-Guide mit Verkostungstipps und Reise-Checkliste",
        og_image="",
        canonical_url=f"{base_url}/guide.html",
        base_url=base_url,
        content=content,
        json_ld="",
    )


def build_sitemap(articles, config):
    """Erstellt eine XML-Sitemap mit lastmod, Prioritäten und image:image-Erweiterung."""
    from urllib.parse import quote
    from xml.sax.saxutils import escape as xml_escape

    base_url = config["site"].get("base_url", "")
    today = datetime.now().strftime("%Y-%m-%d")

    # Statische Seiten ohne Bilder (impressum, datenschutz, suche absichtlich
    # ausgelassen – noindex-Seiten gehören nicht in die Sitemap)
    # Format: (url, lastmod, priority)
    static_pages = [
        (f"{base_url}/", today, "1.0"),
        (f"{base_url}/karte.html", today, "0.8"),
        (f"{base_url}/ueber-uns.html", today, "0.6"),
    ]

    # Kategorie-Seiten
    categories = set(a.get("category", "Allgemein") for a in articles)
    categories.update(["Whisky", "Reise", "Lifestyle", "Natur", "Urlaub"])
    for cat in sorted(categories):
        cat_slug = quote(cat.lower())
        static_pages.append((f"{base_url}/kategorie/{cat_slug}.html", today, "0.7"))

    # Statische Seiten als XML-Einträge (ohne image:image)
    xml_entries = ""
    for url, lastmod, priority in static_pages:
        xml_entries += (
            f"  <url>\n"
            f"    <loc>{xml_escape(url)}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>\n"
        )

    # Artikel mit image:image-Erweiterung
    for article in articles:
        slug = article.get("meta", {}).get("slug", "")
        if not slug:
            continue
        date = article.get("date", today)
        safe_slug = quote(slug)
        page_url = f"{base_url}/artikel/{safe_slug}.html"

        image_url = article.get("image_url", "")
        # Relative Pfade (/images/...) auf absolute URL ergänzen
        if image_url and image_url.startswith("/"):
            image_url = base_url + image_url
        image_alt = article.get("image_alt", "") or article.get("title", "")
        article_title = article.get("title", "")

        image_block = ""
        if image_url:
            image_block = (
                f"    <image:image>\n"
                f"      <image:loc>{xml_escape(image_url)}</image:loc>\n"
                f"      <image:title>{xml_escape(image_alt or article_title)}</image:title>\n"
                f"    </image:image>\n"
            )

        xml_entries += (
            f"  <url>\n"
            f"    <loc>{xml_escape(page_url)}</loc>\n"
            f"    <lastmod>{date}</lastmod>\n"
            f"    <priority>0.8</priority>\n"
            f"{image_block}"
            f"  </url>\n"
        )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        f'{xml_entries}'
        '</urlset>'
    )


# ============================================================
# Haupt-Build-Funktion
# ============================================================

def _write_html(filepath, html_content):
    """Schreibt HTML-Datei mit CSS-Externalisierung und Pinterest-Tag."""
    html = _externalize_css(html_content)
    html = html.replace('</head>', _PINTEREST_TAG + '\n</head>', 1)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)


def build_site(config):
    """Baut die komplette Website neu auf."""
    global _CSS_EXTRACTED
    _CSS_EXTRACTED = False  # Reset für jeden Build
    print("\n  Website v2 wird gebaut...")

    # Verzeichnisse erstellen
    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "artikel").mkdir(exist_ok=True)
    (SITE_DIR / "kategorie").mkdir(exist_ok=True)

    # Copy images and data from v1 site if they exist
    v1_images = os.path.join(os.path.dirname(SITE_DIR), "site", "images")
    v2_images = os.path.join(SITE_DIR, "images")
    if os.path.exists(v1_images) and not os.path.exists(v2_images):
        shutil.copytree(v1_images, v2_images)
        print("  Bilder aus v1 kopiert.")

    v1_data = os.path.join(os.path.dirname(SITE_DIR), "site", "data")
    v2_data = os.path.join(SITE_DIR, "data")
    if os.path.exists(v1_data) and not os.path.exists(v2_data):
        shutil.copytree(v1_data, v2_data)
        print("  Daten aus v1 kopiert.")

    # Alle Artikel laden
    articles = load_all_articles()
    print(f"  {len(articles)} Artikel gefunden.")

    if not articles:
        print("  HINWEIS: Noch keine Artikel vorhanden.")
        print("  Generiere zuerst Artikel mit Option [2] oder [3].")

    # 1. Startseite zuerst (extrahiert CSS für style.css)
    index_html = build_index_page(articles, config)
    _write_html(SITE_DIR / "index.html", index_html)
    print("  Startseite erstellt (+ style.css extrahiert).")

    # 2. Artikelseiten erstellen (pre-loaded articles durchreichen → O(N) statt O(N²))
    for article in articles:
        # Slug fallback: meta.slug → article.slug → skip
        slug = article.get("meta", {}).get("slug", "") or article.get("slug", "")
        if not slug:
            continue
        # Keep meta.slug in sync for downstream use
        if not article.get("meta", {}).get("slug"):
            article.setdefault("meta", {})["slug"] = slug
        html = build_article_page(article, config, all_articles=articles)
        _write_html(SITE_DIR / "artikel" / f"{slug}.html", html)
    print(f"  {len(articles)} Artikelseiten erstellt.")

    # 3. Kategorieseiten erstellen
    categories = set(a.get("category", "Allgemein") for a in articles)
    # Standard-Kategorien immer erstellen
    categories.update(["Whisky", "Reise", "Lifestyle", "Natur", "Urlaub"])
    for cat in categories:
        cat_html = build_category_page(cat, articles, config)
        _write_html(SITE_DIR / "kategorie" / f"{cat.lower()}.html", cat_html)
    print(f"  {len(categories)} Kategorieseiten erstellt.")

    # 4. Karten-Daten erstellen
    try:
        from map_data_builder import build_map_data
        build_map_data(config)
    except Exception as e:
        print(f"  WARNUNG: Karten-Daten konnten nicht erstellt werden: {e}")

    # 5. Kartenseite erstellen
    try:
        map_html = build_map_page(config)
        _write_html(SITE_DIR / "karte.html", map_html)
        print("  Kartenseite erstellt.")
    except Exception as e:
        print(f"  WARNUNG: Kartenseite konnte nicht erstellt werden: {e}")

    # 6. Über-uns-Seite erstellen
    about_html = build_about_page(config)
    _write_html(SITE_DIR / "ueber-uns.html", about_html)
    print("  Über-uns-Seite erstellt.")

    # 7. Impressum erstellen
    impressum_html = build_impressum_page(config)
    _write_html(SITE_DIR / "impressum.html", impressum_html)
    print("  Impressum erstellt.")

    # 8. Datenschutz erstellen
    datenschutz_html = build_datenschutz_page(config)
    _write_html(SITE_DIR / "datenschutz.html", datenschutz_html)
    print("  Datenschutzseite erstellt.")

    # 9. Guide-Seite wurde entfernt (Lead-Magnet nicht mehr aktiv)

    # 10. Suchseite + Suchindex erstellen
    search_html = build_search_page(config)
    _write_html(SITE_DIR / "suche.html", search_html)
    (SITE_DIR / "data").mkdir(exist_ok=True)
    search_index = build_search_index(articles, config)
    with open(SITE_DIR / "data" / "search-index.json", "w", encoding="utf-8") as f:
        f.write(search_index)
    print("  Suchseite + Suchindex erstellt.")

    # 11. Danke-Seite erstellen
    danke_html = build_danke_page(config)
    _write_html(SITE_DIR / "danke.html", danke_html)
    print("  Danke-Seite erstellt.")

    # 12. 404-Seite erstellen
    page_404 = build_404_page(config)
    _write_html(SITE_DIR / "404.html", page_404)
    print("  404-Seite erstellt.")

    # 12. RSS Feed erstellen
    rss_xml = build_rss_feed(articles, config)
    with open(SITE_DIR / "feed.xml", "w", encoding="utf-8") as f:
        f.write(rss_xml)
    print("  RSS Feed erstellt.")

    # 13. Sitemap erstellen
    sitemap_xml = build_sitemap(articles, config)
    with open(SITE_DIR / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_xml)
    print("  Sitemap erstellt.")

    # 14. Whisky-Glossar erstellen
    try:
        from glossary_builder import build_glossary_pages
        build_glossary_pages(config)
    except Exception as e:
        print(f"  WARNUNG: Glossar-Seiten konnten nicht erstellt werden: {e}")

    # 15. robots.txt erstellen
    base_url = config["site"].get("base_url", "")
    robots_txt = f"""User-agent: *
Allow: /

Sitemap: {base_url}/sitemap.xml
"""
    with open(SITE_DIR / "robots.txt", "w", encoding="utf-8") as f:
        f.write(robots_txt)
    print("  robots.txt erstellt.")

    print(f"\n  Website bereit unter: {SITE_DIR}")
    print(f"  Öffne {SITE_DIR / 'index.html'} im Browser um sie zu sehen!")

    # 7. Push to V2 GitHub repo
    _push_to_v2_repo(str(PROJECT_DIR))

    return str(SITE_DIR)
