"""
Site Builder: Generiert eine komplette statische Website aus Artikel-Daten.
Erstellt HTML-Seiten, Startseite, Kategorie-Seiten und Sitemap.
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
SITE_DIR = PROJECT_DIR / "site"
ARTICLES_DIR = PROJECT_DIR / "articles"


# ============================================================
# Deutsche Monatsnamen
# ============================================================
MONATE = {
    "January": "Januar", "February": "Februar", "March": "März",
    "April": "April", "May": "Mai", "June": "Juni",
    "July": "Juli", "August": "August", "September": "September",
    "October": "Oktober", "November": "November", "December": "Dezember",
}


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
# HTML-Templates (eingebettet - keine externen Abhaengigkeiten)
# ============================================================

def _base_template():
    """Basis-HTML-Template fuer alle Seiten."""
    return """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | {site_name}</title>
    <meta name="description" content="{meta_description}">
    <meta name="keywords" content="{keywords}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{og_description}">
    <meta property="og:type" content="article">
    <meta property="og:image" content="{og_image}">
    <link rel="canonical" href="{canonical_url}">
    <style>
        :root {{
            --whisky-dark: #1a1209;
            --whisky-brown: #3d2b1f;
            --whisky-amber: #b8860b;
            --whisky-gold: #d4a574;
            --whisky-light: #f5e6d3;
            --whisky-cream: #faf6f0;
            --whisky-white: #fffdf9;
            --text-primary: #2c2c2c;
            --text-secondary: #5a5a5a;
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.08);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.1);
            --shadow-lg: 0 8px 30px rgba(0,0,0,0.12);
            --radius: 12px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Georgia', 'Times New Roman', serif;
            background: var(--whisky-cream);
            color: var(--text-primary);
            line-height: 1.8;
            font-size: 17px;
        }}

        /* --- HEADER --- */
        header {{
            background: linear-gradient(135deg, var(--whisky-dark) 0%, var(--whisky-brown) 100%);
            color: var(--whisky-gold);
            padding: 0;
            box-shadow: var(--shadow-lg);
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        .header-inner {{
            max-width: 1100px;
            margin: 0 auto;
            padding: 15px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .logo {{
            font-size: 1.6em;
            font-weight: bold;
            letter-spacing: 2px;
            text-decoration: none;
            color: var(--whisky-gold);
        }}
        .logo span {{
            color: #fff;
            font-weight: 300;
        }}
        nav a {{
            color: var(--whisky-light);
            text-decoration: none;
            margin-left: 28px;
            font-size: 0.9em;
            letter-spacing: 0.5px;
            transition: color 0.2s;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        nav a:hover {{ color: var(--whisky-gold); }}

        /* --- HERO (nur Startseite) --- */
        .hero {{
            background: linear-gradient(135deg, var(--whisky-dark) 0%, var(--whisky-brown) 50%, var(--whisky-amber) 100%);
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
            max-width: 1100px;
            margin: 0 auto;
            padding: 40px 24px;
        }}
        .content-grid {{
            display: grid;
            grid-template-columns: 1fr 340px;
            gap: 40px;
        }}
        @media (max-width: 900px) {{
            .content-grid {{ grid-template-columns: 1fr; }}
        }}

        /* --- ARTIKELKARTEN (Startseite) --- */
        .article-card {{
            background: var(--whisky-white);
            border-radius: var(--radius);
            box-shadow: var(--shadow-sm);
            overflow: hidden;
            margin-bottom: 28px;
            transition: box-shadow 0.3s, transform 0.2s;
        }}
        .article-card:hover {{
            box-shadow: var(--shadow-md);
            transform: translateY(-2px);
        }}
        .article-card .card-body {{
            padding: 28px;
        }}
        .card-meta {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.8em;
            color: var(--text-secondary);
            margin-bottom: 8px;
            display: flex;
            gap: 16px;
        }}
        .card-meta .cat {{
            background: var(--whisky-light);
            color: var(--whisky-brown);
            padding: 2px 10px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85em;
        }}
        .article-card h2 {{
            font-size: 1.4em;
            margin-bottom: 10px;
            line-height: 1.3;
        }}
        .article-card h2 a {{
            color: var(--whisky-brown);
            text-decoration: none;
        }}
        .article-card h2 a:hover {{
            color: var(--whisky-amber);
        }}
        .article-card .teaser {{
            color: var(--text-secondary);
            font-size: 0.95em;
            margin-bottom: 16px;
        }}
        .read-more {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: var(--whisky-amber);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9em;
        }}
        .read-more:hover {{ text-decoration: underline; }}

        /* --- ARTIKEL-SEITE --- */
        .article-header {{
            background: linear-gradient(135deg, var(--whisky-dark) 0%, var(--whisky-brown) 100%);
            color: #fff;
            padding: 60px 24px 50px;
            text-align: center;
        }}
        .article-header h1 {{
            font-size: 2.2em;
            max-width: 800px;
            margin: 0 auto 16px;
            line-height: 1.3;
        }}
        .article-header .meta-line {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.85em;
            opacity: 0.75;
        }}
        .article-body {{
            background: var(--whisky-white);
            border-radius: var(--radius);
            box-shadow: var(--shadow-md);
            padding: 48px;
            margin-top: -30px;
            position: relative;
        }}
        .article-body h2 {{
            color: var(--whisky-brown);
            font-size: 1.5em;
            margin: 36px 0 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--whisky-light);
        }}
        .article-body h3 {{
            color: var(--whisky-amber);
            font-size: 1.2em;
            margin: 28px 0 12px;
        }}
        .article-body p {{ margin-bottom: 18px; }}
        .article-body ul, .article-body ol {{
            margin: 16px 0;
            padding-left: 28px;
        }}
        .article-body li {{ margin-bottom: 8px; }}
        .article-body blockquote {{
            border-left: 4px solid var(--whisky-amber);
            background: var(--whisky-light);
            padding: 20px 24px;
            margin: 24px 0;
            border-radius: 0 var(--radius) var(--radius) 0;
            font-style: italic;
            color: var(--whisky-brown);
        }}
        .article-body a {{
            color: var(--whisky-amber);
            text-decoration: underline;
            text-decoration-color: var(--whisky-gold);
        }}
        .article-body a:hover {{ color: var(--whisky-brown); }}

        .affiliate-link {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: linear-gradient(135deg, var(--whisky-amber), var(--whisky-gold));
            color: #fff !important;
            padding: 3px 10px 3px 8px;
            border-radius: 4px;
            text-decoration: none !important;
            border-bottom: none !important;
            font-size: 0.9em;
            font-weight: 600;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            transition: background 0.2s, transform 0.1s;
            white-space: nowrap;
        }}
        .affiliate-link::before {{ content: "→"; font-size: 0.8em; }}
        .affiliate-link:hover {{
            background: linear-gradient(135deg, var(--whisky-brown), var(--whisky-amber));
            transform: translateY(-1px);
            color: #fff !important;
        }}

        .related-box {{
            background: var(--whisky-light);
            border-radius: var(--radius);
            padding: 24px;
            margin-top: 36px;
            border: 1px solid var(--whisky-gold);
        }}
        .related-box h3 {{
            color: var(--whisky-brown);
            margin-bottom: 12px;
            border: none;
        }}

        /* --- SIDEBAR --- */
        .sidebar {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        .sidebar-box {{
            background: var(--whisky-white);
            border-radius: var(--radius);
            box-shadow: var(--shadow-sm);
            padding: 24px;
            margin-bottom: 24px;
        }}
        .sidebar-box h3 {{
            color: var(--whisky-brown);
            font-size: 1em;
            margin-bottom: 14px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--whisky-light);
            font-family: Georgia, serif;
        }}
        .sidebar-box ul {{ list-style: none; padding: 0; }}
        .sidebar-box li {{ margin-bottom: 10px; }}
        .sidebar-box a {{
            color: var(--text-primary);
            text-decoration: none;
            font-size: 0.9em;
        }}
        .sidebar-box a:hover {{ color: var(--whisky-amber); }}

        .tag-cloud {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .tag {{
            background: var(--whisky-light);
            color: var(--whisky-brown);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            text-decoration: none;
            transition: background 0.2s;
        }}
        .tag:hover {{
            background: var(--whisky-gold);
            color: #fff;
        }}

        .cta-box {{
            background: linear-gradient(135deg, var(--whisky-brown) 0%, var(--whisky-dark) 100%);
            color: var(--whisky-light);
            border-radius: var(--radius);
            padding: 28px;
            text-align: center;
        }}
        .cta-box h3 {{ color: var(--whisky-gold); border: none; }}
        .cta-box p {{ font-size: 0.9em; margin: 10px 0 16px; opacity: 0.85; }}
        .cta-box a {{
            display: inline-block;
            background: var(--whisky-amber);
            color: #fff;
            padding: 10px 28px;
            border-radius: 30px;
            text-decoration: none;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .cta-box a:hover {{ background: var(--whisky-gold); }}

        /* --- TAGS --- */
        .article-tags {{
            margin-top: 32px;
            padding-top: 20px;
            border-top: 1px solid var(--whisky-light);
        }}

        /* --- FOOTER --- */
        footer {{
            background: var(--whisky-dark);
            color: var(--whisky-gold);
            text-align: center;
            padding: 40px 24px;
            margin-top: 60px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.85em;
        }}
        footer a {{ color: var(--whisky-gold); text-decoration: none; }}
        footer a:hover {{ text-decoration: underline; }}
        .footer-note {{
            opacity: 0.5;
            font-size: 0.85em;
            margin-top: 12px;
        }}

        /* --- CARD IMAGE --- */
        .card-image-wrapper {{
            position: relative;
            overflow: hidden;
            border-radius: var(--radius) var(--radius) 0 0;
            height: 210px;
        }}
        .card-image {{
            width: 100%; height: 210px; object-fit: cover;
            display: block;
            filter: saturate(1.15) contrast(1.05) brightness(0.92);
            transition: transform 0.5s ease, filter 0.3s ease;
        }}
        .article-card:hover .card-image {{
            transform: scale(1.04);
            filter: saturate(1.25) contrast(1.08) brightness(0.97);
        }}
        /* Einheitlicher Warm-Amber-Overlay auf allen Kartenbildern */
        .card-image-wrapper::after {{
            content: '';
            position: absolute; inset: 0;
            background: linear-gradient(
                to bottom,
                rgba(184, 134, 11, 0.08) 0%,
                rgba(61, 43, 31, 0.28) 100%
            );
            pointer-events: none;
        }}
        .card-image-placeholder {{
            width: 100%; height: 210px;
            background: linear-gradient(135deg, var(--whisky-dark) 0%, var(--whisky-brown) 100%);
            display: flex; align-items: center; justify-content: center;
            font-size: 3em; color: var(--whisky-gold);
            border-radius: var(--radius) var(--radius) 0 0;
        }}

        /* --- ARTICLE HERO IMAGE --- */
        .article-hero-image {{
            width: 100%; max-height: 480px; object-fit: cover; display: block;
        }}
        .article-image-credit {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.72em; color: var(--text-secondary);
            text-align: right; padding: 4px 8px; background: var(--whisky-light);
        }}
        .article-image-credit a {{ color: var(--text-secondary); }}

        /* --- EMPFEHLUNG BOX --- */
        .empfehlung-box {{
            border: 2px solid var(--whisky-gold); border-radius: var(--radius);
            padding: 20px 24px; margin: 32px 0;
            background: linear-gradient(135deg, var(--whisky-cream) 0%, #fff9f0 100%);
            display: flex; align-items: flex-start; gap: 16px;
        }}
        .empfehlung-box .emp-icon {{ font-size: 2em; flex-shrink: 0; margin-top: 2px; }}
        .empfehlung-box .emp-content {{ flex: 1; }}
        .empfehlung-box .emp-title {{
            font-family: Georgia, serif; font-weight: bold;
            color: var(--whisky-brown); font-size: 1.05em; margin-bottom: 6px;
        }}
        .empfehlung-box .emp-text {{
            font-size: 0.9em; color: var(--text-secondary); margin-bottom: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        .empfehlung-box .emp-cta {{
            display: inline-block; background: var(--whisky-amber);
            color: #fff !important; padding: 8px 20px; border-radius: 20px;
            text-decoration: none !important; font-weight: bold; font-size: 0.85em;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            transition: background 0.2s; margin-right: 8px; margin-bottom: 4px;
        }}
        .empfehlung-box .emp-cta:hover {{ background: var(--whisky-brown); color: #fff !important; }}

        /* --- SHARE BUTTONS --- */
        .share-bar {{
            display: flex; gap: 10px; margin: 28px 0 20px;
            flex-wrap: wrap; align-items: center;
        }}
        .share-label {{
            font-size: 0.85em; color: var(--text-secondary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        .share-btn {{
            display: inline-flex; align-items: center; gap: 6px;
            padding: 8px 16px; border-radius: 20px;
            text-decoration: none !important; font-size: 0.82em;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-weight: 600; transition: opacity 0.2s; color: #fff !important;
        }}
        .share-btn:hover {{ opacity: 0.85; }}
        .share-btn-whatsapp {{ background: #25D366; }}
        .share-btn-x {{ background: #000; }}
        .share-btn-pinterest {{ background: #E60023; }}
        .share-btn-email {{ background: var(--whisky-brown); }}

        /* --- BREADCRUMB --- */
        .breadcrumb {{
            background: var(--whisky-light); padding: 10px 24px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 0.82em; color: var(--text-secondary);
        }}
        .breadcrumb-inner {{ max-width: 1100px; margin: 0 auto; }}
        .breadcrumb a {{ color: var(--text-secondary); text-decoration: none; }}
        .breadcrumb a:hover {{ color: var(--whisky-amber); }}

        /* --- RELATED GRID --- */
        .related-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 12px; }}
        .related-item {{
            background: var(--whisky-cream); border-radius: 8px;
            padding: 12px 14px; text-decoration: none !important;
            border-left: 3px solid var(--whisky-gold);
            color: var(--whisky-brown) !important; font-size: 0.88em;
            line-height: 1.4; transition: background 0.2s, border-color 0.2s; display: block;
        }}
        .related-item:hover {{ background: var(--whisky-light); border-left-color: var(--whisky-amber); }}

        /* --- PERSONAL PHOTO BADGE --- */
        .personal-photo-wrapper {{ position: relative; display: block; }}
        .personal-photo-badge {{
            position: absolute; bottom: 8px; left: 8px;
            background: rgba(61,43,31,0.85); color: var(--whisky-gold);
            font-size: 0.7em; padding: 2px 8px; border-radius: 10px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
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

        /* --- RESPONSIVE --- */
        @media (max-width: 600px) {{
            .hero h1 {{ font-size: 1.8em; }}
            .article-header h1 {{ font-size: 1.5em; }}
            .article-body {{ padding: 24px; }}
            .header-inner {{ flex-direction: column; gap: 12px; }}
            nav a {{ margin-left: 12px; }}
            .card-image-wrapper, .card-image, .card-image-placeholder {{ height: 160px; }}
            .article-hero-image {{ max-height: 240px; }}
            .related-grid {{ grid-template-columns: 1fr; }}
            .empfehlung-box {{ flex-direction: column; gap: 8px; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="header-inner">
            <a href="{base_url}/index.html" class="logo">WHISKY<span>.MAGAZIN</span></a>
            <nav>
                <a href="{base_url}/index.html">Start</a>
                <a href="{base_url}/kategorie/whisky.html">Whisky</a>
                <a href="{base_url}/kategorie/reise.html">Reise</a>
                <a href="{base_url}/karte.html">Karte</a>
                <a href="{base_url}/kategorie/lifestyle.html">Lifestyle</a>
                <a href="https://www.whisky.reise" target="_blank">whisky.reise</a>
            </nav>
        </div>
    </header>
    {content}
    <footer>
        <p>Ein Projekt von <a href="https://www.whisky.reise">whisky.reise</a> &mdash; Whisky, Reisen & mehr.</p>
        <p class="footer-note">* Affiliate-Links: Bei Käufen über gekennzeichnete Links erhalten wir eine kleine Provision.</p>
    </footer>
</body>
</html>"""


# ============================================================
# Seiten generieren
# ============================================================

def load_all_articles():
    """Laedt alle gespeicherten Artikel aus dem articles-Ordner."""
    ARTICLES_DIR.mkdir(exist_ok=True)
    articles = []
    for json_file in sorted(ARTICLES_DIR.glob("*.json"), reverse=True):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                article = json.load(f)
                articles.append(article)
        except Exception as e:
            print(f"  Warnung: Konnte {json_file.name} nicht laden: {e}")
    return articles


def _find_related_articles(current_article, all_articles, base_url, max_count=4):
    """Findet verwandte Artikel basierend auf Kategorie- und Tag-Uebereinstimmung."""
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
        # Punkte fuer ueberlappende Kategorien
        a_cats = set()
        if a.get("categories"):
            a_cats = set(c.lower() for c in a["categories"])
        elif a.get("category"):
            a_cats = {a["category"].lower()}
        cat_score = len(current_cats & a_cats) * 2
        # Punkte fuer ueberlappende Tags
        a_tags = set(t.lower() for t in a.get("tags", []))
        tag_score = len(current_tags & a_tags)
        total = cat_score + tag_score
        if total > 0:
            scored.append((total, a))

    # Nach Score sortieren (hoechster zuerst), bei Gleichstand nach Datum
    scored.sort(key=lambda x: (x[0], x[1].get("date", "")), reverse=True)

    cat_emoji = {"whisky": "🥃", "reise": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "lifestyle": "✨", "natur": "🌿", "urlaub": "🌄"}

    items = []
    for _, a in scored[:max_count]:
        slug = a.get("meta", {}).get("slug", "")
        title = a["title"]
        cat = a.get("category", "").lower()
        emoji = cat_emoji.get(cat, "📖")
        items.append(f'<a href="{base_url}/artikel/{slug}.html" class="related-item">{emoji} {title}</a>')

    # Falls weniger als max_count gefunden, mit neuesten Artikeln auffuellen
    used_slugs = {current_slug} | {a.get("meta", {}).get("slug", "") for _, a in scored[:max_count]}
    if len(items) < max_count:
        for a in all_articles:
            slug = a.get("meta", {}).get("slug", "")
            if slug and slug not in used_slugs:
                title = a["title"]
                cat = a.get("category", "").lower()
                emoji = cat_emoji.get(cat, "📖")
                items.append(f'<a href="{base_url}/artikel/{slug}.html" class="related-item">{emoji} {title}</a>')
                used_slugs.add(slug)
                if len(items) >= max_count:
                    break

    if items:
        grid = '\n'.join(items)
        return f'<div class="related-box"><h3>Das könnte dich auch interessieren</h3><div class="related-grid">{grid}</div></div>'
    return ""


def _replace_related_box(html_content, related_html):
    """Ersetzt die GPT-generierte related-box durch echte verlinkte Artikel."""
    # Entferne die bestehende related-box (verschiedene Formate)
    pattern = r'<div class=["\']related-box["\']>.*?</div>'
    cleaned = re.sub(pattern, '', html_content, flags=re.DOTALL)
    # Fuege die neue related-box vor dem Ende ein
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
            '<div class="emp-icon">🏴󠁧󠁢󠁳󠁣󠁴󠁿</div>'
            '<div class="emp-content">'
            '<div class="emp-title">Reise planen</div>'
            '<div class="emp-text">Fähre, Hotel und mehr für deine Schottland-Reise – alles auf einen Blick.</div>'
            f'<a href="{faehre}" target="_blank" rel="noopener noreferrer" class="emp-cta">Fähre buchen →</a>'
            f'<a href="{hotel}" target="_blank" rel="noopener noreferrer" class="emp-cta">Hotels ansehen →</a>'
            '</div></div>'
        )
    else:
        # Erstes Keyword aus Tags für Amazon-Suche
        tags = article.get('tags', [])
        keyword = tags[0].lower().replace(' ', '+') if tags else 'single+malt+whisky'
        box = (
            '<div class="empfehlung-box">'
            '<div class="emp-icon">🥃</div>'
            '<div class="emp-content">'
            '<div class="emp-title">Diesen Whisky bestellen</div>'
            '<div class="emp-text">Die im Artikel erwähnten Whiskys findest du bei Amazon – oft mit Prime-Lieferung.</div>'
            f'<a href="https://www.amazon.de/s?k={keyword}+whisky&tag={amazon_tag}" target="_blank" rel="noopener noreferrer" class="emp-cta">Bei Amazon ansehen →</a>'
            '</div></div>'
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
    """Prueft ob ein Artikel Karten-Locations hat (explizit oder per Reisebericht-Typ)."""
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
    """Erzeugt Mini-Map HTML fuer Artikel mit Ortsbezug."""
    slug = article.get("meta", {}).get("slug", "")

    return f"""
    <div class="article-mini-map" style="margin: 20px 0;">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <span style="font-size:1.2em;">📍</span>
            <a href="{base_url}/karte.html?highlight={slug}"
               style="color:var(--whisky-amber); text-decoration:none; font-size:0.9em;
                      font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
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


def build_article_page(article, config):
    """Erstellt die HTML-Seite fuer einen einzelnen Artikel."""
    from urllib.parse import quote
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    meta = article.get("meta", {})
    slug = meta.get("slug", "")
    date_display = _german_date(article.get("date", ""))
    category = article.get('category', 'Allgemein')
    cat_lower = category.lower()
    reading_time = _reading_time(article['html_content'])

    tags_html = ""
    if article.get("tags"):
        tag_links = " ".join(
            f'<span class="tag">{tag}</span>' for tag in article["tags"]
        )
        tags_html = f'<div class="article-tags"><div class="tag-cloud">{tag_links}</div></div>'

    # Sidebar mit neuesten Artikeln
    all_articles = load_all_articles()
    recent_html = ""
    for a in all_articles[:5]:
        if a.get("meta", {}).get("slug") != slug:
            s = a.get("meta", {}).get("slug", "")
            t = a["title"]
            recent_html += f'<li><a href="{base_url}/artikel/{s}.html">{t}</a></li>\n'

    # Related-Box + Empfehlung-Box
    related_html = _find_related_articles(article, all_articles, base_url, max_count=4)
    article_html = _replace_related_box(article['html_content'], related_html)
    article_html = _inject_empfehlung_boxes(article_html, article, config)

    # Hero-Bild (Unsplash oder persönliches Cartoon-Foto)
    hero_img = ""
    if article.get("image_url"):
        is_personal = article.get("image_source") == "personal_cartoon"
        img_tag = f'<img src="{article["image_url"]}" alt="{article.get("image_alt", article["title"])}" class="article-hero-image" loading="lazy">'
        if is_personal:
            hero_img = f'<div class="personal-photo-wrapper">{img_tag}<span class="personal-photo-badge">Eigenes Foto</span></div>'
        else:
            hero_img = img_tag
        if article.get("image_credit"):
            hero_img += f'<div class="article-image-credit">{article["image_credit"]}</div>'

    # OG-Image
    og_image = article.get("image_url", f"{base_url}/images/default.jpg")

    # Share-Buttons
    article_url = f"{base_url}/artikel/{slug}.html"
    share_title = quote(article["title"])
    share_url = quote(article_url)
    share_html = f"""<div class="share-bar">
        <span class="share-label">Teilen:</span>
        <a href="https://wa.me/?text={share_title}%20{share_url}" class="share-btn share-btn-whatsapp" target="_blank" rel="noopener noreferrer">📱 WhatsApp</a>
        <a href="https://x.com/intent/tweet?text={share_title}&url={share_url}" class="share-btn share-btn-x" target="_blank" rel="noopener noreferrer">✕ X</a>
        <a href="https://pinterest.com/pin/create/button/?url={share_url}&description={share_title}" class="share-btn share-btn-pinterest" target="_blank" rel="noopener noreferrer">📌 Pinterest</a>
        <a href="mailto:?subject={share_title}&body={share_url}" class="share-btn share-btn-email">✉ E-Mail</a>
    </div>"""

    # Sidebar CTAs (Reise-Artikel bekommen Reise-CTAs zuerst)
    amazon_tag = config.get('affiliate_links', {}).get('amazon_tag', 'whiskyreise74-21')
    travel = config.get('affiliate_links', {}).get('travel_links', {})
    faehre_url = travel.get('faehre', '#')
    is_travel = cat_lower in ('reise', 'urlaub')

    if is_travel:
        cta1 = f"""<div class="cta-box">
                    <h3>Schottland-Reise planen</h3>
                    <p>Fähren, Flüge & Hotels auf einen Blick</p>
                    <a href="{faehre_url}" target="_blank" rel="noopener noreferrer">Fähre buchen &#8594;</a>
                </div>
                <div class="cta-box" style="margin-top: 20px;">
                    <h3>Whisky entdecken</h3>
                    <p>Die besten Single Malts bei Amazon</p>
                    <a href="https://www.amazon.de/s?k=single+malt+whisky&tag={amazon_tag}" target="_blank" rel="noopener noreferrer">Whisky shoppen &#8594;</a>
                </div>"""
    else:
        cta1 = f"""<div class="cta-box">
                    <h3>Whisky entdecken</h3>
                    <p>Finde deinen nächsten Lieblings-Dram</p>
                    <a href="https://www.amazon.de/s?k=single+malt+whisky&tag={amazon_tag}" target="_blank" rel="noopener noreferrer">Whisky bei Amazon &#8594;</a>
                </div>
                <div class="cta-box" style="margin-top: 20px;">
                    <h3>Schottland-Reise planen</h3>
                    <p>Fähren, Flüge & Hotels</p>
                    <a href="{faehre_url}" target="_blank" rel="noopener noreferrer">Fähre buchen &#8594;</a>
                </div>"""

    # Mini-Map fuer Artikel mit Ortsbezug
    mini_map_html = ""
    if _has_map_locations(article):
        mini_map_html = _build_mini_map_html(article, base_url)

    content = f"""
    <div class="article-header">
        <h1>{article['title']}</h1>
        <div class="meta-line">{date_display} &bull; {category} &bull; {reading_time} Min. Lesezeit &bull; von {config['site']['author']}</div>
    </div>
    {hero_img}
    <div class="breadcrumb">
        <div class="breadcrumb-inner">
            <a href="{base_url}/index.html">Start</a> ›
            <a href="{base_url}/kategorie/{cat_lower}.html">{category}</a> ›
            {article['title']}
        </div>
    </div>
    <div class="container">
        <div class="content-grid">
            <main>
                <div class="article-body">
                    {mini_map_html}
                    {article_html}
                    {share_html}
                    {tags_html}
                </div>
            </main>
            <aside class="sidebar">
                <div class="sidebar-box">
                    <h3>Neueste Artikel</h3>
                    <ul>{recent_html}</ul>
                </div>
                {cta1}
            </aside>
        </div>
    </div>"""

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
    )


def build_index_page(articles, config):
    """Erstellt die Startseite mit Artikeluebersicht."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    tagline = config["site"]["tagline"]

    cat_emoji = {"Whisky": "🥃", "Reise": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Lifestyle": "✨", "Natur": "🌿", "Urlaub": "🌄"}

    # Artikelkarten
    cards_html = ""
    for article in articles[:12]:
        meta = article.get("meta", {})
        slug = meta.get("slug", "")
        teaser = meta.get("teaser", meta.get("meta_description", ""))
        date_display = _german_date(article.get("date", ""))
        category = article.get("category", "Allgemein")

        emoji = cat_emoji.get(category, "🥃")
        if article.get("image_url"):
            onerror = f"this.parentNode.innerHTML='<div class=\\'card-image-placeholder\\'>{emoji}</div>'"
            img_html = f'<div class="card-image-wrapper"><img src="{article["image_url"]}" alt="{article.get("image_alt", article["title"])}" class="card-image" loading="lazy" onerror="{onerror}"></div>'
        else:
            img_html = f'<div class="card-image-placeholder">{emoji}</div>'

        cards_html += f"""
        <div class="article-card">
            {img_html}
            <div class="card-body">
                <div class="card-meta">
                    <span class="cat">{category}</span>
                    <span>{date_display}</span>
                </div>
                <h2><a href="{base_url}/artikel/{slug}.html">{article['title']}</a></h2>
                <p class="teaser">{teaser}</p>
                <a href="{base_url}/artikel/{slug}.html" class="read-more">Weiterlesen &#8594;</a>
            </div>
        </div>"""

    # Sidebar: Kategorien + Tags
    categories = {}
    all_tags = set()
    for a in articles:
        cat = a.get("category", "Allgemein")
        categories[cat] = categories.get(cat, 0) + 1
        for tag in a.get("tags", []):
            all_tags.add(tag)

    cat_html = ""
    for cat_name, count in sorted(categories.items()):
        cat_slug = cat_name.lower()
        cat_html += f'<li><a href="{base_url}/kategorie/{cat_slug}.html">{cat_name} ({count})</a></li>\n'

    tags_html = " ".join(f'<span class="tag">{t}</span>' for t in sorted(all_tags)[:20])

    content = f"""
    <div class="hero">
        <h1>{site_name}</h1>
        <p>{tagline}</p>
    </div>
    <div class="container">
        <div class="content-grid">
            <main>
                {cards_html}
            </main>
            <aside class="sidebar">
                <div class="sidebar-box">
                    <h3>Kategorien</h3>
                    <ul>{cat_html}</ul>
                </div>
                <div class="sidebar-box">
                    <h3>Schlagwörter</h3>
                    <div class="tag-cloud">{tags_html}</div>
                </div>
                <div class="cta-box">
                    <h3>Whisky shoppen</h3>
                    <p>Die besten Single Malts auf einen Blick</p>
                    <a href="https://www.amazon.de/s?k=single+malt+whisky&tag={config.get('affiliate_links', {}).get('amazon_tag', 'whiskyreise74-21')}" target="_blank" rel="noopener noreferrer">Jetzt entdecken &#8594;</a>
                </div>
                <div class="sidebar-box" style="margin-top: 20px;">
                    <h3>Über uns</h3>
                    <p style="font-size:0.9em; color: var(--text-secondary);">
                        Wir sind leidenschaftliche Whisky-Liebhaber und Reisende.
                        Hier teilen wir unser Wissen über Single Malts, Destillerien
                        und die schönsten Whisky-Regionen der Welt.
                    </p>
                    <p style="margin-top:10px;"><a href="https://www.whisky.reise" target="_blank">&#8594; Mehr auf whisky.reise</a></p>
                </div>
            </aside>
        </div>
    </div>"""

    return _base_template().format(
        title="Start",
        site_name=site_name,
        meta_description=tagline,
        keywords="Whisky, Scotch, Single Malt, Reise, Schottland, Destillerien",
        og_description=tagline,
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/index.html",
        base_url=base_url,
        content=content,
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

        if article.get("image_url"):
            img_html = f'<div class="card-image-wrapper"><img src="{article["image_url"]}" alt="{article.get("image_alt", article["title"])}" class="card-image" loading="lazy"></div>'
        else:
            emoji = cat_emoji_map.get(cat, cat_emoji_map.get(category_name, "🥃"))
            img_html = f'<div class="card-image-placeholder">{emoji}</div>'

        cards_html += f"""
        <div class="article-card">
            {img_html}
            <div class="card-body">
                <div class="card-meta"><span>{date_display}</span></div>
                <h2><a href="{base_url}/artikel/{slug}.html">{article['title']}</a></h2>
                <p class="teaser">{teaser}</p>
                <a href="{base_url}/artikel/{slug}.html" class="read-more">Weiterlesen &#8594;</a>
            </div>
        </div>"""

    if not cards_html:
        cards_html = '<p style="color: var(--text-secondary);">Noch keine Artikel in dieser Kategorie.</p>'

    content = f"""
    <div class="article-header">
        <h1>Kategorie: {category_name}</h1>
        <div class="meta-line">{len(filtered)} Artikel</div>
    </div>
    <div class="container">
        <div class="content-grid">
            <main>{cards_html}</main>
            <aside class="sidebar">
                <div class="cta-box">
                    <h3>Alle Artikel</h3>
                    <p>Zurück zur Übersicht</p>
                    <a href="{base_url}/index.html">Zur Startseite &#8594;</a>
                </div>
            </aside>
        </div>
    </div>"""

    return _base_template().format(
        title=f"Kategorie: {category_name}",
        site_name=site_name,
        meta_description=f"Alle Artikel in der Kategorie {category_name}",
        keywords=category_name,
        og_description=f"Alle Artikel in der Kategorie {category_name}",
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/kategorie/{category_name.lower()}.html",
        base_url=base_url,
        content=content,
    )


def build_map_page(config):
    """Erstellt die interaktive Karten-Seite mit Leaflet.js."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    map_config = config.get("map", {})
    center_lat, center_lon = map_config.get("default_center", [57.0, -4.5])
    default_zoom = map_config.get("default_zoom", 6)

    content = f"""
    <div class="map-page">
        <div class="map-header">
            <h1>Unsere Whisky-Reisekarte</h1>
            <p class="map-subtitle">18 Jahre Destillerien, Reisen & Abenteuer &mdash; von Schottland bis Kentucky</p>
        </div>
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
                <select id="filter-country"><option value="">Alle Laender</option></select>
            </div>
            <div class="filter-group filter-toggles">
                <label class="toggle-label"><input type="checkbox" id="toggle-distillery" checked> Destillerien</label>
                <label class="toggle-label"><input type="checkbox" id="toggle-city" checked> Staedte</label>
                <label class="toggle-label"><input type="checkbox" id="toggle-nature" checked> Natur</label>
                <label class="toggle-label"><input type="checkbox" id="toggle-poi" checked> Sehenswuerdigkeiten</label>
                <label class="toggle-label"><input type="checkbox" id="toggle-travel_stop" checked> Reisestopps</label>
            </div>
            <div class="map-stats" id="map-stats"></div>
        </div>
        <div id="map" style="height: 65vh; min-height: 400px; border-radius: 12px; box-shadow: var(--shadow-md); z-index: 1;"></div>
        <div class="location-cards" id="location-cards"></div>
    </div>

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

    <style>
        .map-page {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
        .map-header {{ text-align: center; margin-bottom: 20px; }}
        .map-header h1 {{ font-size: 2em; color: var(--whisky-brown); margin-bottom: 8px; }}
        .map-subtitle {{ color: var(--text-secondary); font-size: 1.05em; }}
        .map-controls {{
            display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
            padding: 16px; background: var(--whisky-white); border-radius: var(--radius);
            box-shadow: var(--shadow-sm); margin-bottom: 16px;
        }}
        .filter-group {{ display: flex; align-items: center; gap: 6px; }}
        .filter-group label {{ font-size: 0.85em; color: var(--text-secondary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .filter-group select {{
            padding: 6px 10px; border: 1px solid var(--whisky-gold); border-radius: 6px;
            background: var(--whisky-cream); font-size: 0.85em; cursor: pointer;
        }}
        .filter-toggles {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .toggle-label {{
            display: flex; align-items: center; gap: 4px; cursor: pointer;
            font-size: 0.82em !important; white-space: nowrap;
        }}
        .toggle-label input {{ accent-color: var(--whisky-amber); }}
        .map-stats {{
            margin-left: auto; font-size: 0.82em; color: var(--text-secondary);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        .location-cards {{
            display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px; margin-top: 24px;
        }}
        .loc-card {{
            background: var(--whisky-white); border-radius: var(--radius);
            box-shadow: var(--shadow-sm); overflow: hidden; cursor: pointer;
            transition: box-shadow 0.3s, transform 0.2s;
        }}
        .loc-card:hover {{ box-shadow: var(--shadow-md); transform: translateY(-2px); }}
        .loc-card-img {{ width: 100%; height: 160px; object-fit: cover; }}
        .loc-card-body {{ padding: 14px; }}
        .loc-card-name {{ font-weight: bold; font-size: 1em; color: var(--whisky-brown); }}
        .loc-card-meta {{
            font-size: 0.8em; color: var(--text-secondary); margin-top: 4px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        .loc-card-type {{
            display: inline-block; font-size: 0.7em; padding: 2px 8px;
            border-radius: 10px; margin-top: 6px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }}
        .type-distillery {{ background: #f0e6d2; color: #8b6914; }}
        .type-city {{ background: #e0e8f0; color: #4a6785; }}
        .type-nature {{ background: #e0f0e0; color: #3a7a3a; }}
        .type-poi {{ background: #f0e0f0; color: #7a3a7a; }}
        .type-travel_stop {{ background: #f0f0e0; color: #7a7a3a; }}

        /* Popup-Styles */
        .map-popup {{ min-width: 220px; max-width: 300px; }}
        .map-popup h3 {{ font-size: 1em; margin: 0 0 6px; color: var(--whisky-brown); }}
        .map-popup .popup-type {{
            font-size: 0.75em; display: inline-block; padding: 1px 6px;
            border-radius: 8px; margin-bottom: 6px;
        }}
        .map-popup .popup-photos {{ display: flex; gap: 4px; margin: 8px 0; overflow-x: auto; }}
        .map-popup .popup-photos img {{
            width: 90px; height: 65px; object-fit: cover; border-radius: 4px; cursor: pointer;
        }}
        .map-popup .popup-years {{ font-size: 0.8em; color: #666; margin: 4px 0; }}
        .map-popup .popup-articles {{ margin-top: 6px; }}
        .map-popup .popup-articles a {{
            display: block; font-size: 0.82em; color: var(--whisky-amber);
            text-decoration: none; padding: 3px 0; border-top: 1px solid #eee;
        }}
        .map-popup .popup-articles a:hover {{ color: var(--whisky-brown); }}

        /* Leaflet-Anpassungen */
        .leaflet-popup-content-wrapper {{ border-radius: 10px; }}
        .marker-cluster-small {{ background-color: rgba(181, 137, 52, 0.6); }}
        .marker-cluster-small div {{ background-color: rgba(181, 137, 52, 0.8); color: #fff; }}
        .marker-cluster-medium {{ background-color: rgba(139, 105, 20, 0.6); }}
        .marker-cluster-medium div {{ background-color: rgba(139, 105, 20, 0.8); color: #fff; }}

        @media (max-width: 768px) {{
            .map-controls {{ flex-direction: column; align-items: flex-start; }}
            .map-stats {{ margin-left: 0; }}
            .location-cards {{ grid-template-columns: 1fr; }}
            #map {{ height: 50vh !important; }}
        }}
    </style>

    <script>
    (function() {{
        const BASE_URL = '{base_url}';
        // Fuer lokales Testen: Daten und Bilder relativ laden
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
            poi: 'Sehenswuerdigkeit', travel_stop: 'Reisestopp'
        }};

        let mapData = null;
        let map = null;
        let markerCluster = null;
        let allMarkers = [];
        let routeLayers = [];

        // Karte initialisieren
        map = L.map('map').setView(CENTER, ZOOM);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            maxZoom: 18
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
            html += ' <span style="font-size:0.75em;color:#888">' + loc.region + ', ' + loc.country + '</span>';

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
            locations.forEach(loc => {{
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
            // Nur Destillerien und POIs mit Artikeln anzeigen
            const featured = locations.filter(l =>
                l.type === 'distillery' || (l.articles && l.articles.length > 0)
            ).slice(0, 24);

            container.innerHTML = featured.map(loc => {{
                const photoSrc = (loc.photos && loc.photos.length > 0)
                    ? LOCAL_BASE + loc.photos[0].src
                    : '';
                const imgHtml = photoSrc
                    ? '<img class="loc-card-img" src="' + photoSrc + '" alt="' + loc.name + '" loading="lazy">'
                    : '<div class="loc-card-img" style="background:linear-gradient(135deg,var(--whisky-amber),var(--whisky-brown));display:flex;align-items:center;justify-content:center;font-size:2em;">🥃</div>';
                return '<div class="loc-card" data-loc-id="' + loc.id + '">'
                    + imgHtml
                    + '<div class="loc-card-body">'
                    + '<div class="loc-card-name">' + loc.name + '</div>'
                    + '<div class="loc-card-meta">' + loc.region + ', ' + loc.country + (loc.years_visited && loc.years_visited.length ? ' &bull; ' + loc.years_visited.join(', ') : '') + '</div>'
                    + '<span class="loc-card-type type-' + loc.type + '">' + (TYPE_LABELS[loc.type] || loc.type) + '</span>'
                    + '</div></div>';
            }}).join('');

            // Klick auf Karte -> Location auf Karte anzeigen
            container.querySelectorAll('.loc-card').forEach(card => {{
                card.addEventListener('click', () => {{
                    const locId = card.dataset.locId;
                    const marker = allMarkers.find(m => m._locData.id === locId);
                    if (marker) {{
                        map.setView(marker.getLatLng(), 12);
                        markerCluster.zoomToShowLayer(marker, () => {{
                            marker.openPopup();
                        }});
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
            const year = document.getElementById('filter-year').value;
            const region = document.getElementById('filter-region').value;
            const country = document.getElementById('filter-country').value;
            const types = ['distillery', 'city', 'nature', 'poi', 'travel_stop']
                .filter(t => document.getElementById('toggle-' + t).checked);

            return locations.filter(loc => {{
                if (year && !loc.years_visited.includes(parseInt(year))) return false;
                if (region && loc.region !== region) return false;
                if (country && loc.country !== country) return false;
                if (!types.includes(loc.type)) return false;
                return true;
            }});
        }}

        function applyFilters() {{
            if (!mapData) return;
            const visible = getVisibleLocations(mapData.locations);
            markerCluster.clearLayers();
            allMarkers.forEach(m => {{
                if (visible.includes(m._locData)) {{
                    markerCluster.addLayer(m);
                }}
            }});

            renderCards(visible);
            updateStats(mapData.locations);
        }}

        // Filter-Events
        ['filter-year', 'filter-region', 'filter-country'].forEach(id => {{
            document.getElementById(id).addEventListener('change', applyFilters);
        }});
        ['toggle-distillery', 'toggle-city', 'toggle-nature', 'toggle-poi',
         'toggle-travel_stop'].forEach(id => {{
            document.getElementById(id).addEventListener('change', applyFilters);
        }});

        // URL-Parameter verarbeiten
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

    return _base_template().format(
        title="Karte",
        site_name=site_name,
        meta_description="Interaktive Karte aller Destillerien, Reiseziele und Orte aus dem Whisky Magazin",
        keywords="Whisky Karte, Destillerien Schottland, Reisekarte, Whisky Trail",
        og_description="18 Jahre Whisky-Reisen auf einer interaktiven Karte: Destillerien, Staedte und Routen",
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/karte.html",
        base_url=base_url,
        content=content,
    )


def build_sitemap(articles, config):
    """Erstellt eine XML-Sitemap."""
    base_url = config["site"].get("base_url", "")
    urls = [f"{base_url}/index.html", f"{base_url}/karte.html"]

    for article in articles:
        slug = article.get("meta", {}).get("slug", "")
        if slug:
            urls.append(f"{base_url}/artikel/{slug}.html")

    xml_entries = ""
    for url in urls:
        xml_entries += f"  <url><loc>{url}</loc></url>\n"

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_entries}</urlset>"""


# ============================================================
# Haupt-Build-Funktion
# ============================================================

def build_site(config):
    """Baut die komplette Website neu auf."""
    print("\n  Website wird gebaut...")

    # Verzeichnisse erstellen
    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / "artikel").mkdir(exist_ok=True)
    (SITE_DIR / "kategorie").mkdir(exist_ok=True)

    # Alle Artikel laden
    articles = load_all_articles()
    print(f"  {len(articles)} Artikel gefunden.")

    if not articles:
        print("  HINWEIS: Noch keine Artikel vorhanden.")
        print("  Generiere zuerst Artikel mit Option [2] oder [3].")

    # 1. Artikelseiten erstellen
    for article in articles:
        slug = article.get("meta", {}).get("slug", "")
        if not slug:
            continue
        html = build_article_page(article, config)
        filepath = SITE_DIR / "artikel" / f"{slug}.html"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"  {len(articles)} Artikelseiten erstellt.")

    # 2. Startseite erstellen
    index_html = build_index_page(articles, config)
    with open(SITE_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    print("  Startseite erstellt.")

    # 3. Kategorieseiten erstellen
    categories = set(a.get("category", "Allgemein") for a in articles)
    # Standard-Kategorien immer erstellen
    categories.update(["Whisky", "Reise", "Lifestyle", "Natur", "Urlaub"])
    for cat in categories:
        cat_html = build_category_page(cat, articles, config)
        filepath = SITE_DIR / "kategorie" / f"{cat.lower()}.html"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(cat_html)
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
        with open(SITE_DIR / "karte.html", "w", encoding="utf-8") as f:
            f.write(map_html)
        print("  Kartenseite erstellt.")
    except Exception as e:
        print(f"  WARNUNG: Kartenseite konnte nicht erstellt werden: {e}")

    # 6. Sitemap erstellen
    sitemap_xml = build_sitemap(articles, config)
    with open(SITE_DIR / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_xml)
    print("  Sitemap erstellt.")

    print(f"\n  Website bereit unter: {SITE_DIR}")
    print(f"  Oeffne {SITE_DIR / 'index.html'} im Browser um sie zu sehen!")

    return str(SITE_DIR)
