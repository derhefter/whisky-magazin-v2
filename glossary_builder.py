"""
Glossary Builder: Generiert alle statischen Seiten für das Whisky-Glossar.

URL-Struktur:
  /whisky-glossar/                               – Glossar-Startseite
  /whisky-glossar/laender/schottland/            – Länderseite
  /whisky-glossar/regionen/islay/               – Regionsseite
  /whisky-glossar/destillerien/lagavulin/        – Destillerieseite
  /whisky-glossar/whiskys/lagavulin-16-jahre/   – Whisky-Detailseite

Aufruf aus site_builder_v2.py:
  from glossary_builder import build_glossary_pages
  build_glossary_pages(config)
"""

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_DIR = PROJECT_DIR / "data" / "glossary"

try:
    from site_builder_v2 import _base_template, _write_html, SITE_DIR
except ImportError:
    # Fallback für standalone-Tests
    SITE_DIR = PROJECT_DIR / "site-v2"

    def _base_template():
        raise RuntimeError("Bitte site_builder_v2 importieren")

    def _write_html(path, html):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)


# ---------------------------------------------------------------------------
# Datenlader
# ---------------------------------------------------------------------------

def _load(filename: str) -> list:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [e for e in data if e.get("published", False) and not e.get("deleted", False)]


def load_glossary_data() -> dict:
    return {
        "countries": _load("countries.json"),
        "regions": _load("regions.json"),
        "distilleries": _load("distilleries.json"),
        "whiskies": _load("whiskies.json"),
    }


# ---------------------------------------------------------------------------
# Kleine Hilfsfunktionen
# ---------------------------------------------------------------------------

_STATUS_LABELS = {
    "active": "Aktiv",
    "silent": "Still gelegt",
    "closed": "Geschlossen",
    "mothballed": "Eingemottet",
    "demolished": "Abgerissen",
}

_GLOSSAR_STYLES = """<style>
.glossar-page h2::before { display: none !important; }
.glossar-page h2 { padding-left: 0 !important; }
</style>
<div class="glossar-page">"""

_GLOSSAR_STYLES_CLOSE = "</div><!-- /glossar-page -->"

_SMOKE_LABELS = {
    "none": "Kein Torf",
    "light": "Leicht torfig",
    "medium": "Mittlerer Torf",
    "heavy": "Stark torfig",
    "very_heavy": "Sehr stark torfig",
}

_WHISKY_TYPE_LABELS = {
    "single_malt": "Single Malt",
    "blended_malt": "Blended Malt",
    "blended": "Blended",
    "single_grain": "Single Grain",
    "blended_grain": "Blended Grain",
    "pot_still": "Single Pot Still",
}

def _smoke_label(key: str) -> str:
    return _SMOKE_LABELS.get(key, key or "–")

def _type_label(key: str) -> str:
    return _WHISKY_TYPE_LABELS.get(key, key or "–")

def _search_block(search_id: str, placeholder: str) -> str:
    """Live-Suchleiste, filtert Elemente mit data-search-Attribut."""
    return f"""
    <div style="margin:0 0 24px;">
        <div style="position:relative;">
            <input type="search" id="{search_id}"
                placeholder="{placeholder}"
                autocomplete="off"
                style="width:100%;padding:10px 40px 10px 16px;border:1.5px solid var(--border);
                       border-radius:var(--radius-sm);font-size:15px;font-family:'Inter',sans-serif;
                       color:var(--text-primary);background:var(--bg-primary);
                       transition:border-color 0.2s;outline:none;box-sizing:border-box;"
                onfocus="this.style.borderColor='var(--accent-amber)'"
                onblur="this.style.borderColor='var(--border)'"
                oninput="(function(q){{
                    var items=document.querySelectorAll('[data-search]');
                    var count=0;
                    items.forEach(function(el){{
                        var match=!q||el.dataset.search.includes(q.toLowerCase());
                        el.style.display=match?'':'none';
                        if(match)count++;
                    }});
                    var cnt=document.getElementById('{search_id}-count');
                    if(cnt)cnt.textContent=q?(count+' Ergebnis'+(count!==1?'se':'')):'';
                }})(this.value)">
            <span style="position:absolute;right:12px;top:50%;transform:translateY(-50%);
                         color:var(--text-secondary);pointer-events:none;font-size:16px;">🔍</span>
        </div>
        <div id="{search_id}-count" style="font-size:12px;color:var(--text-secondary);
             margin-top:6px;font-family:'Inter',sans-serif;min-height:18px;"></div>
    </div>"""


def _feedback_section(page_name: str, page_type: str, page_url: str) -> str:
    """Feedback-Formular für redaktionelle Anmerkungen."""
    safe_name = page_name.replace("'", "\\'").replace('"', '&quot;')
    fn = f"submitFb_{page_type}"
    return f"""
    <div style="max-width:760px;margin:48px auto;padding:0 24px;">
        <div style="background:var(--bg-surface);border-radius:var(--radius-sm);
                    padding:28px 32px;border:1px solid var(--border);">
            <h3 style="font-family:'Fraunces',serif;font-size:18px;font-weight:600;margin:0 0 8px;">
                Redaktionelles Feedback</h3>
            <p style="font-size:14px;color:var(--text-secondary);margin:0 0 20px;line-height:1.6;">
                Fehler entdeckt oder Anmerkung? Schreib uns kurz &ndash; wir lesen jede Nachricht.</p>
            <div style="display:none;"><input id="fb-hp-{page_type}" tabindex="-1" autocomplete="off"></div>
            <textarea id="fb-msg-{page_type}" rows="4"
                placeholder="Deine Anmerkung (mindestens 20 Zeichen) \u2026"
                style="width:100%;padding:10px 14px;border:1.5px solid var(--border);
                       border-radius:var(--radius-sm);font-size:14px;font-family:'Inter',sans-serif;
                       color:var(--text-primary);background:var(--bg-primary);resize:vertical;
                       outline:none;box-sizing:border-box;transition:border-color 0.2s;"
                onfocus="this.style.borderColor='var(--accent-amber)'"
                onblur="this.style.borderColor='var(--border)'"></textarea>
            <input type="email" id="fb-email-{page_type}"
                placeholder="Deine E-Mail (optional, f\u00fcr R\u00fcckfragen)"
                style="width:100%;margin-top:10px;padding:10px 14px;border:1.5px solid var(--border);
                       border-radius:var(--radius-sm);font-size:14px;font-family:'Inter',sans-serif;
                       color:var(--text-primary);background:var(--bg-primary);outline:none;
                       box-sizing:border-box;transition:border-color 0.2s;"
                onfocus="this.style.borderColor='var(--accent-amber)'"
                onblur="this.style.borderColor='var(--border)'">
            <div style="margin-top:12px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
                <button onclick="{fn}()"
                    style="background:var(--accent-amber);color:#fff;border:none;
                           border-radius:var(--radius-sm);padding:10px 24px;font-size:14px;
                           font-family:'Inter',sans-serif;font-weight:500;cursor:pointer;
                           transition:opacity 0.2s;"
                    onmouseover="this.style.opacity='0.85'"
                    onmouseout="this.style.opacity='1'">Senden</button>
                <span id="fb-status-{page_type}" style="font-size:13px;color:var(--text-secondary);
                      font-family:'Inter',sans-serif;"></span>
            </div>
        </div>
    </div>
    <script>
    function {fn}() {{
        var msg=document.getElementById('fb-msg-{page_type}').value.trim();
        var email=document.getElementById('fb-email-{page_type}').value.trim();
        var hp=document.getElementById('fb-hp-{page_type}').value;
        var status=document.getElementById('fb-status-{page_type}');
        if(msg.length<20){{status.textContent='Bitte mindestens 20 Zeichen eingeben.';status.style.color='var(--accent-warm)';return;}}
        status.textContent='Wird gesendet \u2026';status.style.color='var(--text-secondary)';
        fetch('/api/subscribe',{{method:'POST',headers:{{'Content-Type':'application/json'}},
            body:JSON.stringify({{action:'feedback',page_name:'{safe_name}',
                page_type:'{page_type}',page_url:'{page_url}',
                message:msg,reply_email:email,honeypot:hp}})
        }})
        .then(function(r){{return r.json();}})
        .then(function(d){{
            if(d.ok){{
                status.textContent='\u2713 Vielen Dank! Wir schauen uns das an.';
                status.style.color='var(--accent-sage)';
                document.getElementById('fb-msg-{page_type}').value='';
                document.getElementById('fb-email-{page_type}').value='';
            }}else{{
                status.textContent=d.error||'Fehler beim Senden.';
                status.style.color='var(--accent-warm)';
            }}
        }})
        .catch(function(){{status.textContent='Verbindungsfehler. Bitte sp\u00e4ter nochmal.';status.style.color='var(--accent-warm)';}});
    }}
    </script>"""


def _tag_badges(tags: list) -> str:
    if not tags:
        return ""
    return " ".join(
        f'<span style="background:var(--bg-surface);color:var(--text-secondary);padding:3px 10px;border-radius:var(--radius-pill);font-size:12px;font-family:\'Inter\',sans-serif;">{t}</span>'
        for t in tags
    )


# ---------------------------------------------------------------------------
# Gemeinsamer Seitenkopf (Breadcrumb + Hero)
# ---------------------------------------------------------------------------

def _breadcrumb(*crumbs) -> str:
    parts = ['<a href="/">Startseite</a>',
             '<a href="/whisky-glossar/">Whisky-Glossar</a>']
    for label, url in crumbs[:-1]:
        parts.append(f'<a href="{url}">{label}</a>')
    if crumbs:
        parts.append(f'<span>{crumbs[-1][0]}</span>')
    inner = " &rsaquo; ".join(parts)
    return f'<nav class="breadcrumb"><div class="breadcrumb-inner">{inner}</div></nav>'


def _page_hero(supertitle: str, title: str, subtitle: str = "") -> str:
    sub = f'<p style="font-size:17px;color:rgba(255,255,255,0.78);line-height:1.7;max-width:620px;margin:16px auto 0;">{subtitle}</p>' if subtitle else ""
    return f"""
    <section style="background:var(--text-primary);color:#fff;padding:60px 24px 48px;text-align:center;position:relative;overflow:hidden;">
        <div style="position:absolute;inset:0;background:radial-gradient(ellipse at 60% 40%,rgba(200,150,62,0.15) 0%,transparent 65%);pointer-events:none;"></div>
        <div style="position:relative;max-width:760px;margin:0 auto;">
            <p style="font-size:11px;letter-spacing:3px;text-transform:uppercase;color:var(--accent-amber);margin:0 0 14px;font-weight:600;">{supertitle}</p>
            <h1 style="font-family:'Fraunces',Georgia,serif;font-size:clamp(28px,5vw,44px);font-weight:600;line-height:1.2;margin:0;color:#fff;">{title}</h1>
            {sub}
        </div>
    </section>"""


def _info_grid(*items) -> str:
    """Renders a 2-col key/value info grid."""
    rows = ""
    for label, value in items:
        if value:
            rows += f'<div style="padding:8px 0;border-bottom:1px solid var(--border);display:flex;gap:12px;"><span style="color:var(--text-secondary);font-size:13px;min-width:140px;">{label}</span><span style="font-size:14px;font-weight:500;">{value}</span></div>'
    return f'<div style="margin:24px 0;">{rows}</div>'


def _card_link(title: str, subtitle: str, url: str, tags: list = None, search_key: str = None) -> str:
    tags_html = _tag_badges(tags or [])
    sk = (search_key or f"{title} {subtitle}").lower().replace('"', '')
    return f"""
    <a href="{url}" data-search="{sk}" style="display:block;background:var(--bg-elevated);border:1px solid var(--border);border-radius:var(--radius-sm);padding:20px 24px;text-decoration:none;color:inherit;transition:box-shadow 0.2s;" onmouseover="this.style.boxShadow='var(--shadow-hover)'" onmouseout="this.style.boxShadow=''">
        <div style="font-family:'Fraunces',serif;font-size:17px;font-weight:600;margin-bottom:4px;">{title}</div>
        <div style="font-size:13px;color:var(--text-secondary);">{subtitle}</div>
        {('<div style="margin-top:8px;">' + tags_html + '</div>') if tags else ''}
    </a>"""


def _section(title: str, body: str) -> str:
    return f"""
    <section style="max-width:960px;margin:48px auto;padding:0 24px;">
        <h2 style="font-family:'Fraunces',serif;font-size:22px;font-weight:600;margin:0 0 20px;padding-bottom:10px;border-bottom:2px solid var(--bg-surface);">{title}</h2>
        {body}
    </section>"""


# ---------------------------------------------------------------------------
# Glossar-Startseite
# ---------------------------------------------------------------------------

def build_glossary_index(data: dict, config: dict) -> str:
    import json as _json
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    countries = data["countries"]
    regions = data["regions"]
    distilleries = data["distilleries"]
    whiskies = data["whiskies"]

    country_cards = "\n".join(
        _card_link(
            c["name_de"],
            c.get("short_description", "")[:100] + "…",
            f"/whisky-glossar/laender/{c['slug']}/"
        )
        for c in countries
    )

    region_cards = "\n".join(
        _card_link(
            r["name"],
            r.get("short_description", "")[:80] + "…",
            f"/whisky-glossar/regionen/{r['slug']}/"
        )
        for r in regions[:6]
    )

    distillery_cards = "\n".join(
        _card_link(
            d["name"],
            d.get("short_description", "")[:80] + "…",
            f"/whisky-glossar/destillerien/{d['slug']}/"
        )
        for d in distilleries[:6]
    )

    # Suchdaten: alle Destillerien + Whiskys als JSON für Client-Suche
    search_items = _json.dumps(
        [{"n": d["name"], "s": d.get("short_description", "")[:60], "u": f"/whisky-glossar/destillerien/{d['slug']}/", "t": "Destillerie"} for d in distilleries]
        + [{"n": w["name"], "s": w.get("short_description", "")[:60], "u": f"/whisky-glossar/whiskys/{w['slug']}/", "t": "Whisky"} for w in whiskies],
        ensure_ascii=False
    )

    content = f"""
    {_GLOSSAR_STYLES}
    <nav class="breadcrumb"><div class="breadcrumb-inner"><a href="/">Startseite</a> &rsaquo; <span>Whisky-Glossar</span></div></nav>
    {_page_hero("Whisky · Reise · Wissen", "Whisky-Glossar",
                "Länder, Regionen, Destillerien und Abfüllungen – strukturiert und redaktionell gepflegt.")}

    <!-- Suchleiste -->
    <div style="max-width:760px;margin:0 auto;padding:24px 24px 0;">
        <div style="position:relative;">
            <input type="search" id="glossar-search" placeholder="Destillerie oder Whisky suchen … z.B. Lagavulin, Ardbeg 10"
                autocomplete="off"
                style="width:100%;padding:12px 44px 12px 18px;border:2px solid var(--accent-amber);
                       border-radius:var(--radius-sm);font-size:16px;font-family:'Inter',sans-serif;
                       color:var(--text-primary);background:var(--bg-primary);
                       outline:none;box-sizing:border-box;box-shadow:var(--shadow-hover);"
                oninput="glossarSearch(this.value)"
                onkeydown="if(event.key==='Escape'){{this.value='';glossarSearch('');}}">
            <span style="position:absolute;right:14px;top:50%;transform:translateY(-50%);
                         color:var(--text-secondary);font-size:18px;pointer-events:none;">🔍</span>
            <div id="glossar-results" style="display:none;position:absolute;top:calc(100% + 4px);left:0;right:0;
                 z-index:500;background:var(--bg-elevated);border:1px solid var(--border);
                 border-radius:var(--radius-sm);box-shadow:0 8px 32px rgba(139,115,85,0.18);
                 max-height:360px;overflow-y:auto;"></div>
        </div>
    </div>
    <script>
    var _glossarData={search_items};
    function glossarSearch(q){{
        var box=document.getElementById('glossar-results');
        if(!q||!q.trim()){{box.style.display='none';return;}}
        var ql=q.toLowerCase();
        var matches=_glossarData.filter(function(i){{
            return i.n.toLowerCase().indexOf(ql)!==-1||i.s.toLowerCase().indexOf(ql)!==-1;
        }}).slice(0,12);
        if(!matches.length){{
            box.innerHTML='<div style="padding:12px 16px;font-size:14px;color:var(--text-secondary);">Keine Treffer f\u00fcr &bdquo;'+q+'&ldquo;</div>';
            box.style.display='block';return;
        }}
        box.innerHTML=matches.map(function(i){{
            var bg='background:var(--bg-surface)';
            return '<a href="'+i.u+'" style="display:flex;align-items:center;gap:12px;padding:10px 16px;text-decoration:none;color:inherit;border-bottom:1px solid var(--border);" onmouseover="this.style.background=\'var(--bg-surface)\'" onmouseout="this.style.background=\'transparent\'">'
                +'<span style="font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--accent-amber);font-family:Inter,sans-serif;min-width:80px;flex-shrink:0;">'+i.t+'</span>'
                +'<div style="min-width:0;"><div style="font-family:Fraunces,serif;font-weight:600;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'+i.n+'</div>'
                +'<div style="font-size:12px;color:var(--text-secondary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'+i.s+'</div></div></a>';
        }}).join('');
        box.style.display='block';
    }}
    document.addEventListener('click',function(e){{
        var box=document.getElementById('glossar-results');
        var inp=document.getElementById('glossar-search');
        if(box&&inp&&!box.contains(e.target)&&e.target!==inp)box.style.display='none';
    }});
    </script>

    <!-- Statistik-Band -->
    <div style="background:var(--accent-amber);padding:20px 24px;margin-top:24px;">
        <div style="max-width:960px;margin:0 auto;display:flex;flex-wrap:wrap;gap:24px;justify-content:center;text-align:center;">
            <div><div style="font-family:'Fraunces',serif;font-size:28px;font-weight:600;color:#fff;">{len(countries)}</div><div style="font-size:12px;color:rgba(255,255,255,0.85);text-transform:uppercase;letter-spacing:1px;">Länder</div></div>
            <div><div style="font-family:'Fraunces',serif;font-size:28px;font-weight:600;color:#fff;">{len(regions)}</div><div style="font-size:12px;color:rgba(255,255,255,0.85);text-transform:uppercase;letter-spacing:1px;">Regionen</div></div>
            <div><div style="font-family:'Fraunces',serif;font-size:28px;font-weight:600;color:#fff;">{len(distilleries)}</div><div style="font-size:12px;color:rgba(255,255,255,0.85);text-transform:uppercase;letter-spacing:1px;">Destillerien</div></div>
            <div><div style="font-family:'Fraunces',serif;font-size:28px;font-weight:600;color:#fff;">{len(whiskies)}</div><div style="font-size:12px;color:rgba(255,255,255,0.85);text-transform:uppercase;letter-spacing:1px;">Whiskys</div></div>
        </div>
    </div>

    {_section("Länder", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{country_cards}</div>')}
    {_section("Regionen", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{region_cards}</div><p style="margin-top:16px;font-size:13px;"><a href="/whisky-glossar/regionen/" style="color:var(--accent-amber);">Alle Regionen →</a></p>')}
    {_section("Destillerien", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{distillery_cards}</div><p style="margin-top:16px;font-size:13px;"><a href="/whisky-glossar/destillerien/" style="color:var(--accent-amber);">Alle Destillerien →</a></p>')}

    <div style="max-width:960px;margin:0 auto 64px;padding:0 24px;">
        <div style="background:var(--bg-surface);border-radius:var(--radius-sm);padding:28px;border:1px solid var(--border);font-size:13px;color:var(--text-secondary);">
            Das Glossar befindet sich im Aufbau. Daten werden schrittweise ergänzt und redaktionell geprüft.
        </div>
    </div>
    {_GLOSSAR_STYLES_CLOSE}
    """

    return _base_template().format(
        title="Whisky-Glossar",
        site_name=site_name,
        meta_description="Das Whisky-Glossar von whisky-reise.com: Länder, Regionen, Destillerien und Abfüllungen – strukturiert und redaktionell gepflegt.",
        keywords="Whisky Glossar, Destillerien, Regionen, Schottland, Islay, Speyside",
        og_description="Whisky-Wissen strukturiert: Länder, Regionen, Destillerien und Abfüllungen.",
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/whisky-glossar/",
        base_url=base_url,
        json_ld="",
        content=content,
    )


# ---------------------------------------------------------------------------
# Länder-Indexseite
# ---------------------------------------------------------------------------

def build_country_page(country: dict, regions: list, distilleries: list,
                       whiskies: list, config: dict) -> str:
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    cid = country["id"]

    country_regions = [r for r in regions if r.get("country_id") == cid]
    country_distilleries = [d for d in distilleries if d.get("country_id") == cid]
    country_whiskies = [w for w in whiskies if w.get("country_id") == cid]

    region_cards = "\n".join(
        _card_link(r["name"], r.get("short_description", "")[:80] + "…",
                   f"/whisky-glossar/regionen/{r['slug']}/")
        for r in country_regions
    )
    distillery_cards = "\n".join(
        _card_link(d["name"], d.get("short_description", "")[:80] + "…",
                   f"/whisky-glossar/destillerien/{d['slug']}/")
        for d in country_distilleries[:8]
    )
    whisky_cards = "\n".join(
        _card_link(
            w["name"],
            f"{_type_label(w.get('whisky_type',''))} · {w.get('abv','?')}% · {_smoke_label(w.get('smoke_profile',''))}",
            f"/whisky-glossar/whiskys/{w['slug']}/",
            tags=w.get("style_tags", [])[:3]
        )
        for w in country_whiskies[:6]
    )

    long_desc = country.get("long_description", "")
    travel = country.get("travel_context", "")

    content = f"""
    {_GLOSSAR_STYLES}
    {_breadcrumb(("Länder", "/whisky-glossar/laender/"), (country["name_de"], f"/whisky-glossar/laender/{country['slug']}/"))}
    {_page_hero("Whisky-Land", country["name_de"], country.get("short_description", ""))}

    <div style="max-width:760px;margin:48px auto;padding:0 24px;">
        <p style="font-size:17px;line-height:1.8;color:var(--text-secondary);">{long_desc}</p>
        {(f'<div style="margin-top:28px;padding:20px 24px;background:var(--bg-surface);border-left:3px solid var(--accent-amber);border-radius:0 var(--radius-sm) var(--radius-sm) 0;font-size:15px;line-height:1.7;"><strong>Reisetipp:</strong> {travel}</div>') if travel else ''}
    </div>

    {(_section("Regionen", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{region_cards}</div>') if region_cards else '')}
    {(_section("Destillerien", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{distillery_cards}</div>') if distillery_cards else '')}
    {(_section("Whiskys", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{whisky_cards}</div>') if whisky_cards else '')}

    <div style="height:48px;"></div>
    {_GLOSSAR_STYLES_CLOSE}
    """

    json_ld = f"""<script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {{"@type":"ListItem","position":1,"name":"Startseite","item":"{base_url}/"}},
        {{"@type":"ListItem","position":2,"name":"Whisky-Glossar","item":"{base_url}/whisky-glossar/"}},
        {{"@type":"ListItem","position":3,"name":"{country["name_de"]}","item":"{base_url}/whisky-glossar/laender/{country["slug"]}/"}}
    ]}}</script>"""

    return _base_template().format(
        title=country.get("seo_title", f"Whisky aus {country['name_de']}"),
        site_name=site_name,
        meta_description=country.get("seo_description", f"Whisky-Destillerien und Regionen aus {country['name_de']}."),
        keywords=f"Whisky {country['name_de']}, Destillerien, Regionen",
        og_description=country.get("seo_description", ""),
        og_image=country.get("image") or f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/whisky-glossar/laender/{country['slug']}/",
        base_url=base_url,
        json_ld=json_ld,
        content=content,
    )


# ---------------------------------------------------------------------------
# Regionsseite
# ---------------------------------------------------------------------------

def build_region_page(region: dict, countries: list, distilleries: list,
                      whiskies: list, config: dict) -> str:
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    rid = region["id"]
    cid = region.get("country_id", "")

    country = next((c for c in countries if c["id"] == cid), {})
    country_name = country.get("name_de", cid)
    country_slug = country.get("slug", cid)

    region_distilleries = [d for d in distilleries if d.get("region_id") == rid]
    region_whiskies = [w for w in whiskies if w.get("region_id") == rid]

    distillery_cards = "\n".join(
        _card_link(d["name"], d.get("short_description", "")[:80] + "…",
                   f"/whisky-glossar/destillerien/{d['slug']}/")
        for d in region_distilleries
    )
    whisky_cards = "\n".join(
        _card_link(
            w["name"],
            f"{_type_label(w.get('whisky_type',''))} · {w.get('abv','?')}% · {_smoke_label(w.get('smoke_profile',''))}",
            f"/whisky-glossar/whiskys/{w['slug']}/",
            tags=w.get("style_tags", [])[:3]
        )
        for w in region_whiskies[:6]
    )

    style_notes = region.get("style_notes", "")
    travel = region.get("travel_context", "")

    content = f"""
    {_GLOSSAR_STYLES}
    {_breadcrumb(
        (country_name, f"/whisky-glossar/laender/{country_slug}/"),
        ("Regionen", "/whisky-glossar/regionen/"),
        (region["name"], f"/whisky-glossar/regionen/{region['slug']}/")
    )}
    {_page_hero(f"Whisky-Region · {country_name}", region["name"], region.get("short_description", ""))}

    <div style="max-width:760px;margin:48px auto;padding:0 24px;">
        <p style="font-size:17px;line-height:1.8;color:var(--text-secondary);">{region.get("long_description","")}</p>
        {(_info_grid(("Stil-Profil", style_notes))) if style_notes else ''}
        {(f'<div style="margin-top:28px;padding:20px 24px;background:var(--bg-surface);border-left:3px solid var(--accent-amber);border-radius:0 var(--radius-sm) var(--radius-sm) 0;font-size:15px;line-height:1.7;"><strong>Reisetipp:</strong> {travel}</div>') if travel else ''}
    </div>

    {(_section("Destillerien in dieser Region", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{distillery_cards}</div>') if distillery_cards else '')}
    {(_section("Whiskys aus dieser Region", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{whisky_cards}</div>') if whisky_cards else '')}

    <div style="height:48px;"></div>
    {_GLOSSAR_STYLES_CLOSE}
    """

    json_ld = f"""<script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {{"@type":"ListItem","position":1,"name":"Startseite","item":"{base_url}/"}},
        {{"@type":"ListItem","position":2,"name":"Whisky-Glossar","item":"{base_url}/whisky-glossar/"}},
        {{"@type":"ListItem","position":3,"name":"{country_name}","item":"{base_url}/whisky-glossar/laender/{country_slug}/"}},
        {{"@type":"ListItem","position":4,"name":"{region["name"]}","item":"{base_url}/whisky-glossar/regionen/{region["slug"]}/"}}
    ]}}</script>"""

    return _base_template().format(
        title=region.get("seo_title", f"{region['name']} – Whisky-Region"),
        site_name=site_name,
        meta_description=region.get("seo_description", f"Whisky-Destillerien und Abfüllungen aus der Region {region['name']}."),
        keywords=f"Whisky {region['name']}, Region, Destillerien, {country_name}",
        og_description=region.get("seo_description", ""),
        og_image=region.get("image") or f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/whisky-glossar/regionen/{region['slug']}/",
        base_url=base_url,
        json_ld=json_ld,
        content=content,
    )


# ---------------------------------------------------------------------------
# Destillerieseite
# ---------------------------------------------------------------------------

def build_distillery_page(distillery: dict, countries: list, regions: list,
                          whiskies: list, config: dict) -> str:
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    did = distillery["id"]
    cid = distillery.get("country_id", "")
    rid = distillery.get("region_id", "")

    country = next((c for c in countries if c["id"] == cid), {})
    region = next((r for r in regions if r["id"] == rid), {})
    country_name = country.get("name_de", cid)
    country_slug = country.get("slug", cid)
    region_name = region.get("name", rid)
    region_slug = region.get("slug", rid)

    distillery_whiskies = [w for w in whiskies if w.get("distillery_id") == did]
    whisky_cards = "\n".join(
        _card_link(
            w["name"],
            f"{_type_label(w.get('whisky_type',''))} · {w.get('abv','?')}% · {_smoke_label(w.get('smoke_profile',''))}",
            f"/whisky-glossar/whiskys/{w['slug']}/",
            tags=w.get("style_tags", [])[:3]
        )
        for w in distillery_whiskies
    )

    founded = distillery.get("founded", "")
    owner = distillery.get("owner", "")
    # Support both old field name (travel_info) and new split fields (visit_info + travel_context)
    travel = distillery.get("travel_context", "")
    visit_info = distillery.get("visit_info", "") or distillery.get("travel_info", "")

    # Karten-Link, wenn Koordinaten vorhanden
    coords = distillery.get("coordinates", {})
    map_link = ""
    if coords and coords.get("lat"):
        map_link = (
            f'<div style="margin:20px 0;">'
            f'<a href="/karte.html?loc=loc-{distillery["slug"]}" '
            f'style="display:inline-flex;align-items:center;gap:8px;color:var(--accent-amber);'
            f'border:1.5px solid var(--accent-amber);border-radius:var(--radius-sm);'
            f'padding:8px 18px;font-size:14px;font-family:\'Inter\',sans-serif;font-weight:500;'
            f'text-decoration:none;transition:background 0.2s;" '
            f'onmouseover="this.style.background=\'rgba(200,150,62,0.08)\'" '
            f'onmouseout="this.style.background=\'transparent\'">'
            f'&#128506; Auf der Karte anzeigen</a></div>'
        )

    distillery_page_url = f"/whisky-glossar/destillerien/{distillery['slug']}/"

    content = f"""
    {_GLOSSAR_STYLES}
    {_breadcrumb(
        (country_name, f"/whisky-glossar/laender/{country_slug}/"),
        (region_name, f"/whisky-glossar/regionen/{region_slug}/"),
        ("Destillerien", "/whisky-glossar/destillerien/"),
        (distillery["name"], f"/whisky-glossar/destillerien/{distillery['slug']}/")
    )}
    {_page_hero(f"Destillerie · {region_name} · {country_name}", distillery["name"], distillery.get("short_description", ""))}

    <div style="max-width:760px;margin:48px auto;padding:0 24px;">
        {_info_grid(
            ("Gegründet", str(founded) if founded else ""),
            ("Eigentümer", owner),
            ("Region", region_name),
            ("Land", country_name),
            ("Status", _STATUS_LABELS.get(distillery.get("status", ""), distillery.get("status", "").capitalize()) if distillery.get("status") else ""),
        )}
        {map_link}
        <p style="font-size:17px;line-height:1.8;color:var(--text-secondary);margin-top:24px;">{distillery.get("long_description","")}</p>
        {(f'<div style="margin-top:24px;padding:16px 20px;background:var(--bg-surface);border-radius:var(--radius-sm);font-size:14px;line-height:1.7;"><strong>Besucherinfo:</strong> {visit_info}</div>') if visit_info else ''}
        {(f'<div style="margin-top:16px;padding:20px 24px;background:var(--bg-surface);border-left:3px solid var(--accent-amber);border-radius:0 var(--radius-sm) var(--radius-sm) 0;font-size:15px;line-height:1.7;"><strong>Reisetipp:</strong> {travel}</div>') if travel else ''}
    </div>

    {(_section(f"Abfüllungen von {distillery['name']}", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{whisky_cards}</div>') if whisky_cards else '')}

    {_feedback_section(distillery["name"], "distillery", distillery_page_url)}

    <div style="height:48px;"></div>
    {_GLOSSAR_STYLES_CLOSE}
    """

    json_ld = f"""<script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"LocalBusiness","name":"{distillery["name"]}",
    "description":"{distillery.get("short_description","").replace('"',"'")}",
    "url":"{base_url}/whisky-glossar/destillerien/{distillery["slug"]}/"
    }}</script>"""

    return _base_template().format(
        title=distillery.get("seo_title", f"{distillery['name']} Destillerie"),
        site_name=site_name,
        meta_description=distillery.get("seo_description", f"Alles über die {distillery['name']} Destillerie: Geschichte, Abfüllungen und Reisetipps."),
        keywords=f"{distillery['name']}, Destillerie, {region_name}, {country_name}, Whisky",
        og_description=distillery.get("seo_description", ""),
        og_image=distillery.get("image") or f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/whisky-glossar/destillerien/{distillery['slug']}/",
        base_url=base_url,
        json_ld=json_ld,
        content=content,
    )


# ---------------------------------------------------------------------------
# Whisky-Detailseite
# ---------------------------------------------------------------------------

def build_whisky_page(whisky: dict, countries: list, regions: list,
                      distilleries: list, config: dict) -> str:
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]
    cid = whisky.get("country_id", "")
    rid = whisky.get("region_id", "")
    did = whisky.get("distillery_id", "")

    country = next((c for c in countries if c["id"] == cid), {})
    region = next((r for r in regions if r["id"] == rid), {})
    distillery = next((d for d in distilleries if d["id"] == did), {})

    country_name = country.get("name_de", cid)
    country_slug = country.get("slug", cid)
    region_name = region.get("name", rid)
    region_slug = region.get("slug", rid)
    distillery_name = distillery.get("name", did)
    distillery_slug = distillery.get("slug", did)

    age = whisky.get("age_statement")
    age_str = f"{age} Jahre" if age else ("NAS" if whisky.get("nas") else "–")
    cask_str = ", ".join(whisky.get("cask_types") or []) or "–"
    tags_html = _tag_badges(whisky.get("style_tags", []))
    nose = whisky.get("tasting_notes_nose", "")
    palate = whisky.get("tasting_notes_palate", "")
    finish = whisky.get("tasting_notes_finish", "")
    editorial = whisky.get("editorial_notes", "")
    travel = whisky.get("travel_context", "")

    tasting_html = ""
    if nose or palate or finish:
        rows = ""
        for label, note in [("Nase", nose), ("Gaumen", palate), ("Abgang", finish)]:
            if note:
                rows += f'<div style="margin-bottom:20px;"><div style="font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--accent-amber);font-weight:600;margin-bottom:6px;">{label}</div><p style="font-size:15px;line-height:1.7;color:var(--text-secondary);margin:0;">{note}</p></div>'
        tasting_html = _section("Tasting Notes", rows)

    content = f"""
    {_GLOSSAR_STYLES}
    {_breadcrumb(
        (country_name, f"/whisky-glossar/laender/{country_slug}/"),
        (region_name, f"/whisky-glossar/regionen/{region_slug}/"),
        (distillery_name, f"/whisky-glossar/destillerien/{distillery_slug}/"),
        (whisky["name"], f"/whisky-glossar/whiskys/{whisky['slug']}/")
    )}
    {_page_hero(f"{distillery_name} · {region_name}", whisky["name"], whisky.get("short_description", ""))}

    <div style="max-width:760px;margin:48px auto;padding:0 24px;">
        {('<div style="margin-bottom:20px;">' + tags_html + '</div>') if tags_html else ''}
        {_info_grid(
            ("Typ", _type_label(whisky.get("whisky_type", ""))),
            ("Reifejahre", age_str),
            ("ABV", f"{whisky.get('abv','?')} %"),
            ("Rauchprofil", _smoke_label(whisky.get("smoke_profile", ""))),
            ("Fasstypen", cask_str),
            ("Destillerie", distillery_name),
            ("Region", region_name),
            ("Land", country_name),
        )}
        <p style="font-size:17px;line-height:1.8;color:var(--text-secondary);margin-top:24px;">{whisky.get("long_description","")}</p>
    </div>

    {tasting_html}

    {(f'<div style="max-width:760px;margin:0 auto 32px;padding:0 24px;"><blockquote style="font-family:\'Fraunces\',serif;font-style:italic;font-size:18px;color:var(--text-primary);border-left:3px solid var(--accent-amber);padding:4px 0 4px 24px;margin:0;">{editorial}</blockquote></div>') if editorial else ''}
    {(f'<div style="max-width:760px;margin:0 auto 48px;padding:0 24px;"><div style="padding:20px 24px;background:var(--bg-surface);border-left:3px solid var(--accent-amber);border-radius:0 var(--radius-sm) var(--radius-sm) 0;font-size:15px;line-height:1.7;"><strong>Reise-Kontext:</strong> {travel}</div></div>') if travel else ''}

    {_feedback_section(whisky["name"], "whisky", f"/whisky-glossar/whiskys/{whisky['slug']}/")}

    <div style="height:48px;"></div>
    {_GLOSSAR_STYLES_CLOSE}
    """

    json_ld = f"""<script type="application/ld+json">
    {{"@context":"https://schema.org","@type":"Product",
    "name":"{whisky["name"]}",
    "description":"{whisky.get("short_description","").replace('"',"'")}",
    "brand":{{"@type":"Brand","name":"{distillery_name}"}},
    "url":"{base_url}/whisky-glossar/whiskys/{whisky["slug"]}/"
    }}</script>"""

    return _base_template().format(
        title=whisky.get("seo_title", whisky["name"]),
        site_name=site_name,
        meta_description=whisky.get("seo_description", whisky.get("short_description", "")),
        keywords=f"{whisky['name']}, {distillery_name}, {region_name}, {country_name}, Whisky",
        og_description=whisky.get("seo_description", whisky.get("short_description", "")),
        og_image=whisky.get("image") or f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/whisky-glossar/whiskys/{whisky['slug']}/",
        base_url=base_url,
        json_ld=json_ld,
        content=content,
    )


# ---------------------------------------------------------------------------
# Index-Seiten (alle Regionen / alle Destillerien)
# ---------------------------------------------------------------------------

def build_region_index(regions: list, countries: list, config: dict) -> str:
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    country_map = {c["id"]: c for c in countries}
    cards = ""
    for r in regions:
        c = country_map.get(r.get("country_id", ""), {})
        cards += _card_link(
            r["name"],
            f"{c.get('name_de','')} · {r.get('short_description','')[:60]}…",
            f"/whisky-glossar/regionen/{r['slug']}/"
        )

    content = f"""
    {_GLOSSAR_STYLES}
    {_breadcrumb(("Regionen", "/whisky-glossar/regionen/"))}
    {_page_hero("Whisky-Regionen", "Alle Regionen im Überblick")}
    {_section("Regionen", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{cards}</div>')}
    <div style="height:48px;"></div>
    {_GLOSSAR_STYLES_CLOSE}
    """

    return _base_template().format(
        title="Whisky-Regionen",
        site_name=site_name,
        meta_description="Alle Whisky-Regionen im Überblick: Islay, Speyside, Highlands, Campbeltown, Lowlands und mehr.",
        keywords="Whisky Regionen, Islay, Speyside, Highlands, Campbeltown",
        og_description="Alle Whisky-Regionen im Überblick.",
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/whisky-glossar/regionen/",
        base_url=base_url,
        json_ld="",
        content=content,
    )


def build_distillery_index(distilleries: list, regions: list,
                           countries: list, config: dict) -> str:
    base_url = config["site"].get("base_url", "")
    site_name = config["site"]["name"]

    region_map = {r["id"]: r for r in regions}
    country_map = {c["id"]: c for c in countries}

    cards = ""
    for d in distilleries:
        r = region_map.get(d.get("region_id", ""), {})
        c = country_map.get(d.get("country_id", ""), {})
        subtitle = f"{r.get('name','')} · {c.get('name_de','')}"
        cards += _card_link(
            d["name"],
            subtitle,
            f"/whisky-glossar/destillerien/{d['slug']}/",
            search_key=f"{d['name']} {r.get('name','')} {c.get('name_de','')} {d.get('short_description','')}"
        )

    content = f"""
    {_GLOSSAR_STYLES}
    {_breadcrumb(("Destillerien", "/whisky-glossar/destillerien/"))}
    {_page_hero("Whisky-Destillerien", "Alle Destillerien im Überblick")}
    <section style="max-width:960px;margin:32px auto 0;padding:0 24px;">
        {_search_block("dist-search", "Destillerie suchen … z.B. Lagavulin, Ardbeg, Bowmore")}
    </section>
    {_section("Destillerien", f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;">{cards}</div>')}
    <div style="height:48px;"></div>
    {_GLOSSAR_STYLES_CLOSE}
    """

    return _base_template().format(
        title="Whisky-Destillerien",
        site_name=site_name,
        meta_description="Alle Whisky-Destillerien im Überblick: Schottland, Irland, Deutschland.",
        keywords="Whisky Destillerien, Lagavulin, Ardbeg, Glenfiddich, Bowmore",
        og_description="Alle Whisky-Destillerien im Überblick.",
        og_image=f"{base_url}/images/default.jpg",
        canonical_url=f"{base_url}/whisky-glossar/destillerien/",
        base_url=base_url,
        json_ld="",
        content=content,
    )


# ---------------------------------------------------------------------------
# Haupt-Build-Funktion
# ---------------------------------------------------------------------------

def build_glossary_pages(config: dict):
    """Wird von build_site() in site_builder_v2.py aufgerufen."""
    data = load_glossary_data()
    countries = data["countries"]
    regions = data["regions"]
    distilleries = data["distilleries"]
    whiskies = data["whiskies"]

    base = SITE_DIR / "whisky-glossar"
    base.mkdir(exist_ok=True)
    (base / "laender").mkdir(exist_ok=True)
    (base / "regionen").mkdir(exist_ok=True)
    (base / "destillerien").mkdir(exist_ok=True)
    (base / "whiskys").mkdir(exist_ok=True)

    # Glossar-Startseite
    _write_html(base / "index.html", build_glossary_index(data, config))

    # Länderseiten
    for c in countries:
        d = SITE_DIR / "whisky-glossar" / "laender" / c["slug"]
        d.mkdir(exist_ok=True)
        _write_html(d / "index.html",
                    build_country_page(c, regions, distilleries, whiskies, config))

    # Regions-Indexseite + Einzelseiten
    _write_html(base / "regionen" / "index.html",
                build_region_index(regions, countries, config))
    for r in regions:
        d = SITE_DIR / "whisky-glossar" / "regionen" / r["slug"]
        d.mkdir(exist_ok=True)
        _write_html(d / "index.html",
                    build_region_page(r, countries, distilleries, whiskies, config))

    # Destillerie-Indexseite + Einzelseiten
    _write_html(base / "destillerien" / "index.html",
                build_distillery_index(distilleries, regions, countries, config))
    for d in distilleries:
        dest = SITE_DIR / "whisky-glossar" / "destillerien" / d["slug"]
        dest.mkdir(exist_ok=True)
        _write_html(dest / "index.html",
                    build_distillery_page(d, countries, regions, whiskies, config))

    # Whisky-Detailseiten
    for w in whiskies:
        d = SITE_DIR / "whisky-glossar" / "whiskys" / w["slug"]
        d.mkdir(exist_ok=True)
        _write_html(d / "index.html",
                    build_whisky_page(w, countries, regions, distilleries, config))

    total = 1 + len(countries) + 1 + len(regions) + 1 + len(distilleries) + len(whiskies)
    print(f"  Whisky-Glossar: {total} Seiten erstellt "
          f"({len(countries)} Länder, {len(regions)} Regionen, "
          f"{len(distilleries)} Destillerien, {len(whiskies)} Whiskys).")
