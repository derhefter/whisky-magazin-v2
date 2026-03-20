"""
Content-Generator: Erstellt SEO-optimierte Whisky- und Reise-Artikel
mithilfe der OpenAI API. Gibt strukturierte Artikel-Daten zurück.
"""

import json
import re
import time
from datetime import datetime
from openai import OpenAI


def _call_openai_with_retry(client, max_retries=3, **kwargs):
    """Ruft die OpenAI API auf mit automatischer Wiederholung bei Fehlern."""
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if any(kw in error_str for kw in ["rate_limit", "429", "500", "502", "503", "timeout", "overloaded"]):
                wait_time = (2 ** attempt) * 5
                print(f"    API-Fehler (Versuch {attempt + 1}/{max_retries}): {e}")
                print(f"    Warte {wait_time} Sekunden...")
                time.sleep(wait_time)
            else:
                raise
    raise Exception(f"OpenAI API nach {max_retries} Versuchen fehlgeschlagen.")


def _build_article_prompt(topic, affiliate_links, content_settings):
    """Erstellt den Prompt für die KI-Artikelgenerierung."""

    shop_links = []
    for shop in affiliate_links.get("whisky_shops", []):
        shop_links.append(f"- {shop['name']}: {shop['url_template']}")

    travel_links = []
    for name, url in affiliate_links.get("travel_links", {}).items():
        travel_links.append(f"- {name}: {url}")

    article_type = topic.get("type", "article")
    type_instructions = {
        "guide": "Schreibe einen umfassenden, praktischen Reiseführer/Guide mit konkreten Tipps, Empfehlungen und nützlichen Informationen. Verwende Infoboxen und praktische Hinweise.",
        "review": "Schreibe eine ausführliche, ehrliche Bewertung/Review mit Verkostungsnotizen, Aromen-Beschreibungen und persönlicher Einschätzung. Gib eine Gesamtbewertung.",
        "listicle": "Schreibe einen strukturierten Listikel-Artikel mit nummerierten Punkten, klaren Beschreibungen und praktischen Empfehlungen für jeden Punkt.",
        "article": "Schreibe einen informativen, gut recherchierten Artikel mit interessanten Fakten und persönlichen Einschätzungen.",
    }

    min_words = content_settings.get("min_word_count", 1200)
    max_words = content_settings.get("max_word_count", 2500)

    return f"""Du bist ein leidenschaftlicher Whisky-Experte und Reiseblogger.
Dein Name ist Ellas. Du bist ein Weltenbummler und Whisky-Liebhaber.
Du schreibst auf Deutsch, in einem warmen, persönlichen, aber fachkundigen Ton.
Du duzt deine Leser.

AUFGABE: Schreibe einen vollständigen Blog-Artikel zum Thema: "{topic['title']}"

ARTIKELTYP: {type_instructions.get(article_type, type_instructions['article'])}

WICHTIGE REGELN:
1. Zwischen {min_words} und {max_words} Wörter.
2. Schreibe in HTML-Format. Verwende <h2>, <h3>, <p>, <ul>, <li>, <ol>, <strong>, <em>, <blockquote>.
3. Beginne NICHT mit <h1> - die Überschrift wird separat gesetzt.
4. Mindestens 4-6 Zwischenüberschriften (<h2>).
5. SEO-optimiert: Hauptkeyword natürlich im Text, in Überschriften und im ersten Absatz.
6. Baue an passenden Stellen Affiliate-Links ein:

WHISKY-SHOP-LINKS (für Produktempfehlungen):
{chr(10).join(shop_links)}

REISE-LINKS (für Reiseempfehlungen):
{chr(10).join(travel_links)}

7. Affiliate-Links als: <a href="LINK" target="_blank" rel="noopener noreferrer" class="affiliate-link">Linktext</a>
   Verwende 3-6 Affiliate-Links, nur wo sie thematisch passen.
8. Füge ein <blockquote> mit einem passenden Whisky-Zitat oder persönlichem Tipp ein.
9. Am Ende einen "Fazit"-Abschnitt.
10. Schreibe lebendig, mit Persönlichkeit - keine trockenen Fakten.
11. WICHTIG - Korrekte Schreibweise von Whisky/Whiskey:
    - Scotch Whisky (OHNE e) - für schottische Whiskys
    - Irish Whiskey (MIT e) - für irische Whiskeys
    - American Whiskey / Bourbon Whiskey (MIT e) - für amerikanische Whiskeys
    - Japanese Whisky (OHNE e) - für japanische Whiskys
    - German Whisky (OHNE e) - für deutsche Whiskys
    Achte IMMER darauf, die landestypische Schreibweise korrekt zu verwenden!
    Auch in zusammengesetzten Wörtern: "Whiskey-Szene" (irisch), "Whisky-Region" (schottisch).
12. WICHTIG - Verwende IMMER korrekte deutsche Umlaute (ä, ö, ü, ß) im Text!
    Schreibe "für" statt "fuer", "schön" statt "schoen", "über" statt "ueber".
    Die Website verwendet UTF-8-Encoding, Umlaute werden korrekt dargestellt.
    Für HTML-Entities verwende &ndash; &mdash; &bdquo; &ldquo; wie gewohnt.
13. Am Ende des Artikels füge eine Box ein mit verwandten Themen (NUR Text, KEINE Links - die werden automatisch hinzugefügt):
    <div class="related-box"><h3>Das könnte dich auch interessieren</h3><ul><li>3-4 verwandte Themenvorschläge als einfache Listenpunkte OHNE a-Tags</li></ul></div>

ANTWORTE NUR MIT DEM HTML-INHALT. Kein zusätzlicher Text."""


def _build_meta_prompt(topic):
    """Erstellt den Prompt für SEO-Meta-Daten."""
    return f"""Erstelle für einen Blog-Artikel mit dem Titel "{topic['title']}" folgendes:

1. SEO Meta-Description (max. 155 Zeichen, Deutsch, mit korrekten Umlauten ä/ö/ü/ß)
2. Kurzer Teaser/Auszug (max. 200 Zeichen, Deutsch, macht neugierig, mit Umlauten)
3. URL-Slug (lowercase, Bindestriche, keine Umlaute, keine Sonderzeichen)
4. 3-5 Focus-Keywords (kommagetrennt)
5. Open-Graph-Beschreibung (max. 200 Zeichen, Deutsch, mit Umlauten)

Antworte EXAKT in diesem JSON-Format:
{{"meta_description": "...", "teaser": "...", "slug": "...", "keywords": "...", "og_description": "..."}}

NUR JSON, kein anderer Text."""


def generate_article(topic, config):
    """
    Generiert einen vollständigen Artikel mit Meta-Daten.
    Gibt ein Dict mit allen Artikeldaten zurück.
    """
    client = OpenAI(api_key=config["openai"]["api_key"])
    model = config["openai"].get("model", "gpt-4o")
    temperature = config["openai"].get("temperature", 0.7)

    # --- Schritt 1: Artikel generieren ---
    print(f"  [1/2] Generiere Artikel: {topic['title']}...")

    prompt = _build_article_prompt(
        topic,
        config["affiliate_links"],
        config["content_settings"],
    )

    response = _call_openai_with_retry(
        client,
        model=model,
        temperature=temperature,
        max_tokens=config["openai"].get("max_tokens", 4000),
        messages=[
            {"role": "system", "content": "Du bist ein professioneller Blog-Autor. Schreibe auf Deutsch mit korrekten Umlauten (ä, ö, ü, ß). Antworte nur mit HTML-Inhalt."},
            {"role": "user", "content": prompt},
        ],
    )

    html_content = response.choices[0].message.content.strip()

    # Code-Block-Wrapper entfernen
    if html_content.startswith("```"):
        html_content = re.sub(r"^```(?:html)?\s*\n?", "", html_content)
        html_content = re.sub(r"\n?```\s*$", "", html_content)

    # --- Schritt 2: Meta-Daten generieren ---
    print(f"  [2/2] Generiere Meta-Daten...")

    meta_response = _call_openai_with_retry(
        client,
        model=model,
        temperature=0.3,
        max_tokens=500,
        messages=[
            {"role": "system", "content": "Du bist ein SEO-Experte. Antworte nur mit validem JSON. Verwende korrekte deutsche Umlaute (ä, ö, ü, ß)."},
            {"role": "user", "content": _build_meta_prompt(topic)},
        ],
    )

    meta_text = meta_response.choices[0].message.content.strip()
    if meta_text.startswith("```"):
        meta_text = re.sub(r"^```(?:json)?\s*\n?", "", meta_text)
        meta_text = re.sub(r"\n?```\s*$", "", meta_text)

    try:
        meta = json.loads(meta_text)
    except json.JSONDecodeError:
        slug = re.sub(r"[^a-z0-9\-]", "", topic["title"].lower().replace(" ", "-").replace(":", "").replace("ü", "ue").replace("ä", "ae").replace("ö", "oe"))
        meta = {
            "meta_description": topic["title"],
            "teaser": topic["title"],
            "slug": slug,
            "keywords": ", ".join(topic.get("tags", [])),
            "og_description": topic["title"],
        }
    # Bestimme Kategorien
    cat = topic.get("category", "Allgemein")
    if cat in ["Reise", "Urlaub"]:
        cats = ["Reise", "Lifestyle"]
    else:
        cats = [cat]


    # Deutsche Monatsnamen (strftime gibt auf Linux englische Namen)
    monate_de = {
        1: "Januar", 2: "Februar", 3: "März", 4: "April",
        5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
        9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
    }
    now = datetime.now()
    date_display = f"{now.day}. {monate_de[now.month]} {now.year}"

    return {
        "title": topic["title"],
        "html_content": html_content,
        "category": topic.get("category", "Allgemein"),
        "categories": cats,
        "tags": topic.get("tags", []),
        "type": topic.get("type", "article"),
        "meta": meta,
        "date": now.strftime("%Y-%m-%d"),
        "date_display": date_display,
    }
