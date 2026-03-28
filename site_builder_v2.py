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
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Bitter:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Work+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #FAF8F4;
            --bg-surface: #F0EBE1;
            --bg-elevated: #FFFFFF;
            --text-primary: #2A2520;
            --text-secondary: #6B5E52;
            --accent-copper: #B8762E;
            --accent-terra: #C4583A;
            --accent-sage: #5B7B6A;
            --accent-muted: #8A7D6B;
            --border: #DDD5C8;
            --shadow-sm: 0 2px 12px rgba(42,37,32,0.06);
            --shadow-hover: 0 4px 20px rgba(42,37,32,0.10);
            --radius-sm: 6px;
            --radius-pill: 24px;
            --max-width: 1100px;
            --article-max: 720px;
            --sidebar-width: 300px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Work Sans', -apple-system, BlinkMacSystemFont, sans-serif;
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
            background: rgba(250,248,244,0.92);
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
            font-family: 'Bitter', Georgia, serif;
            font-weight: 600;
            font-size: 22px;
            color: var(--text-primary);
            text-decoration: none;
            letter-spacing: -0.5px;
        }}
        .site-logo .logo-dot {{
            color: var(--accent-copper);
            font-size: 28px;
            line-height: 1;
        }}
        .site-logo .logo-magazin {{
            font-family: 'Work Sans', sans-serif;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-left: 4px;
        }}
        .site-nav {{ display: flex; align-items: center; gap: 28px; }}
        .site-nav a {{
            font-family: 'Work Sans', sans-serif;
            font-size: 14px;
            font-weight: 500;
            color: var(--text-secondary);
            text-decoration: none;
            transition: color 0.2s;
        }}
        .site-nav a:hover {{ color: var(--accent-copper); }}

        /* --- HEADINGS --- */
        h1, h2, h3, h4 {{
            font-family: 'Bitter', Georgia, serif;
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
            background: var(--accent-terra);
        }}
        h3 {{ font-size: 18px; font-weight: 600; }}

        /* --- BUTTONS --- */
        .btn {{ display: inline-block; padding: 10px 24px; font-family: 'Work Sans', sans-serif; font-size: 14px; font-weight: 500; border-radius: var(--radius-sm); text-decoration: none; cursor: pointer; transition: all 0.2s; border: none; }}
        .btn-primary {{ background: var(--accent-copper); color: #fff; }}
        .btn-primary:hover {{ background: #a06828; }}
        .btn-ghost {{ background: transparent; border: 1.5px solid var(--accent-copper); color: var(--accent-copper); }}
        .btn-ghost:hover {{ background: var(--accent-copper); color: #fff; }}
        .btn-secondary {{ background: transparent; border: 1.5px solid var(--accent-sage); color: var(--accent-sage); }}
        .btn-secondary:hover {{ background: var(--accent-sage); color: #fff; }}

        /* --- BADGES --- */
        .badge {{ display: inline-block; padding: 4px 12px; font-family: 'Work Sans', sans-serif; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; border-radius: var(--radius-pill); }}
        .badge-copper {{ background: var(--accent-copper); color: #fff; }}
        .badge-terra {{ background: var(--accent-terra); color: #fff; }}
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
        .card-title {{ font-family: 'Bitter', serif; font-size: 18px; font-weight: 600; margin: 0 0 8px; line-height: 1.3; }}
        .card-title a {{ color: var(--text-primary); text-decoration: none; }}
        .card-title a:hover {{ color: var(--accent-copper); }}
        .card-meta {{ font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }}
        .card-teaser {{ font-size: 15px; color: var(--text-secondary); line-height: 1.6; }}

        /* --- BLOCKQUOTE --- */
        blockquote {{
            font-family: 'Bitter', serif;
            font-style: italic;
            font-size: 18px;
            color: var(--text-primary);
            border-left: 3px solid var(--accent-copper);
            padding: 4px 0 4px 24px;
            margin: 32px 0;
            background: none;
        }}

        /* --- HERO (nur Startseite) --- */
        .hero {{
            background: linear-gradient(135deg, var(--text-primary) 0%, var(--text-primary) 50%, var(--accent-copper) 100%);
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
            font-family: 'Work Sans', sans-serif;
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
            font-family: 'Bitter', serif;
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
            color: var(--accent-copper);
        }}
        .article-card .teaser {{
            color: var(--text-secondary);
            font-size: 15px;
            margin-bottom: 16px;
            line-height: 1.6;
        }}
        .read-more {{
            font-family: 'Work Sans', sans-serif;
            color: var(--accent-copper);
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
            font-family: 'Work Sans', sans-serif;
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
            color: var(--accent-copper);
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
            font-family: 'Bitter', serif;
            font-style: italic;
            font-size: 18px;
            color: var(--text-primary);
            border-left: 3px solid var(--accent-copper);
            padding: 4px 0 4px 24px;
            margin: 32px 0;
            background: none;
        }}
        .article-body a {{
            color: var(--accent-copper);
            text-decoration: underline;
            text-decoration-color: var(--accent-copper);
        }}
        .article-body a:hover {{ color: var(--text-primary); }}

        .affiliate-link {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: var(--accent-copper);
            color: #fff !important;
            padding: 3px 10px 3px 8px;
            border-radius: var(--radius-sm);
            text-decoration: none !important;
            border-bottom: none !important;
            font-size: 14px;
            font-weight: 500;
            font-family: 'Work Sans', sans-serif;
            transition: background 0.2s, transform 0.1s;
            white-space: nowrap;
        }}
        .affiliate-link::before {{ content: "→"; font-size: 0.8em; }}
        .affiliate-link:hover {{
            background: #a06828;
            transform: translateY(-1px);
            color: #fff !important;
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
            font-family: 'Work Sans', sans-serif;
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
            font-family: 'Bitter', Georgia, serif;
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
        .sidebar-box a:hover {{ color: var(--accent-copper); }}

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
            background: var(--accent-copper);
            color: #fff;
        }}

        .cta-box {{
            background: var(--text-primary);
            color: var(--bg-surface);
            border-radius: var(--radius-sm);
            padding: 28px;
            text-align: center;
        }}
        .cta-box h3 {{ color: var(--accent-copper); border: none; padding-left: 0; }}
        .cta-box h3::before {{ display: none; }}
        .cta-box p {{ font-size: 14px; margin: 10px 0 16px; opacity: 0.85; }}
        .cta-box a {{
            display: inline-block;
            background: var(--accent-copper);
            color: #fff;
            padding: 10px 28px;
            border-radius: var(--radius-sm);
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            font-family: 'Work Sans', sans-serif;
        }}
        .cta-box a:hover {{ background: #a06828; }}

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
        .footer-logo {{ font-family: 'Bitter', serif; font-weight: 600; font-size: 20px; color: var(--bg-primary); margin-bottom: 12px; }}
        .footer-tagline {{ font-size: 14px; color: var(--accent-muted); line-height: 1.6; }}
        .footer-nav h4 {{ font-family: 'Bitter', serif; font-size: 14px; font-weight: 600; color: var(--bg-primary); margin-bottom: 16px; text-transform: uppercase; letter-spacing: 1px; padding-left: 0; }}
        .footer-nav h4::before {{ display: none; }}
        .footer-nav a {{ display: block; font-size: 14px; color: var(--accent-muted); text-decoration: none; margin-bottom: 8px; transition: color 0.2s; }}
        .footer-nav a:hover {{ color: var(--accent-copper); }}
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
        .footer-quote {{ font-family: 'Bitter', serif; font-style: italic; font-size: 14px; color: var(--accent-muted); }}

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
            font-size: 3em; color: var(--accent-copper);
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
        }}

        /* --- ARTICLE HERO IMAGE --- */
        .article-hero-image {{
            width: 100%; max-height: 480px; object-fit: cover; display: block;
        }}
        .article-image-credit {{
            font-family: 'Work Sans', sans-serif;
            font-size: 12px; color: var(--text-secondary);
            text-align: right; padding: 4px 8px; background: var(--bg-surface);
        }}
        .article-image-credit a {{ color: var(--text-secondary); }}

        /* --- EMPFEHLUNG BOX --- */
        .empfehlung-box {{
            border-left: 4px solid var(--accent-copper);
            background: var(--bg-surface);
            border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
            padding: 24px 28px; margin: 32px 0;
            display: flex; align-items: flex-start; gap: 16px;
        }}
        .empfehlung-box h3 {{
            font-family: 'Bitter', serif;
            font-size: 16px;
            margin: 0 0 8px;
            padding-left: 0;
        }}
        .empfehlung-box h3::before {{ display: none; }}
        .empfehlung-box .emp-icon {{ font-size: 2em; flex-shrink: 0; margin-top: 2px; }}
        .empfehlung-box .emp-content {{ flex: 1; }}
        .empfehlung-box .emp-title {{
            font-family: 'Bitter', serif; font-weight: 600;
            color: var(--text-primary); font-size: 16px; margin-bottom: 6px;
        }}
        .empfehlung-box .emp-text {{
            font-size: 14px; color: var(--text-secondary); margin-bottom: 12px;
            font-family: 'Work Sans', sans-serif;
        }}
        .empfehlung-box .emp-cta {{
            display: inline-block; background: var(--accent-copper);
            color: #fff !important; padding: 8px 20px; border-radius: var(--radius-sm);
            text-decoration: none !important; font-weight: 500; font-size: 14px;
            font-family: 'Work Sans', sans-serif;
            transition: background 0.2s; margin-right: 8px; margin-bottom: 4px;
        }}
        .empfehlung-box .emp-cta:hover {{ background: #a06828; color: #fff !important; }}

        /* --- SHARE BUTTONS --- */
        .share-bar {{
            display: flex; gap: 10px; margin: 28px 0 20px;
            flex-wrap: wrap; align-items: center;
        }}
        .share-label {{
            font-size: 13px; color: var(--text-secondary);
            font-family: 'Work Sans', sans-serif;
        }}
        .share-btn {{
            display: inline-flex; align-items: center; gap: 6px;
            padding: 8px 16px; border-radius: var(--radius-pill);
            text-decoration: none !important; font-size: 12px;
            font-family: 'Work Sans', sans-serif;
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
            font-family: 'Work Sans', sans-serif;
            font-size: 13px; color: var(--text-secondary);
        }}
        .breadcrumb-inner {{ max-width: var(--max-width); margin: 0 auto; }}
        .breadcrumb a {{ color: var(--text-secondary); text-decoration: none; }}
        .breadcrumb a:hover {{ color: var(--accent-copper); }}

        /* --- RELATED GRID --- */
        .related-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 12px; }}
        .related-item {{
            background: var(--bg-primary); border-radius: var(--radius-sm);
            padding: 12px 14px; text-decoration: none !important;
            border-left: 3px solid var(--accent-copper);
            color: var(--text-primary) !important; font-size: 14px;
            line-height: 1.4; transition: background 0.2s, border-color 0.2s; display: block;
        }}
        .related-item:hover {{ background: var(--bg-surface); border-left-color: var(--accent-terra); }}

        /* --- PERSONAL PHOTO BADGE --- */
        .personal-photo-wrapper {{ position: relative; display: block; }}
        .personal-photo-badge {{
            position: absolute; bottom: 8px; left: 8px;
            background: rgba(42,37,32,0.85); color: var(--accent-copper);
            font-size: 12px; padding: 2px 8px; border-radius: var(--radius-pill);
            font-family: 'Work Sans', sans-serif;
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
            font-family: 'Work Sans', sans-serif;
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
        .author-info h4 {{ font-family: 'Bitter', serif; margin: 0 0 4px; font-size: 16px; padding-left: 0; }}
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
        .article-body {{ max-width: var(--article-max); }}
        .article-sidebar {{ position: relative; }}
        .sidebar-sticky {{ position: sticky; top: 88px; }}
        .tasting-panel {{
            background: var(--bg-surface);
            border-radius: var(--radius-sm);
            padding: 24px;
            margin-bottom: 24px;
        }}
        .tasting-panel h3 {{
            font-family: 'Work Sans', sans-serif;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--accent-copper);
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
        .trust-stat-number {{ font-family: 'Bitter', serif; font-size: 32px; font-weight: 700; color: var(--accent-copper); }}
        .trust-stat-label {{ font-size: 14px; color: var(--text-secondary); margin-top: 4px; }}

        /* --- RESPONSIVE --- */
        @media (max-width: 768px) {{
            .footer-inner {{ grid-template-columns: 1fr; gap: 32px; }}
            .footer-bottom {{ flex-direction: column; gap: 8px; text-align: center; }}
            .site-nav {{ gap: 16px; }}
            .newsletter-form {{ flex-direction: column; }}
            .trust-stats {{ gap: 24px; }}
        }}
        @media (max-width: 600px) {{
            .hero h1 {{ font-size: 1.8em; }}
            .article-header h1 {{ font-size: 1.5em; }}
            .article-body {{ padding: 24px; }}
            .header-inner {{ flex-direction: column; gap: 12px; }}
            .site-nav a {{ margin-left: 0; }}
            .card-image-wrapper, .card-image, .card-image-placeholder {{ height: 160px; }}
            .article-hero-image {{ max-height: 240px; }}
            .related-grid {{ grid-template-columns: 1fr; }}
            .empfehlung-box {{ flex-direction: column; gap: 8px; }}
        }}
    </style>
</head>
<body>
    <header class="site-header">
        <div class="header-inner">
            <a href="/" class="site-logo">whisky<span class="logo-dot">.</span><span class="logo-magazin">Magazin</span></a>
            <nav class="site-nav">
                <a href="/">Startseite</a>
                <a href="/kategorie/whisky.html">Whisky</a>
                <a href="/kategorie/reise.html">Reisen</a>
                <a href="/karte.html">Karte</a>
            </nav>
        </div>
    </header>
    {content}
    <footer class="site-footer">
        <div class="footer-inner">
            <div>
                <div class="footer-logo">whisky<span style="color:var(--accent-copper)">.</span>Magazin</div>
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
                <a href="#">Über uns</a>
                <a href="#">Newsletter</a>
                <a href="#">Datenschutz</a>
                <a href="#">Impressum</a>
            </div>
        </div>
        <div class="footer-bottom">
            <span>&copy; 2007–2026 Whisky Magazin</span>
            <span class="footer-quote">„Der beste Whisky ist der, den man mit Freunden teilt."</span>
        </div>
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


def _find_related_articles(current_article, all_articles, base_url, max_count=3):
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

    # Falls weniger als max_count gefunden, mit neuesten Artikeln auffuellen
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
            '<h3 style="padding-left:0;">🏴󠁧󠁢󠁳󠁣󠁴󠁿 Reise planen</h3>'
            '<p>Fähre, Hotel und mehr für deine Schottland-Reise – alles auf einen Blick.</p>'
            f'<a href="{faehre}" class="btn btn-primary" style="margin-top:12px;margin-right:8px;" target="_blank" rel="nofollow noopener">Fähre buchen</a>'
            f'<a href="{hotel}" class="btn btn-primary" style="margin-top:12px;" target="_blank" rel="nofollow noopener">Hotels ansehen</a>'
            '</div>'
        )
    else:
        # Erstes Keyword aus Tags für Amazon-Suche
        tags = article.get('tags', [])
        keyword = tags[0].lower().replace(' ', '+') if tags else 'single+malt+whisky'
        box = (
            '<div class="empfehlung-box">'
            '<h3 style="padding-left:0;">🥃 Diesen Whisky bestellen</h3>'
            '<p>Die im Artikel erwähnten Whiskys findest du bei Amazon – oft mit Prime-Lieferung.</p>'
            f'<a href="https://www.amazon.de/s?k={keyword}+whisky&tag={amazon_tag}" class="btn btn-primary" style="margin-top:12px;" target="_blank" rel="nofollow noopener">Bei Amazon ansehen</a>'
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
               style="color:var(--accent-copper); text-decoration:none; font-size:0.9em;
                      font-family:'Work Sans',sans-serif;">
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

    # Tags als badge-outline
    tags_html = ""
    if article.get("tags"):
        tag_badges = " ".join(
            f'<span class="badge badge-outline">{tag}</span>' for tag in article["tags"]
        )
        tags_html = f'<div style="margin:32px 0;">{tag_badges}</div>'

    # Sidebar mit neuesten Artikeln (kept for data, used in sidebar CTA)
    all_articles = load_all_articles()

    # Related-Box + Empfehlung-Box
    related_html = _find_related_articles(article, all_articles, base_url, max_count=3)
    article_html = _replace_related_box(article['html_content'], "")
    article_html = _inject_empfehlung_boxes(article_html, article, config)

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

    # Mini-Map fuer Artikel mit Ortsbezug
    mini_map_html = ""
    if has_locations:
        mini_map_html = _build_mini_map_html(article, base_url)

    # Tasting panel (only for Whisky category)
    tasting_panel_html = _build_tasting_panel(article)

    # Mid-article newsletter CTA
    mid_newsletter_html = '''<div style="background:var(--bg-surface);border-radius:var(--radius-sm);padding:32px;text-align:center;margin:40px 0;">
        <h3 style="font-family:'Bitter',serif;font-size:20px;margin:0 0 8px;padding-left:0;">Gefällt dir diese Geschichte?</h3>
        <p style="font-size:14px;color:var(--text-secondary);margin:0 0 16px;">Hol dir die besten Whisky-Stories direkt ins Postfach.</p>
        <form action="#" data-newsletter class="newsletter-form" style="justify-content:center;">
            <input type="email" placeholder="Deine E-Mail" required>
            <button type="submit" class="btn btn-primary">Dabei sein</button>
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
        <a href="/" style="color:var(--accent-copper);text-decoration:none;">Startseite</a>
        <span style="margin:0 8px;">&#8250;</span>
        <a href="/kategorie/{cat_lower}.html" style="color:var(--accent-copper);text-decoration:none;">{category}</a>
        <span style="margin:0 8px;">&#8250;</span>
        <span>{title_breadcrumb}</span>
    </nav>
    <div style="max-width:var(--article-max);margin:0 auto;padding:16px 24px 24px;text-align:center;">
        <span class="badge badge-copper">{category}</span>
        <h1 style="font-size:34px;margin:16px 0 12px;padding-left:0;">{article['title']}</h1>
        <p style="color:var(--text-secondary);font-size:14px;">Von Steffen &amp; Elmar &#183; {date_display} &#183; {reading_time} Min. Lesezeit</p>
        {trust_badge_html}
    </div>
    <div style="max-width:var(--max-width);margin:0 auto;padding:0 24px;">
        {hero_img_html}
    </div>
    <div class="article-layout">
        <article class="article-body">
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
                    <h4 style="font-family:'Bitter',serif;font-size:16px;margin:0 0 8px;padding-left:0;">Schottland-Post</h4>
                    <p style="font-size:13px;color:var(--text-secondary);margin:0 0 16px;">Einmal im Monat die besten Stories.</p>
                    <form action="#" data-newsletter style="display:flex;flex-direction:column;gap:8px;">
                        <input type="email" placeholder="E-Mail" style="padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:13px;font-family:'Work Sans',sans-serif;">
                        <button type="submit" class="btn btn-primary" style="font-size:13px;padding:8px 16px;">Anmelden</button>
                    </form>
                </div>
                {sidebar_cta_html}
            </div>
        </aside>
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

    # Collect categories + tags (needed for region cards)
    categories = {}
    all_tags = set()
    for a in articles:
        cat = a.get("category", "Allgemein")
        categories[cat] = categories.get(cat, 0) + 1
        for tag in a.get("tags", []):
            all_tags.add(tag)

    # --- 1. Hero Intro ---
    hero_html = f"""
    <section class="hero-intro" style="text-align:center; padding:80px 24px 64px;">
        <div class="author-photo" style="width:72px;height:72px;border-radius:50%;background:url('/images/authors-steffen-elmar.jpg') center/cover;margin:0 auto 24px;"></div>
        <h1 style="font-family:'Bitter',serif;font-size:36px;font-weight:700;margin:0 0 16px;">Willkommen im Whisky Magazin</h1>
        <p style="font-size:17px;color:var(--text-secondary);max-width:560px;margin:0 auto 12px;line-height:1.6;">{tagline}</p>
        <p style="font-size:13px;color:var(--accent-muted);text-transform:uppercase;letter-spacing:2px;font-weight:500;">Von Steffen &amp; Elmar — seit 2007 unterwegs</p>
    </section>"""

    # --- 2. Featured Stories Grid ---
    featured_cards_html = ""
    for idx, article in enumerate(articles[:5]):
        meta = article.get("meta", {})
        slug = meta.get("slug", "")
        teaser = meta.get("teaser", meta.get("meta_description", ""))
        date_display = _german_date(article.get("date", ""))
        category = article.get("category", "Allgemein")
        reading_time = _reading_time(article.get("html_content", "")) if article.get("html_content") else 3
        img_url = article.get("image_url", "")
        img_bg = f"background-image:url({img_url});" if img_url else "background:linear-gradient(135deg, var(--bg-surface) 0%, var(--border) 100%);"

        if idx == 0:
            # Featured large card spanning 2 columns
            featured_cards_html += f"""
        <div class="card" style="grid-column:span 2;display:grid;grid-template-columns:1fr 1fr;overflow:hidden;">
            <div class="card-image" style="{img_bg}background-size:cover;background-position:center;min-height:320px;"></div>
            <div class="card-body" style="padding:28px 32px;display:flex;flex-direction:column;justify-content:center;">
                <span class="badge badge-copper">{category}</span>
                <h3 class="card-title" style="font-size:22px;margin-top:12px;"><a href="{base_url}/artikel/{slug}.html">{article['title']}</a></h3>
                <p class="card-meta">{date_display} · {reading_time} Min. Lesezeit</p>
                <p class="card-teaser">{teaser}</p>
                <a href="{base_url}/artikel/{slug}.html" class="btn btn-ghost" style="margin-top:16px;align-self:flex-start;">Weiterlesen</a>
            </div>
        </div>"""
        else:
            # Regular card
            teaser_short = teaser[:120] + "..." if len(teaser) > 120 else teaser
            featured_cards_html += f"""
        <div class="card">
            <div class="card-image" style="{img_bg}background-size:cover;background-position:center;height:200px;"></div>
            <div class="card-body">
                <span class="badge badge-outline">{category}</span>
                <h3 class="card-title"><a href="{base_url}/artikel/{slug}.html">{article['title']}</a></h3>
                <p class="card-meta">{date_display} · {reading_time} Min. Lesezeit</p>
                <p class="card-teaser">{teaser_short}</p>
            </div>
        </div>"""

    stories_html = f"""
    <section style="max-width:var(--max-width);margin:0 auto;padding:0 24px 64px;">
        <h2 style="text-align:center;padding-left:0;font-size:22px;font-weight:600;">Aktuelle Geschichten</h2>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:32px;">
            {featured_cards_html}
        </div>
        <div style="text-align:center;margin-top:32px;">
            <a href="{base_url}/kategorie/whisky.html" class="btn btn-ghost">Alle Geschichten entdecken</a>
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
                stars_html += '<span style="color:var(--accent-copper);font-size:18px;">&#9733;</span>'
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
    <section style="background:var(--bg-surface);padding:64px 24px;">
        <div style="max-width:var(--max-width);margin:0 auto;">
            <p style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:2px;color:var(--accent-copper);margin:0 0 8px;text-align:center;">WHISKY DES MONATS</p>
            <p style="text-align:center;font-size:13px;color:var(--text-secondary);margin:0 0 24px;">{wotm_month}</p>
            <div class="card" style="max-width:720px;margin:0 auto;border-top:3px solid var(--accent-copper);padding:32px 36px;">
                <h3 style="font-family:'Bitter',serif;font-size:28px;font-weight:700;margin:0 0 8px;">{wotm_name}</h3>
                <p style="font-size:14px;color:var(--text-secondary);margin:0 0 20px;letter-spacing:0.5px;">{sub_line}</p>
                <div style="margin:0 0 20px;">
                    <p style="font-size:14px;margin:0 0 6px;"><strong style="color:var(--accent-copper);display:inline-block;width:80px;">Aroma</strong> {wotm_aroma}</p>
                    <p style="font-size:14px;margin:0 0 6px;"><strong style="color:var(--accent-copper);display:inline-block;width:80px;">Geschmack</strong> {wotm_geschmack}</p>
                    <p style="font-size:14px;margin:0 0 6px;"><strong style="color:var(--accent-copper);display:inline-block;width:80px;">Abgang</strong> {wotm_abgang}</p>
                </div>
                <div style="display:flex;align-items:center;gap:12px;margin:0 0 20px;">
                    <div>{stars_html}</div>
                    <span style="font-size:13px;color:var(--text-secondary);">{wotm_wertung}/100</span>
                </div>
                {f'<p style="font-size:15px;font-weight:600;margin:0 0 20px;">Ab ca. {wotm_price} &euro;</p>' if wotm_price else ""}
                <div style="display:flex;flex-wrap:wrap;gap:12px;">{cta_html}</div>
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
    <section style="background:var(--bg-surface);padding:64px 24px;">
        <div style="max-width:var(--max-width);margin:0 auto;">
            <p style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:2px;color:var(--accent-copper);margin:0 0 16px;text-align:center;">Whisky des Monats</p>
            <div class="card" style="display:grid;grid-template-columns:200px 1fr;border-top:3px solid var(--accent-copper);">
                <div class="card-image" style="{w_img_bg}background-size:cover;background-position:center;height:100%;min-height:240px;"></div>
                <div class="card-body" style="padding:28px 32px;">
                    <h3 style="font-family:'Bitter',serif;font-size:22px;margin:0 0 12px;">{whisky_article['title']}</h3>
                    <p style="font-size:15px;color:var(--text-secondary);line-height:1.6;">{w_teaser}</p>
                    <a href="{base_url}/artikel/{w_slug}.html" class="btn btn-primary" style="margin-top:16px;">Jetzt entdecken</a>
                </div>
            </div>
        </div>
    </section>"""

    # --- 4. Newsletter CTA ---
    newsletter_html = """
    <section class="newsletter-section">
        <div class="newsletter-inner">
            <h2 style="font-family:'Bitter',serif;font-size:24px;padding-left:0;">Schottland-Post</h2>
            <p>Die besten Whisky-Geschichten und Reise-Tipps, einmal im Monat. Kostenlos.</p>
            <form class="newsletter-form" action="#" data-newsletter>
                <input type="email" placeholder="Deine E-Mail-Adresse" required>
                <button type="submit" class="btn btn-primary">Anmelden</button>
            </form>
            <p style="font-size:12px;color:var(--accent-muted);margin-top:12px;">Bereits über 2.400 Whisky-Fans lesen mit.</p>
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
                    <h3 style="font-family:'Bitter',serif;font-size:16px;margin:0 0 4px;">{cat_name}</h3>
                    <p style="font-size:13px;color:var(--text-secondary);margin:0;">{count} Artikel</p>
                </div>
            </a>"""

    regions_html = f"""
    <section style="max-width:var(--max-width);margin:0 auto;padding:64px 24px;">
        <h2 style="text-align:center;padding-left:0;font-size:22px;font-weight:600;">Regionen entdecken</h2>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-top:32px;">
            {region_cards_html}
        </div>
    </section>"""

    # --- 6. Trust Section ---
    trust_html = f"""
    <section class="trust-section">
        <div class="trust-stats">
            <div>
                <div class="trust-stat-number">14</div>
                <div class="trust-stat-label">Jahre unterwegs</div>
            </div>
            <div>
                <div class="trust-stat-number">{len(articles)}</div>
                <div class="trust-stat-label">Geschichten</div>
            </div>
            <div>
                <div class="trust-stat-number">88</div>
                <div class="trust-stat-label">Destillerien besucht</div>
            </div>
            <div>
                <div class="trust-stat-number">16</div>
                <div class="trust-stat-label">Reisejahre</div>
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
            <a href="/" style="color:var(--accent-copper);text-decoration:none;">Startseite</a>
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
            <nav class="breadcrumb"><a href="/">Startseite</a> &rsaquo; Karte</nav>
            <h1>Unsere Reisekarte</h1>
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
                <select id="filter-country"><option value="">Alle Länder</option></select>
            </div>
            <div class="filter-group filter-toggles">
                <label class="toggle-label"><input type="checkbox" id="toggle-distillery" checked> Destillerien</label>
                <label class="toggle-label"><input type="checkbox" id="toggle-poi" checked> Sehenswürdigkeiten</label>
            </div>
            <div class="map-stats" id="map-stats"></div>
        </div>
        <div id="map" style="height: 65vh; min-height: 400px; border-radius: 12px; box-shadow: var(--shadow-hover); z-index: 1;"></div>
        <div class="location-directory" id="location-cards"></div>
    </div>

    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>

    <style>
        .map-page {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
        .breadcrumb {{
            font-family: 'Work Sans', sans-serif; font-size: 13px;
            color: var(--text-secondary); margin-bottom: 12px;
        }}
        .breadcrumb a {{ color: var(--accent-copper); text-decoration: none; }}
        .breadcrumb a:hover {{ text-decoration: underline; }}
        .map-header {{ text-align: center; margin-bottom: 20px; padding-top: 16px; }}
        .map-header h1 {{ font-family: 'Bitter', serif; font-size: 2em; color: var(--text-primary); margin-bottom: 8px; font-weight: 700; }}
        .map-subtitle {{ font-family: 'Work Sans', sans-serif; color: var(--text-secondary); font-size: 1.05em; }}
        .map-controls {{
            display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
            padding: 16px; background: var(--bg-elevated); border-radius: var(--radius-sm);
            box-shadow: var(--shadow-sm); margin-bottom: 16px;
        }}
        .filter-group {{ display: flex; align-items: center; gap: 6px; }}
        .filter-group label {{ font-size: 0.85em; color: var(--text-secondary);
            font-family: 'Work Sans', sans-serif; }}
        .filter-group select {{
            padding: 6px 10px; border: 1px solid var(--border); border-radius: var(--radius-sm);
            background: var(--bg-primary); font-size: 0.85em; cursor: pointer;
            font-family: 'Work Sans', sans-serif; color: var(--text-primary);
            transition: border-color 0.2s;
        }}
        .filter-group select:focus {{
            outline: none; border-color: var(--accent-copper);
        }}
        .filter-toggles {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .toggle-label {{
            display: flex; align-items: center; gap: 4px; cursor: pointer;
            font-size: 0.82em !important; white-space: nowrap;
            font-family: 'Work Sans', sans-serif; color: var(--text-secondary);
        }}
        .toggle-label input {{ accent-color: var(--accent-copper); }}
        .map-stats {{
            margin-left: auto; font-size: 0.82em; color: var(--text-secondary);
            font-family: 'Work Sans', sans-serif;
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
            font-family: 'Bitter', serif;
            font-size: 1.1em; font-weight: 600; color: var(--text-primary);
            margin: 0;
        }}
        .dir-section-count {{
            background: var(--accent-copper); color: #fff; font-size: 0.75em;
            padding: 2px 8px; border-radius: 12px; font-weight: bold;
            font-family: 'Work Sans', sans-serif;
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
            border-color: var(--accent-copper); box-shadow: var(--shadow-hover);
            transform: translateY(-2px);
        }}
        .dir-item.type-distillery {{ border-left: 3px solid var(--accent-copper); }}
        .dir-item.type-city {{ border-left: 3px solid var(--accent-sage); }}
        .dir-item.type-nature {{ border-left: 3px solid #5B8C5A; }}
        .dir-item.type-poi {{ border-left: 3px solid var(--accent-terra); }}
        .dir-item.type-travel_stop {{ border-left: 3px solid var(--accent-muted); }}
        .dir-item-name {{
            font-family: 'Bitter', serif;
            font-weight: 600; font-size: 0.92em; color: var(--text-primary);
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .dir-item-region {{
            font-size: 0.75em; color: var(--text-secondary);
            font-family: 'Work Sans', sans-serif;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .dir-item-footer {{
            display: flex; align-items: center; gap: 6px; margin-top: 2px;
        }}
        .dir-item-years {{
            font-size: 0.7em; color: var(--accent-copper); font-weight: 500;
            font-family: 'Work Sans', sans-serif;
        }}
        .dir-item-arts {{
            font-size: 0.7em; color: var(--text-secondary);
            font-family: 'Work Sans', sans-serif;
            margin-left: auto;
        }}
        .dir-empty {{
            color: var(--text-secondary); font-size: 0.9em; font-style: italic;
            padding: 8px 0;
        }}
        .type-distillery {{ background: var(--bg-surface); color: var(--accent-copper); }}
        .type-city {{ background: rgba(91,123,106,0.12); color: var(--accent-sage); }}
        .type-nature {{ background: rgba(91,140,90,0.12); color: #5B8C5A; }}
        .type-poi {{ background: rgba(196,88,58,0.12); color: var(--accent-terra); }}
        .type-travel_stop {{ background: rgba(138,125,107,0.12); color: var(--accent-muted); }}

        /* Popup-Styles */
        .map-popup {{ min-width: 220px; max-width: 300px; font-family: 'Work Sans', sans-serif; }}
        .map-popup h3 {{ font-family: 'Bitter', serif; font-size: 1em; font-weight: 600; margin: 0 0 6px; color: var(--text-primary); }}
        .map-popup .popup-type {{
            font-family: 'Work Sans', sans-serif;
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
            display: block; font-size: 0.82em; color: var(--accent-copper);
            text-decoration: none; padding: 3px 0; border-top: 1px solid var(--border);
        }}
        .map-popup .popup-articles a:hover {{ color: var(--text-primary); }}

        /* Leaflet-Anpassungen */
        .leaflet-popup-content-wrapper {{ border-radius: var(--radius-sm); box-shadow: var(--shadow-hover); }}
        .marker-cluster-small {{ background-color: rgba(184, 118, 46, 0.5); }}
        .marker-cluster-small div {{ background-color: rgba(184, 118, 46, 0.8); color: #fff; font-family: 'Work Sans', sans-serif; }}
        .marker-cluster-medium {{ background-color: rgba(184, 118, 46, 0.6); }}
        .marker-cluster-medium div {{ background-color: rgba(184, 118, 46, 0.9); color: #fff; font-family: 'Work Sans', sans-serif; }}

        @media (max-width: 768px) {{
            .map-controls {{ flex-direction: column; align-items: flex-start; }}
            .map-stats {{ margin-left: 0; }}
            .dir-items {{ flex-direction: column; }}
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

            const SECTIONS = [
                {{ key: 'distillery', icon: '🥃', label: 'Destillerien' }},
                {{ key: 'poi',        icon: '📍', label: 'Sehenswürdigkeiten' }},
            ];

            let html = '';
            SECTIONS.forEach(sec => {{
                const items = locations
                    .filter(l => l.type === sec.key)
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
            const year = document.getElementById('filter-year').value;
            const region = document.getElementById('filter-region').value;
            const country = document.getElementById('filter-country').value;
            // Nur Destillerien und Sehenswürdigkeiten (poi) anzeigen
            const types = ['distillery', 'poi']
                .filter(t => document.getElementById('toggle-' + t) && document.getElementById('toggle-' + t).checked);

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
        ['toggle-distillery', 'toggle-poi'].forEach(id => {{
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
        og_description="18 Jahre Whisky-Reisen auf einer interaktiven Karte: Destillerien, Städte und Routenn",
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/karte.html",
        base_url=base_url,
        content=content,
    )


def _push_to_v2_repo(project_dir):
    """Kopiert site-v2/ ins whisky-magazin-v2 Repo und pusht zu GitHub."""
    try:
        v2_repo = Path("C:/Users/steff/Documents lokal/Business-Ideen/whisky-magazin-v2")
        if not v2_repo.exists():
            print("  WARNUNG: whisky-magazin-v2 Verzeichnis nicht gefunden, Push uebersprungen.")
            return

        src_dir = Path(project_dir) / "site-v2"
        if not src_dir.exists():
            print("  WARNUNG: site-v2 Verzeichnis nicht gefunden, Push uebersprungen.")
            return

        # Copy all files from site-v2/ to whisky-magazin-v2/, excluding .git
        for item in src_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(src_dir)
                dest = v2_repo / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(item), str(dest))

        # Git add, commit, push
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        repo_str = str(v2_repo)
        subprocess.run(["git", "-C", repo_str, "add", "."], check=True, capture_output=True)
        result = subprocess.run(
            ["git", "-C", repo_str, "commit", "-m", f"Auto-update V2: {timestamp}"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            subprocess.run(["git", "-C", repo_str, "push"], check=True, capture_output=True)
            print(f"  V2 gepusht nach GitHub ({timestamp})")
        else:
            # Nothing to commit
            print("  V2: Keine Aenderungen zum Pushen.")
    except Exception as e:
        print(f"  WARNUNG: V2 Push fehlgeschlagen: {e}")


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

    # 7. Push to V2 GitHub repo
    _push_to_v2_repo(str(PROJECT_DIR))

    return str(SITE_DIR)
