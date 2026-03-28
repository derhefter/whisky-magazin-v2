# Whisky Magazin — Bedienungsanleitung

**Version 2.0 | Stand: März 2026**

---

## Inhalt

1. [Systemübersicht](#1-systemübersicht)
2. [Schnellstart (5 Minuten)](#2-schnellstart-5-minuten)
3. [Website-Versionen (V1 Classic vs. V2 Notebook)](#3-website-versionen-v1-classic-vs-v2-notebook)
4. [Artikel generieren](#4-artikel-generieren)
5. [Whisky des Monats verwalten](#5-whisky-des-monats-verwalten)
6. [Newsletter-System](#6-newsletter-system)
7. [Mailchimp einrichten](#7-mailchimp-einrichten)
8. [E-Mail-Benachrichtigungen einrichten](#8-e-mail-benachrichtigungen-einrichten)
9. [Automatischer Zeitplaner](#9-automatischer-zeitplaner)
10. [GitHub & Vercel Deployment](#10-github--vercel-deployment)
11. [Karten-Seite verwalten](#11-karten-seite-verwalten)
12. [Fotos & Bilder](#12-fotos--bilder)
13. [Affiliate-Links konfigurieren](#13-affiliate-links-konfigurieren)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Systemübersicht

Das Whisky Magazin ist ein vollautomatischer Blog-Generator für Schottland-Reisen und Whisky-Themen. Kein WordPress, kein CMS, kein Server erforderlich — alles läuft lokal und wird als statisches HTML bereitgestellt.

### Was das System kann

| Funktion | Beschreibung |
|---|---|
| Artikel-Generator | GPT-4o erstellt SEO-optimierte Artikel aus einer Themenbibliothek |
| Website-Build | Zwei unabhängige Design-Versionen (V1 Classic, V2 Notebook) |
| Newsletter | Monatlicher Newsletter mit Mailchimp-Integration |
| Whisky des Monats | Eigener Redaktions-Workflow mit E-Mail-Freigabe |
| Karte | Leaflet.js-Karte mit 110 Destillerien und 201 Orten |
| Affiliate | Amazon + Tradedoubler automatisch in jeden Artikel |
| Deployment | Automatisch via GitHub → Vercel |

### Aktueller Stand (März 2026)

- 36 Artikel (Schottland-Reisen 2007–2024, Bourbon Trail 2024)
- Autoren: Steffen & Elmar
- 5 Kategorien: Whisky, Reise, Natur, Lifestyle, Urlaub
- 110 Destillerien auf der Karte, davon 88 persönlich besucht
- 201 Orte in der Kartendatenbank
- 73+ vorbereitete Artikel-Themen

### Verzeichnisstruktur

```
whisky-magazin/
│
├── articles/                    ← JSON-Quelldateien aller Artikel
│
├── data/
│   └── manual-locations.json    ← Manuell gepflegte Orte (GPS, Typ, Region)
│
├── site/                        ← V1 Classic (gebaut von site_builder.py)
│   ├── artikel/                 ← Artikel-HTML-Dateien
│   ├── kategorie/               ← Kategorie-Seiten
│   ├── data/map-data.json       ← Kartendaten (201 Orte)
│   ├── images/                  ← Titelbilder
│   ├── index.html               ← Startseite
│   ├── karte.html               ← Interaktive Karte
│   └── sitemap.xml
│
├── site-v2/                     ← V2 Notebook (gebaut von site_builder_v2.py)
│   └── [gleiche Struktur wie site/]
│
├── design-concepts/             ← HTML-Mockups (Golden Hour, Salt & Stone, Notebook)
│
├── scotland-archive/            ← Originalfotos aus 18 Jahren Schottland-Reisen
│   └── cartoon-source/
│       └── canva-upload/        ← 15 optimierte JPGs für Canva Pro
│
├── main.py                      ← Hauptmenü + CLI
├── site_builder.py              ← V1-Generator
├── site_builder_v2.py           ← V2-Generator
├── content_generator.py         ← GPT-4o Artikel-Generator
├── image_fetcher.py             ← Unsplash API
├── map_data_builder.py          ← Kartendaten-Builder
├── wotm_generator.py            ← Whisky des Monats Generator
├── newsletter_generator.py      ← Newsletter-System
├── mailchimp_setup.py           ← Mailchimp Einrichtungs-Assistent
├── schedule_setup.py            ← Zeitplaner-Einrichtung
├── topic_library.py             ← 73+ vorbereitete Themen
├── used_topics.json             ← Duplikat-Schutz
│
├── config.json                  ← API-Keys + Einstellungen (NICHT in Git!)
├── config.example.json          ← Vorlage ohne echte Keys
├── starten.bat                  ← Windows-Startdatei
├── setup.bat                    ← Einmalige Installation
└── ANLEITUNG.md                 ← Diese Datei
```

---

## 2. Schnellstart (5 Minuten)

### Schritt 1: Python installieren (einmalig)

Python 3.9 oder höher von https://www.python.org/downloads/ herunterladen und installieren.

Wichtig: Beim Installer "Add Python to PATH" anhaken.

### Schritt 2: Abhängigkeiten installieren (einmalig)

```
setup.bat doppelklicken
```

Das installiert alle Python-Pakete aus `requirements.txt` in eine virtuelle Umgebung (`venv/`).

### Schritt 3: API-Keys eintragen (einmalig)

1. `config.example.json` kopieren → als `config.json` speichern
2. Eigene Keys eintragen:

```json
{
  "openai": {
    "api_key": "sk-...",
    "model": "gpt-4o"
  },
  "unsplash": {
    "api_key": "..."
  },
  "site": {
    "name": "Whisky Magazin",
    "author": "Steffen",
    "base_url": "https://whisky-magazin.vercel.app"
  }
}
```

> `config.json` niemals in Git committen — sie ist bereits in `.gitignore`.

### Schritt 4: Verbindung testen

```
starten.bat doppelklicken → Option [1]
```

Erwartete Ausgabe: `OpenAI OK! Antwort: Slainte Mhath! ...`

### Schritt 5: Ersten Artikel generieren und Website ansehen

```
starten.bat → [2] → [9] → [10]
```

Das generiert einen Artikel, baut V2 neu und öffnet http://localhost:8082 im Browser.

---

## 3. Website-Versionen (V1 Classic vs. V2 Notebook)

Beide Versionen enthalten identischen Inhalt (gleiche Artikel, gleiche Karte), unterscheiden sich aber vollständig im Design.

### V1 — Whisky Magazin Classic

| Eigenschaft | Wert |
|---|---|
| Ordner | `site/` |
| Design | Warm Amber / Braun, Georgia-Schrift |
| Stil | Klassisches Magazin-Layout |
| Generator | `site_builder.py` |
| Menü Build | `[4]` |
| Menü Vorschau | `[5]` |
| Lokale URL | http://localhost:8080 |
| Vercel URL | https://whisky-magazin.vercel.app |
| GitHub Repo | derhefter/whisky-magazin |

### V2 — Whisky Magazin Notebook

| Eigenschaft | Wert |
|---|---|
| Ordner | `site-v2/` |
| Design | Notebook-Style, Creme / Kupfer-Töne |
| Schriften | Bitter (Überschriften) + Work Sans (Text) |
| Generator | `site_builder_v2.py` |
| Menü Build | `[9]` |
| Menü Vorschau | `[10]` |
| Lokale URL | http://localhost:8082 |
| Vercel URL | https://whisky-magazin-v2.vercel.app |
| GitHub Repo | derhefter/whisky-magazin-v2 |

> V2 ist die aktuell bevorzugte Version für Weiterentwicklung.

### Normaler Workflow (empfohlen: V2)

```
1. starten.bat doppelklicken
2. [2]  → Neuen Artikel generieren (~2 Minuten)
3. [9]  → V2 Website neu bauen (~10 Sekunden)
4. [10] → V2 im Browser anzeigen (http://localhost:8082)
```

### Design anpassen

Das gesamte CSS liegt inline in den Builder-Skripten, jeweils in der Funktion `_base_template()`:

- V1: `site_builder.py` → Funktion `_base_template()` → CSS unter `:root`
- V2: `site_builder_v2.py` → Funktion `_base_template()` → CSS unter `:root`

Farbvariablen (Beispiel V2):

```css
:root {
  --cream: #faf6ef;
  --copper: #b87333;
  --ink: #2c2416;
  --warm-gray: #8b7d6b;
}
```

---

## 4. Artikel generieren

### Automatisch mit GPT-4o

```
starten.bat → [2] (einen Artikel) oder [3] (drei Artikel)
```

Das System:
1. Wählt ein noch nicht verwendetes Thema aus `topic_library.py`
2. Generiert einen Artikel mit GPT-4o (1.200–2.500 Wörter)
3. Holt ein passendes Titelbild von Unsplash
4. Speichert alles als JSON in `articles/`
5. Markiert das Thema in `used_topics.json` als verwendet

Dauer: ca. 2 Minuten pro Artikel.

### Manuell: Eigene Reiseberichte anlegen

Neue JSON-Datei in `articles/` erstellen. Dateiname-Schema: `YYYY-MM-DD_thema-slug.json`

Beispiel: `2024-08-15_glenlivet-besuch-speyside.json`

```json
{
  "title": "Titel des Artikels",
  "date": "2024-08-15",
  "date_display": "15. August 2024",
  "slug": "glenlivet-besuch-speyside",
  "category": "Reise",
  "tags": ["Schottland", "Speyside", "Destillerie"],
  "author": "Steffen",
  "teaser": "Kurzer Vorschautext für die Startseite (2-3 Sätze).",
  "meta_description": "SEO-Beschreibung, max. 160 Zeichen.",
  "content_html": "<h2>Überschrift</h2><p>Artikeltext als HTML...</p>",
  "image_url": "",
  "locations": ["The Glenlivet"]
}
```

### Pflichtfelder

| Feld | Beschreibung |
|---|---|
| `title` | Artikelüberschrift |
| `date` | ISO-Datum YYYY-MM-DD — bestimmt die Sortierung |
| `slug` | URL-freundlicher Name (nur Kleinbuchstaben, Bindestriche) |
| `category` | Eine von: Whisky, Reise, Natur, Lifestyle, Urlaub |
| `content_html` | Artikelinhalt als HTML |
| `author` | Steffen oder Elmar |

### Optionale Felder

| Feld | Beschreibung |
|---|---|
| `image_url` | Eigenes Titelbild (URL oder relativer Pfad). Leer = Unsplash automatisch |
| `locations` | Array mit Orts-/Destillerienamen für Karten-Verknüpfung |
| `tags` | Schlagwörter für Kategorieseiten |

### Themen-Bibliothek erweitern

Neue Themen in `topic_library.py` zur Liste `WHISKY_TOPICS` hinzufügen:

```python
{
    "title": "Tobermory — Die Destillerie auf der Insel Mull",
    "category": "Whisky",
    "tags": ["Schottland", "Islands", "Destillerie"],
    "type": "article"
}
```

### Alle Themen aufgebraucht

`used_topics.json` löschen — alle 73+ Themen sind sofort wieder verfügbar.

### Artikel bearbeiten

1. Gewünschte JSON-Datei in `articles/` mit einem Texteditor öffnen
2. Felder bearbeiten (HTML-Inhalt im Feld `content_html`)
3. Speichern
4. Website neu bauen: `[9]` (V2) oder `[4]` (V1)

### Artikel löschen

JSON-Datei aus `articles/` löschen, dann Website neu bauen.

---

## 5. Whisky des Monats verwalten

Der "Whisky des Monats" (WOTM) ist ein monatliches Redaktions-Feature: Ein ausgewählter Whisky wird prominent auf der Website hervorgehoben und bildet die Grundlage für den monatlichen Newsletter.

### Workflow

```
1. Du wählst den Whisky des Monats aus
2. System generiert automatisch einen ausführlichen Artikel
3. Du erhältst eine E-Mail mit dem Entwurf zur Prüfung
4. Du gibst frei
5. Der Artikel erscheint auf der Website und im Newsletter
```

### Per Menü (empfohlen)

```
starten.bat → [11]
```

Das Menü fragt: `Whisky-Name (z.B. 'Lagavulin 16'):`

Nach der Eingabe generiert das System automatisch:
- Einen detaillierten WOTM-Artikel (Tasting-Notizen, Geschichte, Paarungen)
- Ein Titelbild über Unsplash
- Eine E-Mail-Benachrichtigung an rosenhefter@gmail.com

### Per Kommandozeile

```bash
python wotm_generator.py --new "Lagavulin 16"
python wotm_generator.py --new "Glenfarclas 15"
python wotm_generator.py --new "Highland Park 18"
```

### WOTM genehmigen

Nach der Prüfung per E-Mail:

```bash
python wotm_generator.py --approve
```

### WOTM-Archiv anzeigen

```bash
python wotm_generator.py --list
```

### Tipps für gute WOTM-Einträge

- Vollständigen Namen mit Alter angeben: "Lagavulin 16" statt "Lagavulin"
- Für Sonderabfüllungen: "Glenfarclas Family Casks 1994"
- Für American Whiskey: "Buffalo Trace Bourbon" oder "Woodford Reserve Double Oaked"

---

## 6. Newsletter-System

Der Newsletter erscheint monatlich und enthält den Whisky des Monats, neue Artikel und redaktionelle Empfehlungen. Der Versand läuft über Mailchimp.

### Vollständiger Workflow Schritt für Schritt

```
Schritt 1: Am 1. des Monats
   System sendet automatisch Erinnerung an rosenhefter@gmail.com:
   "Zeit für den Whisky des Monats!"

Schritt 2: Whisky des Monats festlegen
   starten.bat → [11]
   ODER: python wotm_generator.py --new "Whisky Name"

Schritt 3: Entwurf prüfen
   Du erhältst eine E-Mail mit dem generierten WOTM-Artikel.
   Prüfe Tasting-Notizen, Geschichte, Paarungsempfehlungen.

Schritt 4: WOTM freigeben
   python wotm_generator.py --approve

Schritt 5: Newsletter-Entwurf erstellen
   starten.bat → [12]
   ODER: python newsletter_generator.py --draft
   System baut den Newsletter automatisch aus dem WOTM + neuen Artikeln.

Schritt 6: Newsletter-Vorschau prüfen
   starten.bat → [13]
   ODER: python newsletter_generator.py --preview
   Du erhältst eine E-Mail mit dem Newsletter-Entwurf + Vorschau-Link.

Schritt 7: Newsletter freigeben
   Im Menü [13] nach der Vorschau: "Freigeben? (j/n)" → j
   ODER direkt: python newsletter_generator.py --approve

Schritt 8: Newsletter versenden
   starten.bat → [14]
   ODER: python newsletter_generator.py --send
   Das Menü fragt zur Sicherheit: "Wirklich senden? (j/n)"
```

### Menü-Kurzreferenz

| Option | Funktion | Kommandozeile |
|---|---|---|
| `[11]` | Whisky des Monats erstellen | `python wotm_generator.py --new "Name"` |
| `[12]` | Newsletter Entwurf erstellen | `python newsletter_generator.py --draft` |
| `[13]` | Vorschau + Freigabe | `python newsletter_generator.py --preview` |
| `[14]` | Newsletter versenden | `python newsletter_generator.py --send` |

### Newsletter-Inhalt

Ein typischer Newsletter enthält:

1. Persönliche Begrüßung
2. Whisky des Monats (ausführlich mit Bild)
3. Neue Artikel seit letztem Newsletter (3–5 Artikel)
4. Reise-Tipp des Monats
5. Affiliate-Links (Amazon, Tradedoubler)
6. Abmelde-Link (Pflicht nach DSGVO)

### Newsletter-Vorlage anpassen

Die Newsletter-HTML-Vorlage liegt in `newsletter_generator.py` in der Funktion `_build_template()`. Das Design orientiert sich am Notebook-Konzept (V2).

### DSGVO-Hinweis

- Abonnenten müssen aktiv zugestimmt haben (Double Opt-In über Mailchimp)
- Jeder Newsletter enthält automatisch einen Abmelde-Link
- Die E-Mail-Adressen der Abonnenten werden ausschließlich bei Mailchimp gespeichert

---

## 7. Mailchimp einrichten

Mailchimp ist der E-Mail-Versand-Dienst für den Newsletter. Das kostenlose Konto reicht für bis zu 500 Abonnenten und 1.000 E-Mails/Monat.

### Ersteinrichtung

```
starten.bat → [15]
ODER: python mailchimp_setup.py
```

Der interaktive Assistent führt durch alle Schritte.

### Manuell einrichten

**Schritt 1: Mailchimp-Konto erstellen**

https://mailchimp.com → "Sign Up Free"

**Schritt 2: API-Key erstellen**

1. Mailchimp → Account → Extras → API Keys
2. "Create A Key" klicken
3. Key kopieren

**Schritt 3: Audience (Liste) erstellen**

1. Mailchimp → Audience → Create Audience
2. Name: "Whisky Magazin Leser"
3. From email: rosenhefter@gmail.com
4. Audience ID notieren (unter Audience → Settings → Audience name and campaign defaults)

**Schritt 4: Signup-Formular einbinden**

Mailchimp → Audience → Signup forms → Embedded forms → Code kopieren und in die Website einfügen.

**Schritt 5: Keys in config.json eintragen**

```json
{
  "mailchimp": {
    "api_key": "abc123def456...-us1",
    "server_prefix": "us1",
    "audience_id": "abc123def"
  }
}
```

Der Server-Präfix (`us1`, `us14`, etc.) steht am Ende des API-Keys nach dem Bindestrich.

### Mailchimp API-Key-Format

```
xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx-us14
                                 ^^^^
                                 server_prefix
```

### Testmail senden

Nach der Einrichtung eine Testmail an sich selbst senden:

```bash
python newsletter_generator.py --test-send rosenhefter@gmail.com
```

---

## 8. E-Mail-Benachrichtigungen einrichten

Das System sendet automatische E-Mails an rosenhefter@gmail.com für:

- Monatliche Erinnerung: "Zeit für den Whisky des Monats"
- WOTM-Entwurf zur Prüfung
- Newsletter-Entwurf zur Freigabe

### Einrichtung mit Gmail

**Option A: Gmail App-Passwort (empfohlen)**

1. Google-Konto → Sicherheit → 2-Faktor-Authentifizierung aktivieren
2. Google-Konto → Sicherheit → App-Passwörter → "Mail" + "Windows-Computer"
3. Das generierte 16-stellige Passwort notieren

In `config.json`:

```json
{
  "email": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "rosenhefter@gmail.com",
    "password": "xxxx xxxx xxxx xxxx",
    "from": "rosenhefter@gmail.com",
    "to": "rosenhefter@gmail.com"
  }
}
```

**Option B: Gmail SMTP direkt (nur wenn 2FA deaktiviert)**

Gleiche Einstellungen, aber mit dem normalen Gmail-Passwort. Weniger sicher, funktioniert aber.

### SMTP-Referenz

| Anbieter | Host | Port | Verschlüsselung |
|---|---|---|---|
| Gmail | smtp.gmail.com | 587 | STARTTLS |
| Outlook | smtp-mail.outlook.com | 587 | STARTTLS |
| GMX | mail.gmx.net | 587 | STARTTLS |
| Strato | smtp.strato.de | 465 | SSL |

### E-Mail-Benachrichtigungen testen

```bash
python newsletter_generator.py --test-email
```

---

## 9. Automatischer Zeitplaner

Der Zeitplaner automatisiert den monatlichen Redaktions-Workflow: Am 1. jedes Monats sendet das System automatisch eine Erinnerung und bereitet den WOTM-Workflow vor.

### Einrichtung

```
starten.bat → [16]
ODER: python schedule_setup.py
```

Der Assistent richtet einen Windows-Taskplaner-Eintrag ein.

### Was der Zeitplaner automatisiert

| Zeitpunkt | Aktion |
|---|---|
| 1. des Monats, 09:00 Uhr | E-Mail-Erinnerung: "Zeit für den Whisky des Monats" |
| Nach WOTM-Freigabe | Newsletter-Entwurf automatisch generieren |
| Wöchentlich (optional) | Neuen Artikel generieren + Website bauen |

### Manuell mit Windows-Taskplaner einrichten

Falls `schedule_setup.py` nicht verfügbar:

1. Windows-Suche: "Aufgabenplanung"
2. "Einfache Aufgabe erstellen"
3. Name: "Whisky Magazin Newsletter-Erinnerung"
4. Trigger: Monatlich, am 1., um 09:00
5. Aktion: Programm starten
6. Programm: `C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin\venv\Scripts\python.exe`
7. Argumente: `newsletter_generator.py --remind`
8. Startordner: `C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin`

### Zeitplaner prüfen

```bash
python schedule_setup.py --status
```

---

## 10. GitHub & Vercel Deployment

Die Website wird automatisch über GitHub und Vercel veröffentlicht. Jedes Mal, wenn du die Website baust und nach GitHub pushst, aktualisiert Vercel automatisch die öffentliche URL.

### Übersicht

| Version | GitHub Repo | Vercel URL |
|---|---|---|
| V1 Classic | derhefter/whisky-magazin | https://whisky-magazin.vercel.app |
| V2 Notebook | derhefter/whisky-magazin-v2 | https://whisky-magazin-v2.vercel.app |

### Deployment-Workflow (V2 Notebook)

```
1. python main.py → [9]  (Website V2 bauen)
2. git add site-v2/
3. git commit -m "Website Update März 2026"
4. git push
   → Vercel erkennt den Push automatisch
   → In ca. 30 Sekunden ist die neue Version live
```

Oder als Einzeiler:

```bash
python main.py --build-v2 && git add site-v2/ && git commit -m "Update" && git push
```

### Vercel für V2 einrichten (einmalig)

**Schritt 1: GitHub-Repository erstellen**

```bash
cd C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin
git remote add v2 https://github.com/derhefter/whisky-magazin-v2.git
```

**Schritt 2: Vercel-Projekt erstellen**

1. https://vercel.com → Login mit GitHub
2. "New Project" klicken
3. "Import Git Repository" → `derhefter/whisky-magazin-v2` auswählen
4. Framework Preset: **Other**
5. Root Directory: `.` (Punkt — also das Root des Repos)
6. Output Directory: `site-v2`
7. "Deploy" klicken

**Schritt 3: Ersten Push durchführen**

```bash
git push v2 main
```

Vercel deployt automatisch. Die URL erscheint im Vercel-Dashboard.

**Schritt 4: Custom Domain verbinden (optional)**

Im Vercel-Dashboard → Projekt → Settings → Domains:

- `whisky-magazin.de` hinzufügen
- DNS-Einträge beim Domain-Anbieter setzen (Vercel zeigt die genauen Werte)

### Automatisches Deployment nach jedem Build

Nach jedem `python main.py --build-v2` oder Menü-Option `[9]`:

V2 wird in `site-v2/` geschrieben. Ein einmaliger Git-Push genügt, damit Vercel automatisch deployt.

Für vollautomatisches Deployment (inkl. Git Push) in `site_builder_v2.py` die Funktion `auto_push()` aktivieren — Details im Kommentar am Ende der Datei.

### Voraussetzungen für GitHub

Git muss installiert und konfiguriert sein:

```bash
git config --global user.name "Steffen Hefter"
git config --global user.email "rosenhefter@gmail.com"
```

### .gitignore prüfen

Folgende Einträge sollten in `.gitignore` stehen:

```
config.json
venv/
__pycache__/
*.pyc
magazin.log
```

---

## 11. Karten-Seite verwalten

Die Karte ist eine Leaflet.js-Seite (`karte.html`) mit 201 eingetragenen Orten: Destillerien, Sehenswürdigkeiten und GPS-Stops aus 18 Jahren Schottland-Reisen.

### Was die Karte zeigt

- Destillerien (110 eingetragen, 88 persönlich besucht)
- Sehenswürdigkeiten / Points of Interest
- Filter nach Jahr, Region, Land
- Toggle: Destillerien / Sehenswürdigkeiten
- Popup pro Ort: Fotos, Besuchsjahre, Links zu Artikeln

Bewusste Entscheidung: Keine Hotels, keine Restaurants auf der Karte.

### Wie die Kartendaten entstehen

`map_data_builder.py` liest:
1. `data/manual-locations.json` — alle Orte mit GPS-Koordinaten
2. Alle Artikel-JSONs — für Artikel-Verlinkung und Besuchsjahre

Das Ergebnis wird in `site/data/map-data.json` und `site-v2/data/map-data.json` geschrieben. Dieser Prozess läuft **automatisch** beim Website-Build.

### Neue Destillerie hinzufügen

1. `data/manual-locations.json` öffnen
2. Eintrag hinzufügen:

```json
{
  "name": "Ardnamurchan Distillery",
  "lat": 56.7234,
  "lon": -6.1456,
  "type": "distillery",
  "region": "Highlands",
  "country": "Scotland",
  "visited": true,
  "visit_years": [2023]
}
```

3. Website neu bauen — die Destillerie erscheint sofort auf der Karte.

### Typen für Locations

| Typ | Beschreibung | Karten-Symbol |
|---|---|---|
| `distillery` | Whisky-Destillerie | Whisky-Flasche |
| `poi` | Sehenswürdigkeit / Point of Interest | Marker |

### Destillerie mit Artikel verknüpfen

Im Artikel-JSON das Feld `locations` setzen:

```json
"locations": ["Ardnamurchan Distillery"]
```

Der Name muss **exakt** mit dem `name`-Feld in `manual-locations.json` übereinstimmen — inklusive Groß-/Kleinschreibung.

### Besuchsjahre nachtragen

Im Eintrag in `manual-locations.json`:

```json
"visited": true,
"visit_years": [2015, 2019, 2023]
```

### GPS-Koordinaten finden

Google Maps → Rechtsklick auf den Ort → "Was ist hier?" → Koordinaten erscheinen unten.

Oder: https://www.latlong.net/

---

## 12. Fotos & Bilder

### Automatische Bilder via Unsplash

Beim Artikel-Generieren holt `image_fetcher.py` automatisch ein passendes Bild:

| Artikel-Typ | Bild-Suche |
|---|---|
| Destillerie-Artikel | Regional passende Landschaft (z.B. "Speyside Scotland whisky") |
| Whisky-Tasting / Bewertung | Whisky-Glas oder Flasche |
| Reise-Artikel | Landschaft des Reiseziels |
| Natur-Artikel | Schottische Landschaft |

Duplikat-Schutz: Jeder Artikel bekommt ein eigenes Bild.

Unsplash Free Plan: 50 Anfragen/Stunde. Das reicht für normalen Betrieb problemlos.

### Eigene Fotos verwenden

Im Artikel-JSON `image_url` manuell setzen:

```json
"image_url": "https://example.com/mein-foto.jpg"
```

Oder ein lokales Bild in `site/images/` ablegen:

```json
"image_url": "../images/glenlivet-2019.jpg"
```

### Scotland Archive

Eigene Originalfotos aus 18 Jahren Schottland-Reisen:

| Ordner | Inhalt |
|---|---|
| `scotland-archive/` | Alle Originalfotos |
| `scotland-archive/cartoon-source/` | 19 ausgewählte Fotos für Canva |
| `scotland-archive/cartoon-source/canva-upload/` | 15 optimierte JPGs (max. 2500px) für Canva Pro |

### Fotos für Canva vorbereiten

Anforderungen für Canva Pro Upload:
- Format: JPG oder PNG
- Maximale Breite: 2500px (größere werden automatisch skaliert)
- Maximale Dateigröße: 25 MB

Fotos mit Windows-Foto-App verkleinern: Rechtsklick → "Größe ändern" → "S" (kleine Größe)

### Urheberrecht bei Destillerie-Fotos

Markenspezifische Flaschenfotos von Distillerie-Websites oder Google-Bildern sind urheberrechtlich geschützt. Für eigene Tasting-Artikel:

1. Eigenes Foto der Flasche machen
2. In `site/images/` ablegen
3. Im Artikel-JSON als `image_url` eintragen

Unsplash-Bilder sind kostenlos für kommerzielle Nutzung (Creative Commons Zero).

---

## 13. Affiliate-Links konfigurieren

Affiliate-Links werden beim Website-Build automatisch durch `site_builder*.py` in jeden Artikel eingebaut.

### Aktive Programme

| Programm | Publisher-ID / Tag | Produktbereich |
|---|---|---|
| Amazon PartnerNet | `whiskyreise74-21` | Whisky, Bücher, Reise-Ausrüstung |
| Tradedoubler | `2205846` | Reisen, Flüge, Hotels |

### Links manuell in Artikel einfügen

Im `content_html` als HTML:

**Amazon:**

```html
<a href="https://www.amazon.de/s?k=lagavulin+16&tag=whiskyreise74-21"
   target="_blank" rel="noopener noreferrer" class="affiliate-link">
   Lagavulin 16 bei Amazon kaufen
</a>
```

**Tradedoubler (Reisen / Flüge):**

```html
<a href="https://clk.tradedoubler.com/click?p=227718&a=2205846"
   target="_blank" rel="noopener noreferrer" class="affiliate-link">
   Schottland-Flüge vergleichen
</a>
```

### Automatic Affiliate Injection

Die Builders suchen nach Keywords im Artikel-Text und fügen automatisch passende Affiliate-Links ein. Diese Logik liegt in `site_builder.py` / `site_builder_v2.py` in der Funktion `_inject_affiliate_links()`.

Eigene Keywords ergänzen:

```python
AFFILIATE_KEYWORDS = {
    "Lagavulin": "https://www.amazon.de/s?k=lagavulin&tag=whiskyreise74-21",
    "Glenfarclas": "https://www.amazon.de/s?k=glenfarclas&tag=whiskyreise74-21",
    ...
}
```

### Steuerlich

Affiliate-Einnahmen sind steuerpflichtig. Ab 256 EUR Jahresgewinn Kleinunternehmerregelung prüfen (§ 19 UStG). Alle Einnahmen in der Steuererklärung (Anlage SO oder Gewerbe) angeben.

### DSGVO / Impressum

Auf der Website muss ein Hinweis auf Affiliate-Links erscheinen. Der Builder fügt automatisch folgenden Disclaimer in die Fußzeile ein: "Diese Website enthält Affiliate-Links. Bei einem Kauf erhalten wir eine kleine Provision ohne Mehrkosten für dich."

---

## 14. Troubleshooting

### Bilder werden nicht angezeigt

**Ursache:** Website wurde direkt als Datei geöffnet (`file://`) statt über einen lokalen Server.

**Lösung:** Immer über `starten.bat → [5]` (V1) oder `[10]` (V2) öffnen. Das startet automatisch einen lokalen Webserver.

---

### Karte zeigt keine Destillerie

**Ursache A:** Feld `locations` im Artikel-JSON fehlt oder stimmt nicht exakt mit `manual-locations.json` überein.

**Lösung:** Exakten Namen aus `manual-locations.json` kopieren und in `"locations": [...]` eintragen, dann neu bauen.

**Ursache B:** Destillerie ist nicht in `data/manual-locations.json` eingetragen.

**Lösung:** Eintrag in `manual-locations.json` hinzufügen, dann Website neu bauen.

---

### Unicode-Fehler in der Windows-Kommandozeile

**Symptom:** Kryptische Zeichen oder Fehlermeldungen bei Umlauten.

**Lösung:** `starten.bat` macht das automatisch (`chcp 65001`). Falls du CMD direkt nutzt:

```
chcp 65001
```

---

### OpenAI-Fehler: "insufficient_quota"

**Lösung:** Guthaben aufladen unter https://platform.openai.com/settings/organization/billing

Empfehlung: 10 EUR aufladen — reicht für ca. 50–100 Artikel.

---

### OpenAI-Fehler: "model_not_found"

**Ursache:** Das Modell `gpt-4o` steht nicht zur Verfügung (zu neues Konto ohne Zahlungsmethode).

**Lösung:** In `config.json` auf `"gpt-3.5-turbo"` wechseln — günstiger, aber Artikel-Qualität etwas geringer.

---

### Unsplash liefert kein Bild

**Ursache:** API-Key fehlt oder Rate-Limit erreicht (50 Anfragen/Stunde im Free Plan).

**Lösung:** `image_url` im Artikel-JSON manuell auf ein eigenes Bild setzen. Oder nächste Stunde warten.

---

### Mailchimp-Fehler: "API Key Invalid"

**Lösung:**
1. API-Key in `config.json` prüfen — muss das Format `xxx...xxx-us14` haben
2. Server-Präfix muss stimmen: letzter Teil des Keys nach dem Bindestrich
3. Neuen Key unter Mailchimp → Account → Extras → API Keys erstellen

---

### Newsletter wird nicht gesendet

**Mögliche Ursachen:**

| Problem | Lösung |
|---|---|
| SMTP-Verbindung schlägt fehl | Gmail App-Passwort prüfen, 2FA aktiviert? |
| Mailchimp-Key falsch | Neuen Key generieren |
| Keine Abonnenten | Test-Abonnent manuell in Mailchimp hinzufügen |
| Newsletter nicht freigegeben | `python newsletter_generator.py --approve` ausführen |

---

### Website-Build schlägt fehl

**Symptom:** Fehlermeldung beim Bauen der Website.

**Häufige Ursachen:**

1. **articles/-Ordner leer:** Mindestens einen Artikel erstellen
2. **JSON-Syntax-Fehler:** Einen Artikel in einem JSON-Validator prüfen (https://jsonlint.com)
3. **Fehlende Abhängigkeiten:** `setup.bat` erneut ausführen

---

### Vercel zeigt alte Version

**Lösung:**
1. Vercel-Dashboard → Projekt → Deployments prüfen
2. Falls Deployment fehlgeschlagen: Logs ansehen
3. Manuell: `git push` nochmals ausführen
4. Im Vercel-Dashboard: "Redeploy" klicken

---

### Git-Fehler: "Permission denied"

**Ursache:** SSH-Key nicht eingerichtet oder HTTPS-Authentifizierung schlägt fehl.

**Lösung mit HTTPS und Token:**

1. GitHub → Settings → Developer settings → Personal access tokens → "Generate new token"
2. Scope: `repo` anhaken
3. Token kopieren
4. Bei `git push` nach Passwort gefragt: Token eingeben (nicht das GitHub-Passwort)

---

### Alle Themen aufgebraucht

**Lösung:** `used_topics.json` löschen — alle 73+ Themen sind sofort wieder verfügbar.

Oder neue Themen in `topic_library.py` ergänzen.

---

## Anhang: Konfigurationsreferenz

### config.json — Vollständiges Schema

```json
{
  "openai": {
    "api_key": "sk-...",
    "model": "gpt-4o",
    "temperature": 0.7,
    "min_word_count": 1200,
    "max_word_count": 2500
  },
  "unsplash": {
    "api_key": "..."
  },
  "site": {
    "name": "Whisky Magazin",
    "author": "Steffen",
    "base_url": "https://whisky-magazin.vercel.app"
  },
  "mailchimp": {
    "api_key": "xxx-us1",
    "server_prefix": "us1",
    "audience_id": "abc123"
  },
  "email": {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "rosenhefter@gmail.com",
    "password": "app-passwort-hier",
    "from": "rosenhefter@gmail.com",
    "to": "rosenhefter@gmail.com"
  }
}
```

### Menü-Referenz

| Option | Funktion | CLI-Äquivalent |
|---|---|---|
| `[1]` | Verbindung testen | `python main.py --test` |
| `[2]` | Einen Artikel generieren | `python main.py --generate` |
| `[3]` | Drei Artikel generieren | `python main.py --generate -n 3` |
| `[4]` | Website V1 bauen | `python main.py --build` |
| `[5]` | Website V1 anzeigen | `python main.py --serve` |
| `[9]` | Website V2 bauen | `python main.py --build-v2` |
| `[10]` | Website V2 anzeigen | `python main.py --serve-v2` |
| `[11]` | Whisky des Monats erstellen | `python wotm_generator.py --new "Name"` |
| `[12]` | Newsletter Entwurf erstellen | `python newsletter_generator.py --draft` |
| `[13]` | Newsletter Vorschau + Freigabe | `python newsletter_generator.py --preview` |
| `[14]` | Newsletter versenden | `python newsletter_generator.py --send` |
| `[15]` | Mailchimp einrichten | `python mailchimp_setup.py` |
| `[16]` | Zeitplaner einrichten | `python schedule_setup.py` |
| `[7]` | Statistiken | `python main.py --stats` |
| `[0]` | Beenden | — |

### Kosten-Übersicht

| Posten | Kosten |
|---|---|
| OpenAI API (ca. 12 Artikel/Monat) | ca. 1–2 EUR/Monat |
| Unsplash API | kostenlos (50 Anfragen/Stunde) |
| Mailchimp (bis 500 Abonnenten) | kostenlos |
| Hosting Vercel | kostenlos |
| GitHub (öffentliches Repo) | kostenlos |
| Eigene Domain (optional) | ca. 10 EUR/Jahr |
| **Gesamt** | **ca. 1–2 EUR/Monat** |

---

## Änderungsprotokoll

| Datum | Änderung |
|---|---|
| 2026-03-27 | Komplett-Rebuild V1 + V2 (36 Artikel, sauber ohne Duplikate) |
| 2026-03-27 | 23 fehlende Destillerien ergänzt (Macallan, Ardbeg, Laphroaig u.a.) → 110 total |
| 2026-03-27 | Karte: Nur Destillerien + Sehenswürdigkeiten sichtbar |
| 2026-03-27 | Famous Grouse Experience: Typ city → poi korrigiert |
| 2026-03-27 | Macallan-Artikel korrekt mit Macallan Distillery verknüpft |
| 2026-03-27 | image_fetcher.py: requests → urllib (venv-kompatibel) |
| 2026-03-27 | starten.bat: zeigt beide Versionen (V1:8080, V2:8082) |
| 2026-03-27 | main.py: Neue Menü-Optionen 11-16 (WOTM, Newsletter, Mailchimp, Zeitplaner) |
| 2026-03-27 | ANLEITUNG.md Version 2.0 — vollständig neu geschrieben |

*Letzte Aktualisierung: 2026-03-27*
