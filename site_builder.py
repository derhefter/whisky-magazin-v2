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
            background: linear-gradient(135deg, var(--whisky-light), var(--whisky-cream));
            padding: 2px 6px;
            border-radius: 4px;
            text-decoration: none !important;
            border-bottom: 2px solid var(--whisky-gold);
        }}
        .affiliate-link:hover {{
            background: var(--whisky-gold);
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

        /* --- RESPONSIVE --- */
        @media (max-width: 600px) {{
            .hero h1 {{ font-size: 1.8em; }}
            .article-header h1 {{ font-size: 1.5em; }}
            .article-body {{ padding: 24px; }}
            .header-inner {{ flex-direction: column; gap: 12px; }}
            nav a {{ margin-left: 12px; }}
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

    related_html = ""
    for _, a in scored[:max_count]:
        slug = a.get("meta", {}).get("slug", "")
        title = a["title"]
        related_html += f'<li><a href="{base_url}/artikel/{slug}.html">{title}</a></li>\n'

    # Falls weniger als max_count gefunden, mit neuesten Artikeln auffuellen
    used_slugs = {current_slug} | {a.get("meta", {}).get("slug", "") for _, a in scored[:max_count]}
    if len(scored) < max_count:
        for a in all_articles:
            if len(scored) + (max_count - len(scored)) <= 0:
                break
            slug = a.get("meta", {}).get("slug", "")
            if slug and slug not in used_slugs:
                title = a["title"]
                related_html += f'<li><a href="{base_url}/artikel/{slug}.html">{title}</a></li>\n'
                used_slugs.add(slug)
                if related_html.count("<li>") >= max_count:
                    break

    if related_html:
        return f'<div class="related-box"><h3>Das könnte dich auch interessieren</h3><ul>{related_html}</ul></div>'
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


def build_article_page(article, config):
    """Erstellt die HTML-Seite fuer einen einzelnen Artikel."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    meta = article.get("meta", {})
    date_display = _german_date(article.get("date", ""))

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
        if a.get("meta", {}).get("slug") != meta.get("slug"):
            s = a.get("meta", {}).get("slug", "")
            t = a["title"]
            recent_html += f'<li><a href="{base_url}/artikel/{s}.html">{t}</a></li>\n'

    # Related-Box: GPT-generierte Platzhalter durch echte Links ersetzen
    related_html = _find_related_articles(article, all_articles, base_url, max_count=4)
    article_html = _replace_related_box(article['html_content'], related_html)

    content = f"""
    <div class="article-header">
        <h1>{article['title']}</h1>
        <div class="meta-line">{date_display} &bull; {article.get('category', 'Allgemein')} &bull; von {config['site']['author']}</div>
    </div>
    <div class="container">
        <div class="content-grid">
            <main>
                <div class="article-body">
                    {article_html}
                    {tags_html}
                </div>
            </main>
            <aside class="sidebar">
                <div class="sidebar-box">
                    <h3>Neueste Artikel</h3>
                    <ul>{recent_html}</ul>
                </div>
                <div class="cta-box">
                    <h3>Whisky entdecken</h3>
                    <p>Finde deinen nächsten Lieblings-Dram</p>
                    <a href="https://www.amazon.de/s?k=single+malt+whisky&tag={config.get('affiliate_links', {}).get('amazon_tag', 'whiskyreise74-21')}" target="_blank" rel="noopener noreferrer">Whisky bei Amazon &#8594;</a>
                </div>
                <div class="cta-box" style="margin-top: 20px;">
                    <h3>Schottland-Reise planen</h3>
                    <p>Fähren, Flüge & Hotels</p>
                    <a href="{config.get('affiliate_links', {}).get('travel_links', {}).get('faehre', '#')}" target="_blank" rel="noopener noreferrer">Fähre buchen &#8594;</a>
                </div>
            </aside>
        </div>
    </div>"""

    return _base_template().format(
        title=article["title"],
        site_name=site_name,
        meta_description=meta.get("meta_description", article["title"]),
        keywords=meta.get("keywords", ""),
        og_description=meta.get("og_description", meta.get("meta_description", "")),
        canonical_url=f"{base_url}/artikel/{meta.get('slug', '')}.html",
        base_url=base_url,
        content=content,
    )


def build_index_page(articles, config):
    """Erstellt die Startseite mit Artikeluebersicht."""
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    tagline = config["site"]["tagline"]

    # Artikelkarten
    cards_html = ""
    for article in articles[:12]:
        meta = article.get("meta", {})
        slug = meta.get("slug", "")
        teaser = meta.get("teaser", meta.get("meta_description", ""))
        date_display = _german_date(article.get("date", ""))
        category = article.get("category", "Allgemein")

        cards_html += f"""
        <div class="article-card">
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
    
    filtered = [a for a in articles if belongs_to_category(a, category_name)]
    cards_html = ""
    for article in filtered:
        meta = article.get("meta", {})
        slug = meta.get("slug", "")
        teaser = meta.get("teaser", meta.get("meta_description", ""))
        date_display = _german_date(article.get("date", ""))

        cards_html += f"""
        <div class="article-card">
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
        canonical_url=f"{base_url}/kategorie/{category_name.lower()}.html",
        base_url=base_url,
        content=content,
    )


def build_sitemap(articles, config):
    """Erstellt eine XML-Sitemap."""
    base_url = config["site"].get("base_url", "")
    urls = [f"{base_url}/index.html"]

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

    # 4. Sitemap erstellen
    sitemap_xml = build_sitemap(articles, config)
    with open(SITE_DIR / "sitemap.xml", "w", encoding="utf-8") as f:
        f.write(sitemap_xml)
    print("  Sitemap erstellt.")

    print(f"\n  Website bereit unter: {SITE_DIR}")
    print(f"  Oeffne {SITE_DIR / 'index.html'} im Browser um sie zu sehen!")

    return str(SITE_DIR)
