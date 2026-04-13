# Whisky Magazin — Gesamtplan

> Zuletzt aktualisiert: April 2026

---

## 1. Vision & Positionierung

### Wer sind wir?

Das Whisky Magazin ist **Steffens persönliches Schottland-Tagebuch**, das seit 2009 wächst.
Kein Redaktionsbüro, keine PR-Samples, keine bezahlten Meinungen — sondern echte Reisen, echte Destilleriebesuche und ehrliche Eindrücke von zwei Typen, die Schottland wirklich kennen.

**Autoren:** Steffen & Elmar (Freunde seit Jahrzehnten, gemeinsame Schottland-Reisen ab 2009)

### Kernbotschaft

> „Schottland ist keine Destination. Es ist ein Zustand."

Wir verbinden **Whisky-Wissen** mit **Reise-Inspiration** auf eine Art, die kein Reiseführer kann: persönlich, eingebettet in echte Geschichten, mit 14 Jahren Ortskenntnissen.

### Zielgruppe

| Segment | Beschreibung |
|---|---|
| **Primär** | Deutschsprachige Männer 35–60, whiskybegeistert, reisefreudig |
| **Sekundär** | Paare & Gruppen, die Schottland-Urlaub planen |
| **Tertiär** | Whisky-Einsteiger, die Orientierung suchen |

### Abgrenzung zu Mitbewerbern

- **Nicht** eine weitere Whisky-Bewertungsseite (kein Whiskybase, kein Ralfy)
- **Nicht** ein Reise-Aggregator (kein TripAdvisor, kein Lonely Planet)
- **Einzigartig:** Reise + Destillerie + persönliche Geschichte in einem

---

## 2. Themen & Content-Strategie

### Fünf Inhaltssäulen

#### 🥃 Whisky (Kern)
- Destillerie-Porträts (Islay, Speyside, Highlands, Campbeltown, Orkney, Skye)
- Tasting Notes & Bewertungen (persönliche Stimme, kein Punkte-System)
- Wissensstücke: Fassreifung, Torfgrad, Regionen, Blending
- Aktuelle Releases & Limited Editions
- Vergleiche (Single Malt vs. Blended, Sherry vs. Bourbon Fass)
- Whisky des Monats (redaktionelles Herzstück)

#### ✈️ Reise (Schottland)
- Reiserouten & Roadtrips (NC500, Islay-Rundreise, Speyside Whisky Trail)
- Städte: Edinburgh, Glasgow, Inverness, Oban
- Inseln: Islay, Skye, Orkney, Jura, Arran
- Praktisches: Mietwagen, Fähren, Unterkunft, beste Reisezeit
- Erlebnisberichte aus unseren eigenen Reisen (2009–heute)

#### 🌿 Natur & Landschaft
- Highlands & Lochs
- Wandern in Schottland
- Schottische Wildnis: Stags, Adler, Herbstfarben

#### 🍽️ Lifestyle & Genuss
- Whisky & Food-Pairings (Käse, Schokolade, Meeresfrüchte)
- Schottische Küche
- Whisky als Geschenkidee / Investment
- Zubehör: Gläser, Karaffen, Adventskalender

#### 📰 Magazin / Stories
- Persönliche Reiseberichte (Ich-Perspektive)
- Portraits: Destillateure, lokale Charaktere
- Geschichte & Kultur Schottlands
- Saisonale Themen (Highland Games, Hogmanay, Whisky Festivals)

### Generierungs-Pipeline

```
topic_library.py     →  73+ vorbereitete Themen (kontinuierlich erweiterbar)
↓
OpenAI GPT-4o        →  1.200–2.500 Wörter, deutsch, SEO-optimiert
↓
articles/ (JSON)     →  Artikel-Archiv (aktuell 46 Artikel)
↓
site_builder_v2.py   →  Statische HTML-Seiten
```

**Rhythmus:** 2–4 neue Artikel pro Monat (manuell oder automatisch)

---

## 3. Design — Direction A: „Bright Highland Editorial"

*(Beschlossen. Implementiert in V2.)*

### Mood

> „Das erste Glas nach einem langen Wandertag — warm, zufrieden, neugierig auf mehr."
> Referenzen: Cereal Magazine, Bon Appetit, Afar Magazine

### Farbpalette

| Token | HEX | Einsatz |
|---|---|---|
| `--bg-primary` | `#FAFAF7` | Seitenhintergrund (warmes Weiß) |
| `--bg-surface` | `#F5F0E8` | Karten, Sections, Sidebar |
| `--text-primary` | `#1A1A1A` | Headlines, Fließtext |
| `--text-secondary` | `#5C5C5C` | Meta-Text, Captions |
| `--accent-amber` | `#C8963E` | Primärakzent — CTAs, Links |
| `--accent-sage` | `#4A7C5E` | Sekundärakzent — Natur, Badges |
| `--border` | `#E8DCC8` | Trennlinien, Card-Borders |

### Typografie

| Rolle | Font | Gewicht |
|---|---|---|
| Headlines / Display | **Fraunces** | 500–600 (italic für Zitate) |
| Body / UI | **Inter** | 400–600 |

### Layout-Prinzipien

- 12-Spalten-Grid, max-width 1200px, 32px Gutter
- Sections: 80px vertikaler Abstand
- Cards: 12px Radius, warme Schatten (`rgba(139,115,85,0.08)`)
- Header: Sticky, `backdrop-filter: blur(12px)`, weiß
- Keine Whisky-Klischee-Texturen (kein Leder, kein Tartan, kein Rauch)
- Bilder: Natürliches Licht, Golden Hour, echtes Schottland — kein Stock-Photo

### Logo

```
WHISKY · MAGAZIN
```
- „WHISKY" in Fraunces 600 · goldener Trennpunkt · „MAGAZIN" in Inter 600
- Favicon: goldenes „W" auf dunklem Quadrat (#1A1A1A)

---

## 4. Funktionalitäten

### Bereits implementiert ✅

| Funktion | Beschreibung | Datei |
|---|---|---|
| **KI-Artikelgenerierung** | GPT-4o, 1.200–2.500 Wörter, SEO-Tags | `content_generator.py` |
| **V2 Site Builder** | Statische HTML, Fraunces/Inter, Amber-Design | `site_builder_v2.py` |
| **Interaktive Karte** | 201 Orte, 110 Destillerien, Leaflet.js | `map_data_builder.py` |
| **Whisky des Monats** | KI-Tasting-Notes, Freigabe-Workflow, JSON-Archiv | `api/admin_wotm.py` |
| **Newsletter-System** | Entwurf generieren, Brevo-Versand, Double Opt-In | `api/admin_wotm.py` |
| **E-Mail-Benachrichtigungen** | Brevo Transactional API | `notifier.py` |
| **Auto-Push GitHub** | Nach jedem Build automatisch | `site_builder_v2.py` |
| **Affiliate-Links** | Amazon/Tradedoubler, automatisch eingebaut | `content_generator.py` |
| **Sitemap** | Für Google-Indexierung | `site_builder_v2.py` |
| **Artikel-Archiv** | 46 JSON-Artikel, alle Umlaute korrekt | `articles/` |

### Geplant / Nächste Schritte 🔜

| Funktion | Priorität | Aufwand |
|---|---|---|
| **Newsletter-Abonnenten gewinnen** | 🟡 Mittel | Ongoing |
| **Kommentar-Funktion** (z.B. Giscus) | 🟢 Low | 2–3h |
| **Foto-Galerie** aus Scotland-Archive | 🟢 Low | 4–6h |
| **Social-Media-Posting** (automatisch) | 🟢 Low | 3–4h |

### Bereits erledigt (seit März 2026) ✅

| Funktion | Status |
|---|---|
| Vercel V2 live auf whisky-reise.com | ✅ Erledigt |
| E-Mail-Benachrichtigungen (Brevo) | ✅ Erledigt |
| Newsletter-System (Brevo Double Opt-In) | ✅ Erledigt |
| Eigene Domain whisky-reise.com | ✅ Erledigt |
| Suchfunktion (clientseitig) | ✅ Erledigt |
| Admin-Dashboard mit 5 Tabs | ✅ Erledigt |
| Automatische Artikel-Generierung (Dashboard + Cron) | ✅ Erledigt |
| Whisky des Monats + Newsletter-Versand via Dashboard | ✅ Erledigt |
| Security-Audit + Fixes (CORS, Auth, CSP) | ✅ Erledigt April 2026 |

---

## 5. Technische Anbindungen

### Aktiv & konfiguriert

| Service | Zweck | Status |
|---|---|---|
| **OpenAI GPT-4o** | Artikelgenerierung, WOTM-Tasting-Notes | ✅ Live |
| **GitHub** (derhefter/whisky-magazin-v2) | Versionskontrolle + Hosting-Quelle | ✅ Auto-Push + Actions |
| **Vercel** | Hosting V2 (whisky-reise.com) | ✅ Live |
| **Brevo** | Newsletter Double Opt-In + Versand | ✅ Live |

### Konfiguration

**Lokal:** `config.json` (API-Keys, URLs — in `.gitignore`)
**Vercel:** Environment Variables (DASHBOARD_PASSWORD, GITHUB_TOKEN, BREVO_API_KEY, OPENAI_API_KEY, CRON_SECRET)

→ Vollständige Konfigurationsübersicht: siehe [BETRIEBSHANDBUCH.md](BETRIEBSHANDBUCH.md), Abschnitt 5

### Lokale Ordnerstruktur

```
Whisky_Ideen/
├── scotland-archive/          # Originalfotos aus 18 Jahren Schottland-Reisen
│   ├── 2009/ … 2024/
│   └── locations.json         # Geo-Daten zu den Foto-Standorten
│
└── whisky-magazin/            # Entwicklungsprojekt (V2, aktiv)
    ├── articles/              # 46 Artikel (JSON)
    ├── articles/drafts/       # Entwürfe (vom Dashboard verwaltet)
    ├── data/                  # WOTM, Newsletter-History, Karten-Daten
    ├── api/                   # Vercel Serverless Functions (8 Endpoints)
    ├── site-v2/               # Generierte V2-Website (→ Vercel)
    │   └── admin/index.html   # Admin-Dashboard
    └── [Python-Skripte]
```

### GitHub Repos

| Repo | Branch | Inhalt | Vercel |
|---|---|---|---|
| `derhefter/whisky-magazin-v2` | main | V2-Site + API | ✅ whisky-reise.com |

---

## 6. Einnahmen-Modell

### Direkt (kurzfristig)

| Quelle | Mechanismus | Potenzial |
|---|---|---|
| **Amazon Affiliate** | Links auf Flaschen, Bücher, Zubehör | 5–8% Provision |
| **Tradedoubler** | Whisky-Shops (Master of Malt, etc.) | 3–6% Provision |
| **Whisky-des-Monats** | Monatliche kuratierte Empfehlung | 1 Klick × viele Leser |

### Indirekt (mittelfristig)

| Quelle | Voraussetzung |
|---|---|
| **Newsletter-Sponsoring** | 500+ Abonnenten |
| **Destillerie-Kooperationen** | Reichweite + Glaubwürdigkeit |
| **Digitale Produkte** | Reiseführer-PDF, Whisky-Tasting-Kurs |

### Kosten

| Posten | Betrag |
|---|---|
| OpenAI API (12 Artikel/Monat) | ca. 1–2 EUR/Monat |
| Hosting (Vercel Free Tier) | 0 EUR |
| Domain (optional) | ca. 10 EUR/Jahr |
| Brevo (bis 300 E-Mails/Tag) | 0 EUR |

---

## 7. Redaktions-Workflow (monatlich, ab Einrichtung automatisch)

```
Montags automatisch
    └── Windows Task Scheduler generiert 2 Artikel-Entwürfe
    └── E-Mail-Benachrichtigung an rosenhefter@gmail.com

Steffen prüft im Dashboard (whisky-reise.com/admin)
    └── Tab "Artikel" → Entwürfe prüfen, bearbeiten, freigeben

Mittwoch + Samstag 10:00 CEST automatisch
    └── Vercel Cron veröffentlicht freigegebene Artikel
    └── GitHub Actions baut Website neu

Monatlich: Whisky des Monats (Dashboard)
    └── Tab "WotM & Newsletter" → Formular ausfüllen
    └── KI poliert Tasting Notes → Newsletter generieren → Vorschau → Senden via Brevo
```

---

## 8. Versions-Geschichte

| Version | Design | Status | URL |
|---|---|---|---|
| **V1 Classic** | Original-Design (2024) | Archiviert | — |
| **V2 Bright Highland Editorial** | Fraunces/Inter, Amber-Palette | ✅ Live | whisky-reise.com |

---

## 9. Offene Entscheidungen

1. **Kommentare:** Giscus (GitHub-basiert) oder ohne?
2. **Sprache:** Rein deutsch bleiben, oder perspektivisch englische Artikel?
3. **Social Media:** Instagram (Fotos) oder primär Newsletter-Fokus?

### Bereits entschieden ✅
- ~~Domain~~ → whisky-reise.com (live)
- ~~V1 abschalten~~ → V1 archiviert, V2 ist live
