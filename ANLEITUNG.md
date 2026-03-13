# WHISKY MAGAZIN - Komplettanleitung

## Was ist das?

Ein automatisches System, das KI-generierte Blog-Artikel zu den Themen Whisky und Reisen erstellt und daraus eine komplette, fertige Website baut.

Kein WordPress nötig. Kein Server-Wissen nötig. Einfach ausführen.

**Voraussetzungen:**
- Python **3.9 oder höher** ([Download](https://www.python.org/downloads/))
- OpenAI API-Key ([Hier erstellen](https://platform.openai.com/api-keys))

**Was die Website enthält:**

- Professionell gestaltete Startseite mit Artikelübersicht
- SEO-optimierte Einzelartikel (1.200-2.500 Wörter)
- Automatisch eingebaute Affiliate-Links (Amazon, Tradedoubler)
- Kategorie-Seiten (Whisky, Reise, Lifestyle, Natur, Urlaub)
- Sitemap für Google-Indexierung
- 73 vorbereitete Themen für ca. 6 Monate Content

---

## Täglich nutzen

### Neuen Artikel erstellen + Website aktualisieren

`starten.bat -> Option [5] oder [2]`

### Nur Website anschauen

`starten.bat -> Option [6]`

Öffnet die Website im Browser unter http://localhost:8080

### Kommandozeile (für Fortgeschrittene)

```
cd whisky-magazin
venv\Scripts\activate
python main.py --auto -n 3    # 3 Artikel generieren + Website bauen
python main.py --generate -n 5 # 5 Artikel generieren (ohne Website-Build)
python main.py --build         # Website neu bauen (aus vorhandenen Artikeln)
python main.py --stats         # Statistiken anzeigen
python main.py --serve         # Lokalen Webserver starten (localhost:8080)
```

---

## Website online stellen (Hosting)

Die generierte Website liegt im Ordner `site/`. Das sind reine HTML-Dateien, die du überall hosten kannst.

### Option 1: Vercel (EMPFOHLEN - kostenlos)

Vercel ist bereits eingerichtet und verbunden mit diesem Repository.

1. Pushe deine Änderungen nach GitHub (`git push`)
2. Vercel deployed automatisch – fertig!
3. Die Website ist unter [whisky-magazin.vercel.app](https://whisky-magazin.vercel.app) erreichbar
4. Optional: Eigene Domain verbinden unter vercel.com -> Project Settings -> Domains

**Nach jedem neuen Artikel:** Einfach `git add . && git commit -m "Neue Artikel" && git push` – Vercel deployed automatisch.

### Option 2: GitHub Pages (kostenlos)

1. Gehe zu Settings -> Pages -> Source: "Deploy from a branch" -> main
2. Website ist unter `deinname.github.io/whisky-magazin` erreichbar

### Option 3: Eigener Webspace / FTP

Falls du bereits Webspace hast (z.B. bei deinem Domain-Anbieter):

1. Öffne ein FTP-Programm (z.B. FileZilla)
2. Verbinde dich mit deinem Webspace
3. Lade den Inhalt des `site/`-Ordners in das gewünschte Verzeichnis
4. Fertig!

### Option 4: Cloudflare Pages (kostenlos)

1. Gehe zu [https://pages.cloudflare.com](https://pages.cloudflare.com/)
2. "Create a project" -> "Direct Upload"
3. `site/`-Ordner hochladen
4. Eigene Domain verbinden

---

## Automatische Artikel-Generierung (GitHub Actions)

Der Workflow `.github/workflows/auto-generate.yml` generiert jeden **Donnerstag um 11:00 Uhr** automatisch 3 neue Artikel und deployed sie.

**Voraussetzung:** Der OpenAI API-Key muss als GitHub Secret eingerichtet sein:

1. Gehe zu deinem Repository auf GitHub
2. Settings > Secrets and variables > Actions
3. "New repository secret" klicken
4. Name: `OPENAI_API_KEY`
5. Value: Dein OpenAI API-Key (beginnt mit `sk-...`)
6. "Add secret" klicken

**Manuell ausloesen:** Actions > "Auto-Generate Articles (Weekly)" > "Run workflow"

**Wichtig:** Unter Settings > Actions > General muss "Workflow permissions" auf **"Read and write permissions"** stehen, damit der Bot die neuen Artikel committen und pushen kann.

---

## Eigene Domain verbinden

Wenn du eine eigene Domain willst (z.B. whisky-magazin.de):

1. Kaufe eine Domain (z.B. bei namecheap.com, ca. 10 EUR/Jahr)
2. In den DNS-Einstellungen: Verweise sie auf deinen Hosting-Anbieter
3. Bei Vercel geht das besonders einfach über das Dashboard unter Project Settings -> Domains

---

## Einstellungen anpassen (config.json)

| Einstellung | Beschreibung | Standard |
|---|---|---|
| `site.name` | Name der Website | "Whisky Magazin" |
| `site.tagline` | Untertitel | "Dein Guide..." |
| `site.author` | Autorname | "Ellas" |
| `site.base_url` | URL der Website (leer = relativ) | "" |
| `openai.model` | KI-Modell | "gpt-4o" |
| `openai.temperature` | Kreativität (0.0-1.0) | 0.7 |
| `min_word_count` | Mindest-Wörter pro Artikel | 1200 |
| `max_word_count` | Max-Wörter pro Artikel | 2500 |

### base_url einstellen (wichtig für Online-Hosting!)

Wenn die Website online steht, trage die URL ein:

```json
"base_url": "https://whisky-magazin.vercel.app"
```

Oder bei Unterverzeichnis:

```json
"base_url": "https://www.whisky.reise/whisky-magazin"
```

Danach Website neu bauen mit `python main.py --build`.

---

## Kosten-Übersicht

| Posten | Kosten |
|---|---|
| OpenAI API (12 Artikel/Monat) | ca. 1-2 EUR/Monat |
| Hosting (Vercel) | kostenlos |
| Eigene Domain (optional) | ca. 10 EUR/Jahr |
| **Gesamt** | **ca. 1-2 EUR/Monat** |

---

## Erwartete Einnahmen

| Zeitraum | Artikel | Geschätzte Einnahmen |
|---|---|---|
| Monat 1-3 | 36 | 50-150 EUR/Monat |
| Monat 4-6 | 72 | 150-400 EUR/Monat |
| Monat 7-12 | 150+ | 300-1.000 EUR/Monat |

Einnahmequellen:

- **Amazon Affiliate** (Whisky-Verkäufe): 3-7% Provision
- **Tradedoubler** (Reisebuchungen): 2-5% Provision
- **Reiseversicherungen**: Einmalprovisionen
- **Google AdSense** (optional später): 2-5 EUR pro 1.000 Besucher

---

## Dateien im Projekt

```
whisky-magazin/
  setup.bat             <- Installation (einmal ausführen)
  starten.bat           <- Programm starten
  main.py               <- Hauptprogramm
  content_generator.py  <- KI-Artikelgenerierung
  site_builder.py       <- Website-Generator
  topic_library.py      <- 73 Themenvorschläge
  config.example.json   <- Vorlage
  config.json           <- Deine Konfiguration (nicht im Git)
  requirements.txt      <- Python-Pakete
  articles/             <- Generierte Artikel (JSON)
  site/                 <- Fertige Website (HTML)
    index.html          <- Startseite
    artikel/            <- Einzelne Artikelseiten
    kategorie/          <- Kategorieseiten
    sitemap.xml         <- Für Google
  used_topics.json      <- Verwendete Themen (lokal, nicht im Git)
  magazin.log           <- Protokoll (lokal, nicht im Git)
```

---

## Blog-Artikel anpassen

Alle Artikel liegen als JSON-Dateien im Ordner `articles/`. Du kannst sie jederzeit manuell bearbeiten.

### Dateiformat

Jede Datei heißt `YYYY-MM-DD_slug.json` und enthält:

```json
{
  "title": "Artikel-Überschrift",
  "html_content": "<h2>...</h2><p>...</p>",
  "category": "Reise",
  "tags": ["Schottland", "Whisky"],
  "type": "article",
  "meta": {
    "meta_description": "SEO-Beschreibung (max. 160 Zeichen)",
    "teaser": "Vorschautext für die Startseite",
    "slug": "url-freundlicher-name",
    "keywords": "SEO Keywords, kommagetrennt",
    "og_description": "Social-Media-Beschreibung"
  },
  "date": "2026-03-13",
  "date_display": "13. März 2026"
}
```

### Artikel bearbeiten

1. Öffne die gewünschte JSON-Datei im `articles/`-Ordner mit einem Texteditor
2. Bearbeite den `html_content` (HTML-formatiert) oder andere Felder
3. Speichere die Datei
4. Baue die Website neu: `python main.py --build`

### Veröffentlichungsdatum ändern

Das Feld `date` bestimmt die Sortierung auf der Startseite (neueste zuerst). Das Feld `date_display` wird dem Leser angezeigt.

1. Ändere `"date": "YYYY-MM-DD"` auf das gewünschte Datum
2. Ändere `"date_display"` auf die deutsche Darstellung (z.B. `"13. März 2026"`)
3. Benenne die Datei um, damit das Datum im Dateinamen übereinstimmt
4. Website neu bauen: `python main.py --build`

### Artikel löschen

1. Lösche die JSON-Datei aus dem `articles/`-Ordner
2. Website neu bauen: `python main.py --build`

### Affiliate-Links einfügen

Im `html_content` können Affiliate-Links als HTML eingefügt werden:

- **Amazon:** `<a href="https://www.amazon.de/s?k=suchbegriff&tag=whiskyreise74-21" target="_blank" rel="noopener noreferrer" class="affiliate-link">Linktext</a>`
- **Tradedoubler (Flüge/Reisen):** `<a href="https://clk.tradedoubler.com/click?p=227718&a=2205846" target="_blank" rel="noopener noreferrer" class="affiliate-link">Linktext</a>`
- **whisky.reise:** `<a href="https://www.whisky.reise/hotels/" target="_blank" rel="noopener noreferrer" class="affiliate-link">Linktext</a>`

---

## FAQ / Häufige Fragen

**Wie füge ich neue Themen hinzu?**
Öffne `topic_library.py` und füge neue Einträge zur Liste `WHISKY_TOPICS` hinzu. Format: `{"title": "...", "category": "Whisky", "tags": ["..."], "type": "article"}`

**Kann ich das Design ändern?**
Ja! Das gesamte CSS ist in `site_builder.py` in der Funktion `_base_template()`. Ändere die Farben unter `:root` oder das Layout im CSS.

**Was passiert wenn alle 73 Themen aufgebraucht sind?**
Das System startet automatisch von vorne oder du kannst `used_topics.json` löschen um alle Themen wieder freizugeben.

**Kann ich Artikel manuell bearbeiten?**
Ja! Öffne die JSON-Datei im `articles/`-Ordner, bearbeite den HTML-Inhalt im Feld `html_content`, und baue die Website neu mit `python main.py --build`.

**OpenAI "insufficient_quota" Fehler?**
Guthaben aufladen: https://platform.openai.com/settings/organization/billing

**Muss mein PC die ganze Zeit an sein?**
Nein. Du führst das Programm manuell aus, wann immer du neue Artikel willst. Z.B. einmal pro Woche `starten.bat` -> Option [5] für 3 neue Artikel.
