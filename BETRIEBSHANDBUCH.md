# Whisky Magazin -- Betriebshandbuch

Stand: April 2026

---

## 1. Systemuebersicht

### Architektur

```
                    +------------------+
                    |  whisky-reise.com |
                    |   (Vercel)        |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
     +--------+--------+          +--------+--------+
     | Statische Seite  |          | API-Endpoints   |
     | (site-v2/)       |          | (api/*.py)       |
     | HTML/CSS/JS      |          | Python Serverless|
     +---------+--------+          +--------+--------+
               |                            |
     +---------+--------+     +-------------+-------------+
     | GitHub Actions    |     | Externe Services          |
     | (Auto-Rebuild)    |     | - Brevo (Newsletter)      |
     +---------+--------+     | - OpenAI (KI-Texte)       |
               |               | - GitHub API (Dateien)    |
     +---------+--------+     +---------------------------+
     | GitHub Repo       |
     | derhefter/        |
     | whisky-magazin-v2 |
     +-------------------+
```

### URLs

| Was | URL |
|-----|-----|
| **Website** | https://www.whisky-reise.com |
| **Admin-Dashboard** | https://www.whisky-reise.com/admin/ |
| **GitHub-Repo** | https://github.com/derhefter/whisky-magazin-v2 |
| **Vercel-Dashboard** | https://vercel.com (Projekt: whisky-magazin-new) |
| **Brevo-Dashboard** | https://app.brevo.com |

### Automatischer Betrieb

Das System laeuft weitgehend automatisch:

| Zeitpunkt | Was passiert | Wer/Was |
|-----------|-------------|---------|
| **Montag 07:00 Uhr** | 2 neue Artikel-Entwuerfe werden generiert | Windows Task Scheduler (lokal) |
| **Nach Generierung** | E-Mail an rosenhefter@gmail.com | Brevo Transactional API |
| **Mittwoch 10:00 CEST** | Aeltester freigegebener Entwurf wird veroeffentlicht | Vercel Cron-Job |
| **Samstag 10:00 CEST** | Aeltester freigegebener Entwurf wird veroeffentlicht | Vercel Cron-Job |
| **Bei Artikel-Aenderung** | Website wird automatisch neu gebaut | GitHub Actions |

**Du musst nur:** Entwuerfe im Dashboard pruefen und freigeben. Alles andere laeuft automatisch.

---

## 2. Admin-Dashboard -- Komplett-Anleitung

### 2.1 Login

1. Oeffne https://www.whisky-reise.com/admin/
2. Gib das Passwort ein (gespeichert in Vercel -> Settings -> Environment Variables -> `DASHBOARD_PASSWORD`)
3. Klicke "Anmelden"

**Session:** Die Anmeldung bleibt 24 Stunden gueltig, auch wenn du den Tab schliesst. Danach musst du dich erneut anmelden.

**Probleme beim Login:**

| Fehlermeldung | Ursache | Loesung |
|---------------|---------|---------|
| "Falsches Passwort" | Passwort stimmt nicht | Vercel -> Settings -> Env Vars -> `DASHBOARD_PASSWORD` pruefen |
| "Server-Fehler" | `DASHBOARD_PASSWORD` nicht gesetzt | In Vercel setzen und neu deployen |
| "Zu viele Versuche" | 5 Fehlversuche in 15 Min. | 15 Minuten warten |
| "Netzwerkfehler" | Keine Internetverbindung oder Vercel down | Verbindung pruefen |

---

### 2.2 Tab: Uebersicht

Zeigt 4 Kennzahlen auf einen Blick:

| KPI | Bedeutung |
|-----|-----------|
| **Abonnenten** | Anzahl Newsletter-Abonnenten in Brevo |
| **Entwuerfe** | Anzahl offener Artikel-Entwuerfe (ausstehend + freigegeben) |
| **Themen offen** | Noch nicht bearbeitete Themen aus der Themen-Queue |
| **Themen erledigt** | Bereits bearbeitete Themen |

Jede Karte ist **klickbar** und navigiert direkt zum zugehoerigen Tab.

---

### 2.3 Tab: Artikel verwalten

Hier siehst du alle Entwuerfe und veroeffentlichten Artikel.

#### Artikel-Status

| Status | Bedeutung | Badge-Farbe |
|--------|-----------|-------------|
| **Ausstehend** | Neu generiert, wartet auf Pruefung | Gelb |
| **In Bearbeitung** | Wurde bearbeitet, noch nicht freigegeben | Blau |
| **Freigegeben** | Wird beim naechsten Cron-Lauf veroeffentlicht (Mi/Sa 10:00) | Gruen |

#### Workflow: Artikel pruefen und freigeben

1. Oeffne den **Artikel**-Tab
2. Fuer jeden Entwurf hast du folgende Aktionen:
   - **Vorschau** (Auge-Icon): Zeigt den Artikel so, wie er spaeter aussehen wird
   - **Bearbeiten** (Stift-Icon): Oeffnet ein Formular zum Aendern von Titel, Teaser und HTML-Inhalt
   - **Freigeben** (Haekchen): Setzt den Status auf "Freigegeben" -- der Artikel wird beim naechsten Cron-Lauf veroeffentlicht
   - **Jetzt veroeffentlichen** (Rakete, nur bei freigegebenen): Veroeffentlicht sofort, ohne auf den Cron zu warten
   - **Ablehnen** (X): Loescht den Entwurf unwiderruflich

3. **Bearbeiten-Formular:**
   - **Titel**: Wird als Ueberschrift und in der URL verwendet
   - **Teaser**: Kurzbeschreibung fuer Artikelkarten und SEO-Meta-Description
   - **HTML-Inhalt**: Der vollstaendige Artikeltext in HTML. Absaetze in `<p>`, Ueberschriften in `<h2>` / `<h3>`
   - Klicke "Speichern" nach Aenderungen

4. **Aktualisieren**: Button oben rechts laedt die Liste neu

#### Was passiert nach der Freigabe?

1. Der Entwurf bekommt den Status "Freigegeben"
2. Beim naechsten Cron-Lauf (Mi oder Sa, 10:00 CEST) wird der **aelteste** freigegebene Entwurf veroeffentlicht
3. Der Artikel wird von `articles/drafts/` nach `articles/` verschoben
4. GitHub Actions baut die Website automatisch neu
5. Vercel deployt die neue Version
6. Der Artikel ist nach ca. 2-3 Minuten live

---

### 2.4 Tab: Themen verwalten

Die Themen-Queue steuert, welche Themen der KI-Generator als naechstes bearbeitet.

#### Funktionen

| Aktion | Wie |
|--------|-----|
| **Filtern** | Oben: Filter nach Saison (Fruehling/Sommer/Herbst/Winter/Ostern/Weihnachten/Silvester) und Status (Offen/In Bearbeitung/Erledigt) |
| **Neues Thema** | Button "Neues Thema" oben rechts -> Titel, Kategorie, Saison, Prioritaet eingeben -> Speichern |
| **Erledigt markieren** | Haekchen-Icon in der Zeile klicken |
| **Loeschen** | Papierkorb-Icon in der Zeile klicken (nach Bestaetigung) |
| **Artikel generieren** | Blitz-Icon (⚡) -> Erzeugt einen KI-Entwurf direkt aus dem Thema (dauert ca. 20-30 Sek.) |

#### Themen-Felder

| Feld | Beschreibung |
|------|-------------|
| **Titel** | Thema des zu erstellenden Artikels |
| **Kategorie** | Whisky, Reise, Lifestyle, Natur, Urlaub |
| **Saison** | Wann das Thema am besten passt |
| **Anlass** | Optionaler Anlass (Ostern, Weihnachten, etc.) |
| **Prioritaet** | 1-20, hoeher = wichtiger |
| **Notizen** | Interne Notizen/Hinweise fuer die Generierung |

#### Tipp: Artikel direkt generieren

Klicke das ⚡-Icon neben einem Thema, um sofort einen KI-Entwurf erstellen zu lassen. Der Entwurf erscheint dann im **Artikel**-Tab zur Pruefung.

---

### 2.5 Tab: Whisky des Monats & Newsletter

Dieser Tab hat zwei Bereiche: Links das WotM-Formular, rechts den Newsletter-Versand.

#### Schritt 1: WotM-Eintrag erstellen

1. **Monat waehlen** im Dropdown oben
2. **Pflichtfelder ausfuellen:**
   - **Whisky-Name**: z.B. "Lagavulin 16 Jahre"
   - **Destillerie**: z.B. "Lagavulin Distillery"
   - **Region**: z.B. "Islay"
   - **Kommentar**: Deine persoenlichen Eindrucke (Freitext). Wird von der KI in einen warmen, persoenlichen Stil umformuliert.

3. **Optionale Felder:**
   - **Destillerie-URL**: Link zur Destillerie-Seite auf whisky-reise.com (falls vorhanden)
   - **Specials / News**: Aktuelle Nachrichten oder besondere Hinweise. Wird als Prosa-Abschnitt im Newsletter dargestellt.
   - **Intro-Text**: Persoenlicher Einfuehrungstext fuer den Newsletter. Wird automatisch von der KI generiert, kann aber ueberschrieben werden.
   - **Affiliate-Link**: Amazon-Link zum Whisky (wird automatisch generiert wenn der Whisky-Name bekannt ist)
   - **Tasting Notes** (aufklappbar):
     - **Aroma**: Geruchsbeschreibung
     - **Geschmack**: Geschmacksbeschreibung
     - **Abgang**: Nachklang
     - **Bewertung**: 0-100 Punkte
     - **Alter**: in Jahren
     - **ABV**: Alkoholgehalt in %
     - **Preis**: in EUR

4. **Fotos** (bis zu 4): Klicke "Fotos waehlen" und waehle JPG/PNG-Dateien aus. Werden als Base64 gespeichert.

5. **Artikel-Teaser** (bis zu 3): Werden automatisch mit den neuesten Artikeln befuellt. Titel, URL und Teaser koennen manuell ueberschrieben werden.

6. Klicke **"Speichern"**

#### Schritt 2: Newsletter generieren

1. Klicke **"Newsletter generieren"** (Blitz-Icon)
2. Die KI poliert automatisch:
   - Deinen Kommentar (persoenlicher Stil)
   - Die Specials (Prosa statt Stichpunkte)
   - Den Intro-Text (wenn leer)
3. Eine **HTML-Vorschau** erscheint im iFrame darunter
4. Optional: Klicke "HTML-Quelltext anzeigen" um den Code direkt zu bearbeiten
5. Klicke **"Newsletter speichern"** um die finale Version zu sichern
6. Zum Neugenerieren mit aktualisierten Feldern: **"Neu generieren"** klicken

#### Schritt 3: Newsletter senden

1. Im rechten Bereich **"Newsletter senden"**: Monat im Dropdown waehlen
2. Klicke **"Newsletter jetzt senden"**
3. Bestaetigung im Dialog
4. Der Newsletter wird ueber Brevo an alle Abonnenten gesendet
5. Erfolg: Kampagnen-ID wird angezeigt

**Wichtig:** Immer erst Newsletter generieren und in der Vorschau pruefen, bevor du sendest!

---

### 2.6 Tab: Newsletter

Zeigt die aktuelle Abonnenten-Statistik:
- Gesamtzahl der Newsletter-Abonnenten
- Liste der letzten Anmeldungen mit E-Mail und Datum
- Daten kommen direkt von der Brevo-API

---

## 3. Automatisierung

### 3.1 Windows Task Scheduler (lokale Artikel-Generierung)

| Eigenschaft | Wert |
|------------|------|
| **Task-Name** | `WhiskyMagazin-AutoGenerate` |
| **Zeitplan** | Jeden Montag, 07:00 Uhr |
| **Befehl** | `python main.py --auto -n 2` |
| **Arbeitsverzeichnis** | `C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin` |
| **Log** | `magazin.log` im Projektordner |

**Was passiert:**
1. 2 Artikel-Entwuerfe werden per GPT-4o generiert
2. Entwuerfe werden als JSON in `articles/drafts/` auf GitHub gepusht
3. Benachrichtigungs-E-Mail wird an rosenhefter@gmail.com gesendet
4. Entwuerfe erscheinen im Dashboard unter "Artikel"

**Task manuell ausfuehren (z.B. fuer Tests):**
```
cd "C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin"
python main.py --auto -n 3
```

**Task pruefen/aendern:**
1. Windows-Taste -> "Aufgabenplanung" suchen und oeffnen
2. Links: "Aufgabenplanungsbibliothek" klicken
3. Task `WhiskyMagazin-AutoGenerate` suchen
4. Rechtsklick -> "Eigenschaften" zum Aendern, "Ausfuehren" zum manuellen Start

### 3.2 Vercel Cron-Jobs (automatische Veroeffentlichung)

Konfiguriert in `vercel.json`:

| Zeitpunkt | Schedule (UTC) | Aktion |
|-----------|---------------|--------|
| **Mittwoch 10:00 CEST** | `0 8 * * 3` | Aeltesten freigegebenen Entwurf veroeffentlichen |
| **Samstag 10:00 CEST** | `0 8 * * 6` | Aeltesten freigegebenen Entwurf veroeffentlichen |

**Ablauf:**
1. Cron ruft `/api/admin_publish` auf
2. Sucht den aeltesten Entwurf mit Status "approved"
3. Verschiebt ihn von `articles/drafts/` nach `articles/`
4. Entfernt interne Felder (_status, _generated_at, _topic_id)
5. Markiert das zugehoerige Thema als "done"
6. Loescht die Draft-Datei
7. GitHub Actions baut die Seite automatisch neu

### 3.3 GitHub Actions (automatischer Site-Rebuild)

Datei: `.github/workflows/build.yml`

**Trigger:** Wenn Dateien in `articles/*.json` oder `data/topics_queue.json` geaendert werden (Push auf `main`).

**Ablauf:**
1. Checkout des Repos
2. Python + Abhaengigkeiten installieren
3. `config.json` wird zur Laufzeit aus fest hinterlegten Werten erstellt (die Datei ist in `.gitignore` und nicht im Repo)
4. `build_site()` aus `site_builder_v2.py` ausfuehren
5. Generierte `site-v2/` Dateien committen (Commit-Nachricht: "Auto-Build: Artikel veroeffentlicht [skip ci]") und pushen
6. Vercel erkennt den Push und deployt automatisch

**Hinweis:** Das `[skip ci]` im Commit-Nachricht verhindert, dass der Build sich selbst in einer Endlosschleife aufruft.

**Zweiter Workflow – `auto-generate.yml`:** Kein automatischer Zeitplan mehr (deaktiviert April 2026). Nur noch manuell ueber "workflow_dispatch" ausfuehren falls der Windows Task Scheduler ausnahmesweise ausfaellt. Der Workflow erstellt dann Entwuerfe (nicht direkt veroeffentlichte Artikel).

### 3.4 E-Mail-Benachrichtigungen

Jedes Mal wenn `python main.py --auto` laeuft (Montag 07:00 per Task Scheduler), sendet das System eine HTML-E-Mail via Brevo Transactional API:

| Eigenschaft | Wert |
|------------|------|
| **Empfaenger** | rosenhefter@gmail.com |
| **Absender** | whisky-news@whisky-reise.com (via Brevo) |
| **Betreff** | "X neue Whisky-Artikel warten auf Freigabe" |
| **Inhalt** | Titel, Kategorie, Teaser und Wortanzahl jedes Entwurfs; Direktlink zum Dashboard; naechste Veroeffentlichungstermine (Mi + Sa) |

**Voraussetzung:** `BREVO_API_KEY` muss in der lokalen `.env`-Datei stehen.

**E-Mail manuell testen:**
```bash
cd "C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin"
python -c "from notifier import notify_new_drafts; notify_new_drafts([{'title':'Test','category':'Whisky','meta':{'teaser':'Testteaser'},'html_content':'<p>Test</p>'}])"
```

---

## 4. Manuelle Operationen

### 4.1 Artikel lokal generieren

```bash
cd "C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin"

# Einen Artikel als Entwurf generieren:
python main.py --auto -n 1

# Drei Artikel generieren:
python main.py --auto -n 3

# Nur generieren (ohne Build):
python main.py --generate -n 2

# Interaktives Menue:
python main.py
```

### 4.2 Website lokal bauen und testen

```bash
# Website komplett neu bauen (generiert alle HTML-Seiten):
python main.py --build-v2

# Lokalen Webserver starten (zum Testen):
python main.py --serve-v2
# Oeffnet http://localhost:8000
```

### 4.3 Artikel direkt bearbeiten (ohne Dashboard)

Artikel liegen als JSON in `articles/`. Jede Datei ist ein Artikel.

**Dateiname-Format:** `YYYY-MM-DD_slug-des-artikels.json`

**Wichtige Felder:**
```json
{
  "title": "Titel des Artikels",
  "date": "2026-04-12",
  "category": "Whisky",
  "html_content": "<p>Der HTML-Inhalt...</p>",
  "image_url": "/images/slug-des-artikels.jpg",
  "image_alt": "Bildbeschreibung",
  "meta": {
    "slug": "slug-des-artikels",
    "meta_description": "SEO-Beschreibung (max 160 Zeichen)",
    "teaser": "Kurzbeschreibung fuer Karten"
  }
}
```

**Aendern:**
1. JSON-Datei in `articles/` oeffnen
2. `html_content` bearbeiten (HTML-Format: `<p>`, `<h2>`, `<h3>`)
3. `python main.py --build-v2` ausfuehren

### 4.4 Bilder verwalten

- Bilder liegen in `site-v2/images/`
- Werden automatisch von Unsplash heruntergeladen bei der Generierung
- **Eigene Bilder:** Als JPG in `site-v2/images/` ablegen, Dateiname = Slug des Artikels
- In der Artikel-JSON: `"image_url": "/images/dateiname.jpg"` setzen

### 4.5 Karten-Eintraege hinzufuegen

Datei: `data/manual-locations.json`

Neuen Eintrag hinzufuegen:
```json
{
  "name": "Name der Destillerie",
  "lat": 57.123,
  "lon": -4.567,
  "type": "distillery",
  "region": "Speyside",
  "visited": true,
  "year": 2023,
  "note": "Tolle Tour!"
}
```

Danach: `python main.py --build-v2`

### 4.6 Produkte / Affiliate-Links anpassen

Datei: `data/products.json`

```json
{
  "whiskys": {
    "produkt-key": {
      "name": "Produktname",
      "asin": "B001TZBIBY",
      "price_range": "30-38",
      "region": "Highlands",
      "category": "Single Malt",
      "short": "Kurzbeschreibung"
    }
  }
}
```

- **ASIN finden:** Auf Amazon die Produkt-URL anschauen -> `/dp/B001TZBIBY/`
- **Amazon-Tag:** `whiskyreise74-21` (in `config.json` hinterlegt)

### 4.7 Seiten im Site-Builder anpassen

Alle Seiten werden von `site_builder_v2.py` generiert:

| Seite | Funktion im Builder | Wann aendern |
|-------|-------------------|-------------|
| Startseite | `build_index_page()` (~Zeile 1800) | Hero-Text, Trust-Stats, Anzahl Artikel |
| Artikel | `build_article_page()` | Automatisch aus JSON |
| Kategorie-Seiten | `build_category_page()` | Automatisch; Meta-Descriptions im Dict `_category_descriptions` innerhalb der Funktion pflegen |
| Karte | `build_map_page()` (~Zeile 2100) | Bei Kartendesign-Aenderungen |
| Ueber uns | `build_about_page()` (~Zeile 3030) | Autoren-Info, Statistiken |
| Impressum | `build_impressum_page()` (~Zeile 3388) | Bei Adress- oder Kontaktaenderungen -- Seite traegt automatisch `noindex, follow` und ist nicht in der Sitemap |
| Datenschutz | `build_datenschutz_page()` (~Zeile 3468) | Bei neuen Trackern/Affiliates -- Seite traegt automatisch `noindex, follow` und ist nicht in der Sitemap |
| Suche | `build_suche_page()` (~Zeile 3740) | Selten -- Seite traegt automatisch `noindex, follow` und ist nicht in der Sitemap |
| Sitemap | `build_sitemap()` (~Zeile 3894) | Bewusst ohne impressum, datenschutz, suche. Neue SEO-irrelevante Seiten hier ebenfalls weglassen |
| Navigation | `_base_template()` (~Zeile 1150) | Bei neuen Menue-Eintraegen |
| `<head>`-Meta-Tags | `_base_template()` (~Zeile 282) | Bei neuen Verification-Tags (Google, Pinterest, etc.) |

**SEO-Hinweis:** Neue Seiten, die nicht indexiert werden sollen (Utility-, Legal- oder Duplikat-Seiten), muessen zwei Dinge bekommen: (1) `<meta name="robots" content="noindex, follow">` im `<head>` und (2) keinen Eintrag in `build_sitemap()`. Beides wird im Builder per Post-Processing (`.replace()`-Aufruf nach `.format()`) und durch Weglassen in der `static_pages`-Liste geloest -- analog zu impressum/datenschutz/suche.

Nach jeder Aenderung: `python main.py --build-v2`

#### Webmaster-Verification-Tags

Im `<head>`-Bereich jeder Seite sind aktuell folgende Verification-Tags hinterlegt (in `_base_template()`, ~Zeile 271 in `site_builder_v2.py`):

| Dienst | Meta-Tag |
|--------|---------|
| Google Search Console | `<meta name="google-site-verification" content="3OKzP9zKRrZV5V4-chXaN7GG39fdLAEeymXqKeqn4Rw">` |
| Pinterest | `<meta name="p:domain_verify" content="4b7a0461f2dd530e9a9c5894618a229d">` |

Neuen Verification-Tag hinzufuegen: Einfach in `_base_template()` unterhalb der bestehenden Tags eintragen, dann `python main.py --build-v2` ausfuehren. Der Tag erscheint automatisch auf **allen** generierten Seiten.

#### Pinterest Tracking Tag (Pixel)

Zusaetzlich zum Verification-Tag ist der **Pinterest Pixel** (Tag-ID: `2613413631015`) auf allen Seiten aktiv. Er wird durch die Konstante `_PINTEREST_TAG` in `site_builder_v2.py` (Zeile ~22) definiert und von `_write_html()` automatisch vor `</head>` jeder HTML-Datei eingefuegt.

| Event | Seite | Zweck |
|-------|-------|-------|
| `PageView` | Alle Seiten | Seitenaufrufe tracken, Zielgruppe aufbauen |
| `lead` | `danke.html` | Newsletter-Anmeldung als Conversion zaehlen |

**Pinterest Tag-ID aendern oder deaktivieren:** Konstante `_PINTEREST_TAG` in `site_builder_v2.py` anpassen, dann neu bauen.

**Naechster Schritt (Auto-Pinnen):** Artikel koennen automatisch beim Veroeffentlichen als Pinterest-Pin erstellt werden. Dafuer werden benoetigt:
- `PINTEREST_ACCESS_TOKEN` (aus Pinterest Developer App)
- `PINTEREST_BOARD_ID` (Ziel-Pinnwand)
Beide als Vercel Environment Variables setzen.

---

## 5. Konfiguration

### 5.1 Vercel Environment Variables

Alle hier aufgefuehrten Variablen muessen in Vercel unter **Settings -> Environment Variables** gesetzt sein.

| Variable | Beschreibung | Beispielwert |
|----------|-------------|--------------|
| `DASHBOARD_PASSWORD` | Login-Passwort fuer /admin | (frei waehlbar, sicher!) |
| `CRON_SECRET` | Absicherung der Mi/Sa-Cron-Jobs gegen unberechtigte Aufrufe | (langer Zufalls-String, mind. 32 Zeichen) |
| `GITHUB_TOKEN` | Fine-grained PAT mit read+write auf das Repo | ghp_... |
| `GITHUB_REPO` | Repository-Pfad | `derhefter/whisky-magazin-v2` |
| `GITHUB_BRANCH` | Branch (Standard: main) | `main` |
| `BREVO_API_KEY` | Brevo API-Key fuer Newsletter + Abonnenten-Statistik | xkeysib-... |
| `BREVO_LIST_ID` | Brevo Newsletter-Listen-ID | `3` |
| `OPENAI_API_KEY` | OpenAI Key fuer KI-Texte (WotM-Polishing + Dashboard-Generierung) | sk-... |
| `UNSPLASH_API_KEY` | Unsplash Key fuer automatische Artikelbilder (Dashboard-Generierung) | (Unsplash Developer Key) |
| `SITE_URL` | Basis-URL der Seite | `https://www.whisky-reise.com` |

**Wichtig:** Nach jeder Aenderung an Environment Variables muss Vercel **neu deployt** werden!

**Neuen CRON_SECRET setzen (einmalig):**
1. Vercel Dashboard -> Settings -> Environment Variables
2. Neue Variable: Name = `CRON_SECRET`, Value = ein langer zufaelliger String (z.B. via Passwort-Generator, mind. 32 Zeichen)
3. Neu deployen

### 5.2 Lokale Konfiguration

#### `.env` (im Projektordner, nicht in Git)
```
BREVO_API_KEY=xkeysib-...        # Pflicht: fuer E-Mail-Benachrichtigungen (montags)
OPENAI_API_KEY=sk-proj-...       # Optional: wird auch aus config.json gelesen
CRON_SECRET=...                  # Nur fuer Vercel noetig, lokal nicht benoetigt
```
`BREVO_API_KEY` ist Pflicht fuer die montaegliche E-Mail-Benachrichtigung an rosenhefter@gmail.com. Ohne diesen Key wird die E-Mail uebersprungen (kein Fehler, nur kein Versand).

#### `config.json` (im Projektordner, nicht in Git)

| Feld | Beschreibung | Wann aendern |
|------|-------------|-------------|
| `site.base_url` | Basis-URL der Seite | Bei Domain-Wechsel |
| `site.name` | Seitenname | Bei Umbenennung |
| `site.author` | Autoren | Bei Aenderung |
| `openai.api_key` | OpenAI API Key | Bei Key-Erneuerung |
| `openai.model` | GPT-Modell | Bei Modellwechsel |
| `affiliate_links.amazon_tag` | Amazon Partner-Tag | Bei Tag-Aenderung |
| `content_settings.unsplash_api_key` | Unsplash Key | Bei Key-Erneuerung |

### 5.3 Brevo-Setup (Newsletter)

| Einstellung | Wert |
|------------|------|
| **Kontaktliste** | Liste ID `3` ("Whisky Magazin Newsletter") |
| **DOI Template** | Template ID `1` (Bestaetigungs-E-Mail mit `{{ doubleoptin }}` Link) |
| **Redirect nach DOI** | https://www.whisky-reise.com/danke.html |

**Pruefen:** https://app.brevo.com -> Kontakte -> Listen

---

## 6. Sicherheit & Wartung

### 6.1 Passwort-Rotation

Das Dashboard-Passwort sollte regelmaessig geaendert werden:

1. Vercel Dashboard -> Settings -> Environment Variables
2. `DASHBOARD_PASSWORD` aendern
3. Vercel neu deployen
4. Neues Passwort sicher notieren (z.B. Passwort-Manager)

**Achtung:** Alle aktiven Sessions werden nach dem Wechsel ungueltig (Token basiert auf dem Passwort).

### 6.2 GitHub Token erneuern

GitHub Fine-Grained Personal Access Tokens laufen ab. So erneuerst du:

1. https://github.com/settings/tokens -> "Fine-grained tokens"
2. Neuen Token erstellen:
   - Repository: `derhefter/whisky-magazin-v2`
   - Permissions: Contents (Read and Write)
   - Expiration: max. 1 Jahr
3. Token kopieren
4. In Vercel unter `GITHUB_TOKEN` den neuen Token eintragen
5. Vercel neu deployen
6. In `.github/workflows/build.yml` ggf. das Repository Secret aktualisieren

### 6.3 API-Key-Management

| Key | Wo gespeichert | Ablauf | Erneuern unter |
|-----|---------------|--------|----------------|
| OpenAI | `config.json` (lokal) + Vercel | Laeuft nicht ab, kann widerrufen werden | https://platform.openai.com/api-keys |
| Unsplash | `config.json` (lokal) | Laeuft nicht ab | https://unsplash.com/oauth/applications |
| Brevo | `.env` (lokal) + Vercel | Laeuft nicht ab | https://app.brevo.com -> Settings -> API Keys |
| GitHub | Vercel | Fine-grained: max 1 Jahr | https://github.com/settings/tokens |

### 6.4 Sicherheitsfeatures (implementiert)

- **HMAC-SHA256 Token-Authentifizierung** mit 24-Stunden-Ablauf
- **Rate Limiting** auf Login (max. 5 Versuche / 15 Minuten)
- **CORS-Einschraenkung** auf `whisky-reise.com` und `localhost:8000`
- **Content Security Policy** (getrennte Regeln fuer Public und Admin)
- **Path-Traversal-Schutz** (Dateinamen-Validierung per Regex)
- **CRON_SECRET** fuer Vercel Cron-Authentifizierung
- **noindex/nofollow** auf Admin-Seiten
- **Double Opt-In** fuer Newsletter (DSGVO-konform)
- **Cookie-Consent-Banner** auf allen oeffentlichen Seiten

### 6.5 Bekannte Einschraenkungen

- Rate Limiting auf Admin-Operationen (Artikel, Themen, WotM) existiert nicht serverseitig, da Vercel Serverless Functions keinen persistenten Speicher haben. Die Token-basierte Authentifizierung bietet jedoch ausreichenden Schutz.
- Der Admin-Bereich nutzt `unsafe-inline` fuer JavaScript in der CSP, da das Dashboard ein Single-Page-HTML ist. Fuer die oeffentliche Seite ist `unsafe-inline` nur fuer Styles aktiv (benoetig fuer Leaflet.js).

---

## 7. Fehlerbehebung

### 7.1 Haeufige Probleme

| Problem | Moegliche Ursache | Loesung |
|---------|-------------------|---------|
| Dashboard zeigt "Fehler" | GITHUB_TOKEN abgelaufen | Neuen Token in Vercel setzen + neu deployen |
| Dashboard zeigt Nullen ueberall | Env Vars fehlen oder falsch | `/api/admin_debug` aufrufen (nach Login) |
| Artikel werden nicht veroeffentlicht | Keine freigegebenen Entwuerfe | Im Artikel-Tab pruefen und freigeben |
| Artikel werden nicht veroeffentlicht | Cron-Job laeuft nicht | Vercel Dashboard -> Cron Jobs pruefen |
| Artikel ist im Dashboard "veroeffentlicht" aber nicht auf der Seite | `meta.slug` fehlte in der JSON-Datei | `python main.py --build-v2` ausfuehren — der Builder normalisiert fehlende Slugs automatisch seit April 2026 |
| Artikel hat kein Bild | `UNSPLASH_API_KEY` fehlt in Vercel | In Vercel setzen + neu deployen; dann Artikel im Dashboard neu generieren |
| E-Mail kommt nicht (montags) | `BREVO_API_KEY` fehlt in `.env` | `.env` Datei pruefen: `BREVO_API_KEY=xkeysib-...` |
| /admin zeigt 404 | Deployment veraltet | Vercel manuell neu deployen |
| Thema wird nicht gespeichert | GITHUB_TOKEN abgelaufen | Neuen Token setzen + neu deployen |
| Newsletter-Versand schlaegt fehl | BREVO_API_KEY fehlt in Vercel | In Vercel setzen + neu deployen |
| KI-Texte werden nicht poliert | OPENAI_API_KEY fehlt in Vercel | In Vercel setzen + neu deployen |
| Bilder fehlen auf der Seite | Bild nicht in `site-v2/images/` | Bild ablegen + `python main.py --build-v2` |
| Website nicht aktuell | Build nicht gelaufen | Manuell: `python main.py --build-v2` + `git push` |
| GitHub Actions Build schlaegt fehl | `OPENAI_API_KEY` Secret fehlt in GitHub | GitHub -> Repo -> Settings -> Secrets -> `OPENAI_API_KEY` setzen |

### 7.2 Debug-Endpoint

Nach dem Login im Dashboard kannst du den Debug-Endpoint aufrufen:

```
GET https://www.whisky-reise.com/api/admin_debug
Header: x-admin-token: <dein-token>
```

Zeigt:
- Welche Environment Variables gesetzt sind (ja/nein, keine Werte!)
- GitHub API Verbindungsstatus
- Brevo API Verbindungsstatus
- Drafts-Verzeichnis Inhalt

### 7.3 Notfall-Prozeduren

#### Seite ist komplett down
1. Vercel Dashboard pruefen -> Deployments
2. Letztes funktionierendes Deployment -> "Redeploy" klicken
3. Falls Git-Problem:
```bash
cd "C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin"
git status
git push
```

#### GitHub Token abgelaufen (Dashboard funktioniert nicht)
1. https://github.com/settings/tokens -> Neuen Token erstellen
2. Vercel -> Settings -> Env Vars -> `GITHUB_TOKEN` aktualisieren
3. Vercel neu deployen (Deployments -> letztes -> Redeploy)

#### Brevo API Key kompromittiert
1. https://app.brevo.com -> Settings -> API Keys -> Alten Key loeschen
2. Neuen Key erstellen
3. Vercel -> Env Vars -> `BREVO_API_KEY` aktualisieren
4. Lokal in `.env` aktualisieren
5. Vercel neu deployen

#### Artikel manuell veroeffentlichen (wenn Cron nicht laeuft)
1. Dashboard -> Artikel-Tab -> Entwurf freigeben
2. "Jetzt veroeffentlichen" (Rakete-Icon) klicken
3. Oder: Browser-Aufruf: `https://www.whisky-reise.com/api/admin_publish` (mit Admin-Token im Header)

---

## 8. Ordnerstruktur

```
whisky-magazin/
+-- articles/               Veroeffentlichte Artikel (JSON)
|   +-- drafts/             Entwuerfe (vom Dashboard verwaltet)
|   +-- rejected/           Abgelehnte Entwuerfe
+-- data/
|   +-- topics_queue.json   Themen-Queue fuer Generator
|   +-- products.json       Amazon-Produkte + ASINs
|   +-- manual-locations.json  Karteneintraege (201 Orte)
|   +-- whisky-of-the-month.json  WotM-Archiv
|   +-- wotm.json           Aktuelles WotM
|   +-- newsletter_history.json  Newsletter-Verlauf
+-- api/                    Vercel Serverless Functions
|   +-- admin_auth.py           Login/Token
|   +-- admin_data.py           Dashboard-Daten
|   +-- admin_articles.py       Artikel verwalten
|   +-- admin_topics.py         Themen-Queue verwalten
|   +-- admin_publish.py        Cron: Artikel veroeffentlichen
|   +-- admin_wotm.py           WotM + Newsletter
|   +-- admin_debug.py          Debug-Endpoint
|   +-- generate_article.py     KI-Artikelgenerierung
|   +-- subscribe.py            Newsletter-Anmeldung
+-- site-v2/                Gebaute Website (von Vercel deployed)
|   +-- admin/index.html    Admin-Dashboard
|   +-- artikel/            Artikel-HTML-Seiten
|   +-- kategorie/          Kategorie-Seiten
|   +-- images/             Bilder
|   +-- style.css           Globales Stylesheet
+-- .github/workflows/
|   +-- build.yml           Auto-Rebuild bei Artikel-Aenderungen (aktiv)
|   +-- auto-generate.yml   Notfall-Backup fuer Artikel-Generierung (nur manuell, kein Zeitplan)
|   +-- pylint.yml          Code-Qualitaetspruefung bei Python-Aenderungen
+-- main.py                 CLI-Hauptskript
+-- content_generator.py    GPT-4o Artikel-Generator
+-- site_builder_v2.py      Statischer Site-Builder
+-- notifier.py             E-Mail-Benachrichtigungen
+-- newsletter_generator.py Newsletter-Template-Generator
+-- wotm_generator.py       WotM-Generator
+-- image_fetcher.py        Unsplash-Bilder
+-- map_data_builder.py     Kartendaten-Builder
+-- topic_library.py        70+ Themen-Vorlagen
+-- config.json             Konfiguration (NICHT in Git)
+-- .env                    Brevo API Key (NICHT in Git)
+-- vercel.json             Vercel-Konfiguration
+-- requirements.txt        Python-Abhaengigkeiten
```

---

## 9. Checklisten

### Woechentlich (ca. 10 Minuten)

- [ ] Dashboard oeffnen: https://www.whisky-reise.com/admin/
- [ ] **Artikel-Tab**: Neue Entwuerfe pruefen
  - Titel und Teaser lesen -- passen sie?
  - Bei Bedarf bearbeiten (Titel, Teaser, Inhalt)
  - Freigeben oder ablehnen
- [ ] **Themen-Tab**: Pruefen ob genuegend Themen in der Queue sind (mind. 4-6 offene)
- [ ] Optional: Brevo Dashboard pruefen (Abonnenten, Bounce-Rate)

### Monatlich (ca. 30-45 Minuten)

- [ ] **Whisky des Monats** erstellen:
  1. Dashboard -> WotM & Newsletter Tab
  2. Neuen Monat waehlen
  3. Whisky-Daten eintragen
  4. Fotos hochladen (optional)
  5. Newsletter generieren
  6. Vorschau pruefen
  7. Newsletter senden
- [ ] Google Search Console pruefen (Indexierung, Fehler)
- [ ] Affiliate-Einnahmen pruefen (Amazon PartnerNet)
- [ ] Produktpreise in `data/products.json` aktualisieren (bei grossen Abweichungen)

### Quartalsweis (ca. 30 Minuten)

- [ ] **GitHub Token** pruefen -- laeuft er bald ab? -> Erneuern (siehe 6.2)
- [ ] **API-Keys** pruefen -- alle noch gueltig?
- [ ] Datenschutzerklaerung aktualisieren falls noetig (neue Partner, Tracker)
- [ ] Content-Strategie ueberpruefen: Welche Artikel performen gut? Welche Themen fehlen?
- [ ] Neue Themen in die Queue eintragen (Dashboard -> Themen -> Neues Thema)
- [ ] Defekte Links pruefen (z.B. mit einem Online Dead Link Checker)
- [ ] **SEO-Grundcheck**: `curl -s https://www.whisky-reise.com/sitemap.xml | grep -c "<url>"` -- Anzahl sollte den tatsaechlichen Artikel+Kategorie+Kern-Seiten entsprechen, keine Legal-Seiten enthalten. Ausserdem: Google Search Console -> Abdeckung -> auf "Ausgeschlossen" pruefen, ob noindex-Seiten (impressum, datenschutz, suche) korrekt herausgefiltert sind.

---

## 10. Schnellreferenz

### CLI-Befehle

```bash
cd "C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin"

python main.py                  # Interaktives Menue
python main.py --auto -n 2      # 2 Artikel generieren + pushen
python main.py --build-v2       # Website bauen + deployen
python main.py --serve-v2       # Lokaler Webserver (Port 8000)
python main.py --generate -n 1  # Nur 1 Artikel generieren (ohne Build)
python main.py --test           # OpenAI API Verbindung testen
python main.py --stats          # Statistiken anzeigen
```

### Wichtige Dateien

| Datei | Zweck | Wann anfassen |
|-------|-------|--------------|
| `config.json` | API-Keys, URLs | Bei Key-Erneuerung oder Domain-Wechsel |
| `data/products.json` | Amazon-Produkte | Neue Produkte hinzufuegen |
| `data/manual-locations.json` | Karteneintraege | Neue Destillerien/POIs |
| `articles/*.json` | Artikel-Inhalte | Artikel manuell bearbeiten |
| `site_builder_v2.py` | Website-Generator | Bei Design/Layout-Aenderungen |
| `vercel.json` | Vercel-Config | Bei Deployment-Aenderungen |

---

## 11. Rechtliches (DSGVO / TMG)

### Pflichtseiten (alle vorhanden)

- **Impressum** (`/impressum.html`) -- Pflicht nach TMG Paragraph 5
- **Datenschutzerklaerung** (`/datenschutz.html`) -- Pflicht nach DSGVO
- **Cookie-Consent-Banner** -- Erscheint bei erstem Besuch

### Bei Aenderungen beachten

| Aenderung | Datenschutzerklaerung aktualisieren? | Impressum aktualisieren? |
|-----------|-------------------------------------|-------------------------|
| Neuer Affiliate-Partner | Ja | Nein |
| Neues Analytics-Tool | Ja + Cookie-Banner | Nein |
| Neuer Newsletter-Anbieter | Ja | Nein |
| Umzug / neue Adresse | Nein | Ja |
| Neuer Hoster | Ja | Nein |

### Newsletter (Double Opt-In)

Der Newsletter nutzt DSGVO-konformes Double Opt-In:
1. Nutzer traegt E-Mail auf der Website ein
2. Brevo sendet Bestaetigungs-E-Mail (Template ID 1)
3. Erst nach Klick auf Bestaetigungslink wird der Kontakt aktiv
4. Abmeldelink in jeder Newsletter-E-Mail (automatisch von Brevo)
