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
     +---------+--------+     | - DeepL API (Uebersetzung)|
               |               | - Azure Translator (Fallb)|
     +---------+--------+     +---------------------------+
     | GitHub Repo       |
     | derhefter/        |
     | whisky-magazin-v2 |
     +-------------------+
```

### URLs

| Was                  | URL                                              |
| -------------------- | ------------------------------------------------ |
| **Website**          | https://www.whisky-reise.com                     |
| **Admin-Dashboard**  | https://www.whisky-reise.com/admin/              |
| **GitHub-Repo**      | https://github.com/derhefter/whisky-magazin-v2   |
| **Vercel-Dashboard** | https://vercel.com (Projekt: whisky-magazin-new) |
| **Brevo-Dashboard**  | https://app.brevo.com                            |

### Automatischer Betrieb

Das System laeuft weitgehend automatisch:

| Zeitpunkt                 | Was passiert                                         | Wer/Was                        |
| ------------------------- | ---------------------------------------------------- | ------------------------------ |
| **Montag 07:00 CEST**     | 2 neue Artikel-Entwuerfe werden generiert            | GitHub Actions (Cron)          |
| **Nach Generierung**      | E-Mail an rosenhefter@gmail.com                      | Brevo Transactional API        |
| **Mittwoch 10:00 CEST**   | Aeltester freigegebener Entwurf wird veroeffentlicht | Vercel Cron-Job                |
| **Samstag 10:00 CEST**    | Aeltester freigegebener Entwurf wird veroeffentlicht | Vercel Cron-Job                |
| **Bei Artikel-Aenderung** | Website wird automatisch neu gebaut                  | GitHub Actions                 |

**Du musst nur:** Entwuerfe im Dashboard pruefen und freigeben. Alles andere laeuft automatisch.

---

## 2. Admin-Dashboard -- Komplett-Anleitung

### 2.1 Login

1. Oeffne https://www.whisky-reise.com/admin/
2. Gib das Passwort ein (gespeichert in Vercel -> Settings -> Environment Variables -> `DASHBOARD_PASSWORD`)
3. Klicke "Anmelden"

**Session:** Die Anmeldung bleibt 24 Stunden gueltig, auch wenn du den Tab schliesst. Danach musst du dich erneut anmelden.

**Probleme beim Login:**

| Fehlermeldung       | Ursache                                   | Loesung                                                        |
| ------------------- | ----------------------------------------- | -------------------------------------------------------------- |
| "Falsches Passwort" | Passwort stimmt nicht                     | Vercel -> Settings -> Env Vars -> `DASHBOARD_PASSWORD` pruefen |
| "Server-Fehler"     | `DASHBOARD_PASSWORD` nicht gesetzt        | In Vercel setzen und neu deployen                              |
| "Zu viele Versuche" | 5 Fehlversuche in 15 Min.                 | 15 Minuten warten                                              |
| "Netzwerkfehler"    | Keine Internetverbindung oder Vercel down | Verbindung pruefen                                             |

---

### 2.2 Tab: Uebersicht

Zeigt 4 Kennzahlen auf einen Blick:

| KPI                 | Bedeutung                                                   |
| ------------------- | ----------------------------------------------------------- |
| **Abonnenten**      | Anzahl Newsletter-Abonnenten in Brevo                       |
| **Entwuerfe**       | Anzahl offener Artikel-Entwuerfe (ausstehend + freigegeben) |
| **Themen offen**    | Noch nicht bearbeitete Themen aus der Themen-Queue          |
| **Themen erledigt** | Bereits bearbeitete Themen                                  |

Jede Karte ist **klickbar** und navigiert direkt zum zugehoerigen Tab.

---

### 2.3 Tab: Artikel verwalten

Hier siehst du alle Entwuerfe und veroeffentlichten Artikel.

#### Artikel-Status

| Status             | Bedeutung                                                   | Badge-Farbe |
| ------------------ | ----------------------------------------------------------- | ----------- |
| **Ausstehend**     | Neu generiert, wartet auf Pruefung                          | Gelb        |
| **In Bearbeitung** | Wurde bearbeitet, noch nicht freigegeben                    | Blau        |
| **Freigegeben**    | Wird beim naechsten Cron-Lauf veroeffentlicht (Mi/Sa 10:00) | Gruen       |

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

| Aktion                 | Wie                                                                                                                               |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Filtern**            | Oben: Filter nach Saison (Fruehling/Sommer/Herbst/Winter/Ostern/Weihnachten/Silvester) und Status (Offen/In Bearbeitung/Erledigt) |
| **Neues Thema**        | Button "Neues Thema" oben rechts -> Titel, Kategorie, Saison, Prioritaet eingeben -> Speichern                                    |
| **Erledigt markieren** | Haekchen-Icon in der Zeile klicken                                                                                                |
| **Loeschen**           | Papierkorb-Icon in der Zeile klicken (nach Bestaetigung)                                                                          |
| **Artikel generieren** | Blitz-Icon (⚡) -> Erzeugt einen KI-Entwurf direkt aus dem Thema (dauert ca. 20-30 Sek.)                                           |

#### Themen-Felder

| Feld           | Beschreibung                                  |
| -------------- | --------------------------------------------- |
| **Titel**      | Thema des zu erstellenden Artikels            |
| **Kategorie**  | Whisky, Reise, Lifestyle, Natur, Urlaub       |
| **Saison**     | Wann das Thema am besten passt                |
| **Anlass**     | Optionaler Anlass (Ostern, Weihnachten, etc.) |
| **Prioritaet** | 1-20, hoeher = wichtiger                      |
| **Notizen**    | Interne Notizen/Hinweise fuer die Generierung |

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

### 2.7 Whisky-Glossar (Admin-Bereich)

Das Glossar ist unter `/whisky-glossar/` oeffentlich erreichbar und enthaelt vier Entitaeten: **Laender**, **Regionen**, **Destillerien** und **Whiskys (Abfuellungen)**. Alle Daten werden redaktionell im Admin-Bereich gepflegt und als JSON-Dateien unter `data/glossary/` im GitHub-Repository gespeichert.

---

> ### ⚡ WICHTIG FUER BEARBEITER: Wie Aenderungen live gehen
>
> **Daten werden NICHT sofort auf der Website sichtbar** — sie durchlaufen immer diesen Weg:
>
> ```
> Admin: "Veroeffentlichen" klicken
>        ↓  (sofort)
> Daten werden in GitHub committed (automatisch, kein Push noetig)
>        ↓  (~30 Sek.)
> Vercel erkennt den neuen Commit und startet einen Website-Build
>        ↓  (~1-2 Min.)
> python main.py --build-v2 generiert alle HTML-Seiten neu
>        ↓  (fertig)
> whisky-reise.com zeigt den aktualisierten Stand
> ```
>
> **Gesamtdauer: ca. 1–2 Minuten** nach dem Klick auf "Veroeffentlichen".
>
> **Erkennbar im Admin:** Nach dem Veroeffentlichen erscheint unten ein blauer Banner mit gruenem Puls-Punkt — *"Glossar-Seiten werden auf whisky-reise.com neu gebaut…"*. Nach ~2,5 Minuten wechselt er automatisch zu *"abgeschlossen ✓"*.
>
> **Kein manueller Eingriff noetig.** Es ist nicht erforderlich, Code zu pushen, lokal zu bauen oder sonstige Schritte auszufuehren.

---

#### Typischer Arbeitsablauf einer Datenpflege-Session

```
1. Im Admin einloggen (whisky-reise.com/admin/)
2. Tab "Glossar" → Sub-Tab "Import" oeffnen
3. CSV- oder JSON-Datei hochladen → Import starten
4. Sub-Tab "Review" oeffnen
5. Neue Eintraege pruefen und freigeben (s.u.)
6. Button "Alle veröffentlichen" klicken
7. Blauer Banner erscheint → ~2 Min. warten
8. Oeffentliche Glossar-Seite pruefen: whisky-reise.com/whisky-glossar/
```

---

#### Review-Queue: Eintraege freigeben

Nach jedem Import landen alle Eintraege in der Review-Queue (Sub-Tab "Review"). Es gibt zwei Typen:

| Typ | Symbol | Bedeutung | Vorgehen |
|-----|--------|-----------|----------|
| `new` | gruen | Voellig neuer Eintrag | Checkbox anhaeken → Batch-Freigabe |
| `update_candidate` | blau | Eintrag existiert bereits, Import hat neue/andere Felder | Einzeln pruefen mit Feld-Vergleich |

**Batch-Freigabe fuer neue Eintraege:**

Neue Eintraege ohne Duplikat-Verdacht koennen in einem Schritt freigegeben werden:

1. Button **"☐ Alle neuen auswaehlen"** (oben rechts in der Queue) anklicken — alle waehlbaren Eintraege werden gecheckt
2. Grüne Aktionsleiste erscheint: *"X ausgewaehlt"*
3. **"✓ Alle freigeben"** klicken → Bestaetigungsdialog → Fortschrittsbalken laeuft durch
4. Danach: **"🚀 Alle veroeffentlichen"** klicken (gruener Balken unten in der Queue)

> **Hinweis:** Eintraege mit `update_candidate`-Status oder Duplikat-Warnung (gelbes Dreieck ⚠) erscheinen **ohne Checkbox** und muessen einzeln geprueft werden.

**Einzelne Eintraege entscheiden (inkl. update_candidate):**

1. **"✓ Entscheiden"** klicken → Review-Modal oeffnet sich
2. Bei `update_candidate`: Feld-Vergleich wird angezeigt (bestehend vs. Import)
   - Felder die neu befuellt werden → werden automatisch uebernommen
   - Felder mit abweichenden Werten → per Klick waehlen welcher Wert behalten wird
3. Entscheidung treffen: **"✓ Freigeben"**, **"⇄ Als Update uebernehmen"** oder **"✗ Ablehnen"**

#### Review-Entscheidungen im Detail

| Entscheidung | Wann verwenden | Was passiert |
|---|---|---|
| **Freigeben** (`approve`) | Neuer Eintrag ist korrekt | Wird unveraendert uebernommen |
| **Als Update uebernehmen** (`merge`) | Bestehender Eintrag soll aktualisiert werden | Smart-Merge: leere Felder werden gefuellt, bei Konflikten gilt die im Modal gewahlte Entscheidung |
| **Ablehnen** (`reject`) | Eintrag ist fehlerhaft oder Duplikat | Wird verworfen, bleibt in der Queue als "rejected" |

#### Smart-Merge-Logik

Beim Typ "Als Update uebernehmen" werden Felder intelligent zusammengefuehrt:

- **Lange Texte** (`long_description`, `short_description`, `travel_context`, `visit_info`, `style_notes`, `editorial_notes`): Bestehender Text bleibt erhalten, wenn er laenger ist — verhindert versehentlichen Inhaltsverlust
- **Alle anderen Felder**: Neuer Wert wird uebernommen, falls nicht leer; andernfalls bleibt bestehender Wert (schuetzt URLs, Koordinaten, Bilder)
- **Manuelle Konflikt-Auswahl**: Im Review-Modal koennen Felder mit abweichendem Inhalt per Klick einzeln entschieden werden

#### Duplikat-Erkennung

Beim Import prueft das System automatisch auf potenzielle Duplikate:

- **Teilstring-Abgleich**: "Ardbeg 10" ↔ "Ardbeg 10 Jahre" → Duplikat-Warnung
- **Bigram-Aehnlichkeit**: Namen mit ≥ 80 % Uebereinstimmung werden gemeldet
- **Destillerie + Reifezeit**: Gleiche Destillerie + gleiches Alter → Warnung
- Verdaechtige Eintraege erscheinen in der Queue mit gelbem Hinweis und muessen manuell entschieden werden

#### Datenstruktur

| Entitaet          | Datei                              | Pflichtfelder                                        |
|-------------------|------------------------------------|------------------------------------------------------|
| **Laender**       | `data/glossary/countries.json`     | id, slug, name_de                                    |
| **Regionen**      | `data/glossary/regions.json`       | id, slug, name, country_id                           |
| **Destillerien**  | `data/glossary/distilleries.json`  | id, slug, name, country_id, region_id                |
| **Abfuellungen**  | `data/glossary/whiskies.json`      | id, slug, name, country_id, distillery_id, whisky_type, abv |

#### Destillerien-Status

| Status       | Bedeutung      |
|--------------|----------------|
| `active`     | Aktiv          |
| `silent`     | Still gelegt   |
| `closed`     | Geschlossen    |
| `mothballed` | Eingemottet    |
| `demolished` | Abgerissen     |

#### Direktzugriff ueber API (fuer Entwickler)

```
GET  ?action=list&entity=distilleries         – Alle Eintraege
GET  ?action=get&entity=distilleries&id=xxx   – Einzelner Eintrag
POST ?action=save   { entity, entry }         – Erstellen / Aktualisieren
POST ?action=delete { entity, id }            – Soft-Delete (setzt published=false)
POST ?action=import_batch                     – CSV oder JSON importieren
GET  ?action=review_queue                     – Review-Queue abrufen
POST ?action=review_decision                  – Einzelne Entscheidung
POST ?action=publish_approved                 – Freigegebene Eintraege live schalten
```

Alle Operationen erfordern den Admin-Token im HTTP-Header `x-admin-token`.

---

## 3. Automatisierung

### 3.1 GitHub Actions (automatische Artikel-Generierung)

| Eigenschaft     | Wert                                                                              |
| --------------- | --------------------------------------------------------------------------------- |
| **Workflow**    | `Auto-Generate Articles`                                                          |
| **Datei**       | `.github/workflows/auto-generate.yml`                                             |
| **Zeitplan**    | Jeden Montag, 07:00 CEST (Sommer) / 06:00 CET (Winter) -- Cron `0 5 * * 1` (UTC)  |
| **Befehl**      | `python main.py --auto -n 2` auf einem Ubuntu-Runner                              |
| **Log**         | GitHub -> Actions -> "Auto-Generate Articles" -> Run auswaehlen                   |

**Was passiert:**

1. 2 Artikel-Entwuerfe werden per GPT-4o generiert
2. Entwuerfe werden als JSON in `articles/drafts/` auf GitHub gepusht
3. Benachrichtigungs-E-Mail wird an rosenhefter@gmail.com gesendet (sofern `BREVO_API_KEY` als Repo-Secret gesetzt ist)
4. Entwuerfe erscheinen im Dashboard unter "Artikel"

**Manuell ausfuehren (z.B. fuer Tests):**

1. GitHub -> Repository oeffnen
2. Reiter "Actions" -> "Auto-Generate Articles"
3. Rechts: "Run workflow" -> Anzahl eingeben (z.B. `1` fuer API-schonenden Test) -> "Run workflow"
4. Nach ~2-3 Minuten erscheint der neue Draft im Dashboard

**Alternativ lokal ausfuehren (Ad-hoc-Generierung):**

```
cd "C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin"
python main.py --auto -n 3
```

**Voraussetzung:** Repo-Secrets unter *GitHub -> Settings -> Secrets and variables -> Actions*:

- `OPENAI_API_KEY` (Pflicht) -- sonst bricht der Workflow im Step "OpenAI Key pruefen" ab
- `BREVO_API_KEY` (optional) -- ohne diesen Key laeuft die Generierung durch, aber die E-Mail-Benachrichtigung wird uebersprungen

### 3.2 Vercel Cron-Jobs (automatische Veroeffentlichung)

Konfiguriert in `vercel.json`:

| Zeitpunkt                  | Schedule (UTC) | Aktion                                           |
| -------------------------- | -------------- | ------------------------------------------------ |
| **Mittwoch 10:00 / 09:00** | `0 8 * * 3`    | Aeltesten freigegebenen Entwurf veroeffentlichen |
| **Samstag 10:00 / 09:00**  | `0 8 * * 6`    | Aeltesten freigegebenen Entwurf veroeffentlichen |

> **Sommer-/Winterzeit:** Der Cron laeuft fix um **08:00 UTC**. In der Sommerzeit (CEST, MESZ) entspricht das **10:00 Uhr deutscher Zeit**, in der Winterzeit (CET) **09:00 Uhr**. Vercel kennt keine Zeitzone — wenn du fix 10:00 deutsche Zeit willst, muesste der Schedule im Winter auf `0 9 * * 3,6` geaendert werden.

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

**Zweiter Workflow – `auto-generate.yml`:** Siehe Abschnitt 3.1. Laeuft automatisch jeden Montag 07:00 CEST und erstellt 2 Entwuerfe in `articles/drafts/`. Kann zusaetzlich jederzeit manuell ueber "Run workflow" angestossen werden.

### 3.4 E-Mail-Benachrichtigungen

Jedes Mal wenn `python main.py --auto` laeuft (Montag 07:00 CEST per GitHub-Actions-Cron, siehe 3.1), sendet das System eine HTML-E-Mail via Brevo Transactional API:

| Eigenschaft    | Wert                                                                                                                           |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Empfaenger** | rosenhefter@gmail.com                                                                                                          |
| **Absender**   | whisky-news@whisky-reise.com (via Brevo)                                                                                       |
| **Betreff**    | "X neue Whisky-Artikel warten auf Freigabe"                                                                                    |
| **Inhalt**     | Titel, Kategorie, Teaser und Wortanzahl jedes Entwurfs; Direktlink zum Dashboard; naechste Veroeffentlichungstermine (Mi + Sa) |

**Voraussetzung:**

- Fuer den automatischen Montags-Lauf: `BREVO_API_KEY` als GitHub-Actions-Secret (Settings -> Secrets and variables -> Actions).
- Fuer lokale Ad-hoc-Laeufe (`python main.py --auto`): `BREVO_API_KEY` in der lokalen `.env`-Datei.

Ohne den Key laeuft die Generierung normal durch, nur die Benachrichtigungs-E-Mail wird uebersprungen.

**E-Mail manuell testen:**

```bash
cd "C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin"
python -c "from notifier import notify_new_drafts; notify_new_drafts([{'title':'Test','category':'Whisky','meta':{'teaser':'Testteaser'},'html_content':'<p>Test</p>'}])"
```

---

## 4. Mehrsprachigkeit (KI-Uebersetzung)

### 4.1 Uebersicht

Alle Artikel-Seiten zeigen eine Sprachleiste direkt unterhalb des Hero-Bildes:

```
🌐  DE · EN · FR · NL · ES · JA
```

- **DE** ist immer die Originalsprache (kein API-Aufruf, kein Kosten)
- Klick auf eine andere Sprache: Artikel wird per KI uebersetzt und im Browser angezeigt
- **Erste Anfrage** einer Sprache: ~2–5 Sekunden (API-Aufruf + GitHub-Cache anlegen)
- **Folgeaufrufe**: sofort (Server-Cache in GitHub + Browser-localStorage 24h)
- Die URL aktualisiert sich auf `?lang=en` — Link ist direkt teilbar

### 4.2 Technischer Ablauf

```
Nutzer klickt [EN]
  → Browser prueft localStorage (24h-Cache)
    → Treffer: sofort anzeigen
    → Kein Treffer: GET /api/translate?slug=&lang=en
      → GitHub prueft articles/translations/en/slug.json
        → Vorhanden: zurueckgeben (< 50ms)
        → Nicht vorhanden: DeepL API aufrufen
          → Bei 429/Quota: Azure Translator aufrufen
          → Ergebnis in GitHub cachen, zurueckgeben
  → h1-Titel + Artikel-Body im DOM ersetzen
```

### 4.3 Kosten und Kontingente

| Service              | Freies Kontingent        | Danach               | Einsatz                         |
| -------------------- | ------------------------ | -------------------- | ------------------------------- |
| **DeepL API Free**   | 500.000 Zeichen / Monat  | 5,49 EUR / Monat     | Primaer (beste Qualitaet EU+JA) |
| **Azure Translator** | 2.000.000 Zeichen / Monat| 10 USD / Mio. Zeichen| Automatischer Fallback          |

**Richtwerte:**
- 1 Artikel ≈ 12.000 Zeichen (inkl. HTML)
- 1 Artikel in 5 Sprachen ≈ 60.000 Zeichen
- 8 neue Artikel / Monat × 5 Sprachen = ~480.000 Zeichen → passt in DeepL Free
- Backkatalog (~80 Artikel × 5 Sprachen = 4,8 Mio.) → ueber mehrere Monate per Azure abrufen

**Rate-Limit:** Max. 10 neue Uebersetzungsanfragen pro IP/Stunde (Schutz vor unkontrollierten Kosten). Gecachte Antworten zaehlen nicht.

### 4.4 Welche Inhalte werden uebersetzt?

| Feld               | Uebersetzt | Hinweis                                       |
| ------------------ | ---------- | --------------------------------------------- |
| Artikel-Titel      | Ja         | Wird in der h1 ersetzt                        |
| Artikel-Volltext   | Ja         | HTML-Inhalt mit Tag-Handling                  |
| Teaser / Excerpt   | Ja         | Im Cache gespeichert                          |
| Meta-Description   | Ja         | Im Cache gespeichert (nicht im DOM sichtbar)  |
| Navigation         | Nein       | Statisch DE (Phase 2 geplant)                 |
| Glossar            | Nein       | Phase 2                                       |
| Index/Kategorie    | Nein       | Phase 3 (Teaser-Uebersetzung)                 |

### 4.5 Uebersetzungs-Cache verwalten

Gecachte Uebersetzungen liegen in GitHub unter:

```
articles/translations/
  en/
    2026-01-15_mein-artikel-slug.json
    ...
  fr/
    ...
  nl/ es/ ja/
```

**Cache fuer einen Artikel loeschen (Neuuebersetzung erzwingen):**

1. GitHub Repo oeffnen -> `articles/translations/{lang}/`
2. Datei `{slug}.json` loeschen
3. Beim naechsten Nutzer-Klick wird automatisch neu uebersetzt

**Alle Uebersetzungen einer Sprache loeschen:**

```bash
# Lokal
rm articles/translations/en/*.json
git add -A && git commit -m "fix: clear en translation cache" && git push
```

### 4.6 API-Endpunkt Details

```
GET /api/translate?slug={slug}&lang={lang}
```

| Parameter | Werte                   |
| --------- | ----------------------- |
| `slug`    | Artikel-Slug (aus URL)  |
| `lang`    | en, fr, nl, es, ja      |

**Antwort (JSON):**

```json
{
  "lang": "en",
  "source_lang": "de",
  "slug": "mein-artikel-slug",
  "translated_at": "2026-04-19T17:00:00Z",
  "service": "deepl",
  "title": "...",
  "html_content": "...",
  "teaser": "...",
  "meta_description": "..."
}
```

---

## 5. Manuelle Operationen

### 5.1 Artikel lokal generieren

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

### 5.2 Website lokal bauen und testen

```bash
# Website komplett neu bauen (generiert alle HTML-Seiten):
python main.py --build-v2

# Lokalen Webserver starten (zum Testen):
python main.py --serve-v2
# Oeffnet http://localhost:8000

# Sicherheits-Smoke-Tests laufen lassen (HMAC, DOI, Retry-Logik):
python -m pytest tests/ -v
# Erwartung: 17 passed
```

### 5.3 Artikel direkt bearbeiten (ohne Dashboard)

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

### 5.4 Bilder verwalten

- Bilder liegen in `site-v2/images/`
- Werden automatisch von Unsplash heruntergeladen bei der Generierung
- **Eigene Bilder:** Als JPG in `site-v2/images/` ablegen, Dateiname = Slug des Artikels
- In der Artikel-JSON: `"image_url": "/images/dateiname.jpg"` setzen

### 5.5 Karten-Eintraege hinzufuegen

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

### 5.6 Produkte / Affiliate-Links anpassen

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

### 5.7 Seiten im Site-Builder anpassen

Alle Seiten werden von `site_builder_v2.py` generiert:

| Seite              | Funktion im Builder                      | Wann aendern                                                                                                   |
| ------------------ | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Startseite         | `build_index_page()` (~Zeile 1800)       | Hero-Text, Trust-Stats, Anzahl Artikel                                                                         |
| Artikel            | `build_article_page()`                   | Automatisch aus JSON                                                                                           |
| Kategorie-Seiten   | `build_category_page()`                  | Automatisch; Meta-Descriptions im Dict `_category_descriptions` innerhalb der Funktion pflegen                 |
| Karte              | `build_map_page()` (~Zeile 2100)         | Bei Kartendesign-Aenderungen                                                                                   |
| Ueber uns          | `build_about_page()` (~Zeile 3030)       | Autoren-Info, Statistiken                                                                                      |
| Impressum          | `build_impressum_page()` (~Zeile 3388)   | Bei Adress- oder Kontaktaenderungen -- Seite traegt automatisch `noindex, follow` und ist nicht in der Sitemap |
| Datenschutz        | `build_datenschutz_page()` (~Zeile 3468) | Bei neuen Trackern/Affiliates -- Seite traegt automatisch `noindex, follow` und ist nicht in der Sitemap       |
| Suche              | `build_suche_page()` (~Zeile 3740)       | Selten -- Seite traegt automatisch `noindex, follow` und ist nicht in der Sitemap                              |
| Sitemap            | `build_sitemap()` (~Zeile 3894)          | Bewusst ohne impressum, datenschutz, suche. Neue SEO-irrelevante Seiten hier ebenfalls weglassen               |
| Navigation         | `_base_template()` (~Zeile 1150)         | Bei neuen Menue-Eintraegen                                                                                     |
| `<head>`-Meta-Tags | `_base_template()` (~Zeile 282)          | Bei neuen Verification-Tags (Google, Pinterest, etc.)                                                          |

**SEO-Hinweis:** Neue Seiten, die nicht indexiert werden sollen (Utility-, Legal- oder Duplikat-Seiten), muessen zwei Dinge bekommen: (1) `<meta name="robots" content="noindex, follow">` im `<head>` und (2) keinen Eintrag in `build_sitemap()`. Beides wird im Builder per Post-Processing (`.replace()`-Aufruf nach `.format()`) und durch Weglassen in der `static_pages`-Liste geloest -- analog zu impressum/datenschutz/suche.

Nach jeder Aenderung: `python main.py --build-v2`

#### Webmaster-Verification-Tags

Im `<head>`-Bereich jeder Seite sind aktuell folgende Verification-Tags hinterlegt (in `_base_template()`, ~Zeile 271 in `site_builder_v2.py`):

| Dienst                | Meta-Tag                                                                                       |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| Google Search Console | `<meta name="google-site-verification" content="3OKzP9zKRrZV5V4-chXaN7GG39fdLAEeymXqKeqn4Rw">` |
| Pinterest             | `<meta name="p:domain_verify" content="4b7a0461f2dd530e9a9c5894618a229d">`                     |

Neuen Verification-Tag hinzufuegen: Einfach in `_base_template()` unterhalb der bestehenden Tags eintragen, dann `python main.py --build-v2` ausfuehren. Der Tag erscheint automatisch auf **allen** generierten Seiten.

#### Pinterest Tracking Tag (Pixel)

Zusaetzlich zum Verification-Tag ist der **Pinterest Pixel** (Tag-ID: `2613413631015`) auf allen Seiten aktiv. Er wird durch die Konstante `_PINTEREST_TAG` in `site_builder_v2.py` (Zeile ~22) definiert und von `_write_html()` automatisch vor `</head>` jeder HTML-Datei eingefuegt.

| Event      | Seite        | Zweck                                       |
| ---------- | ------------ | ------------------------------------------- |
| `PageView` | Alle Seiten  | Seitenaufrufe tracken, Zielgruppe aufbauen  |
| `lead`     | `danke.html` | Newsletter-Anmeldung als Conversion zaehlen |

**Pinterest Tag-ID aendern oder deaktivieren:** Konstante `_PINTEREST_TAG` in `site_builder_v2.py` anpassen, dann neu bauen.

**Naechster Schritt (Auto-Pinnen):** Artikel koennen automatisch beim Veroeffentlichen als Pinterest-Pin erstellt werden. Dafuer werden benoetigt:

- `PINTEREST_ACCESS_TOKEN` (aus Pinterest Developer App)
- `PINTEREST_BOARD_ID` (Ziel-Pinnwand)
  Beide als Vercel Environment Variables setzen.

---

## 6. Konfiguration

### 6.1 Vercel Environment Variables

Alle hier aufgefuehrten Variablen muessen in Vercel unter **Settings -> Environment Variables** gesetzt sein.

| Variable             | Beschreibung                                                         | Beispielwert                              |
| -------------------- | -------------------------------------------------------------------- | ----------------------------------------- |
| `DASHBOARD_PASSWORD` | Login-Passwort fuer /admin                                           | (frei waehlbar, sicher!)                  |
| `CRON_SECRET`        | Absicherung der Mi/Sa-Cron-Jobs gegen unberechtigte Aufrufe          | (langer Zufalls-String, mind. 32 Zeichen) |
| `GITHUB_TOKEN`       | Fine-grained PAT mit read+write auf das Repo                         | ghp_...                                   |
| `GITHUB_REPO`        | Repository-Pfad                                                      | `derhefter/whisky-magazin-v2`             |
| `GITHUB_BRANCH`      | Branch (Standard: main)                                              | `main`                                    |
| `BREVO_API_KEY`      | Brevo API-Key fuer Newsletter + Abonnenten-Statistik                 | xkeysib-...                               |
| `BREVO_LIST_ID`      | Brevo Newsletter-Listen-ID                                           | `3`                                       |
| `OPENAI_API_KEY`          | OpenAI Key fuer KI-Texte (WotM-Polishing + Dashboard-Generierung)    | sk-...                               |
| `UNSPLASH_API_KEY`        | Unsplash Key fuer automatische Artikelbilder (Dashboard-Generierung) | (Unsplash Developer Key)             |
| `SITE_URL`                | Basis-URL der Seite                                                  | `https://www.whisky-reise.com`       |
| `DEEPL_API_KEY`           | DeepL API Key fuer Artikel-Uebersetzungen (primaer)                  | Free-Keys enden auf `:fx`            |
| `AZURE_TRANSLATOR_KEY`    | Azure Translator Key (Fallback wenn DeepL Quota erschoepft)          | Aus Azure Portal -> Cognitive Svcs   |
| `AZURE_TRANSLATOR_REGION` | Azure-Region des Translator-Dienstes                                 | `westeurope` (Standard)              |
| `ADMIN_KEY_VERSION`       | Zaehler (kein Random!) — wird in den HMAC der Admin-Tokens gemischt. Inkrementieren = alle Browser-Sessions sofort ungueltig. | `1` (Start), `2`, `3` ... |
| `NEWSLETTER_TOKEN_SECRET` | Eigenes Secret fuer DOI-/Unsubscribe-Tokens, entkoppelt vom Brevo-Key. Ohne Setzung Fallback auf Legacy-Schema. | `<32+ Bytes Base64>` |
| `TURNSTILE_SECRET_KEY`    | Cloudflare-Turnstile-Secret fuer Captcha auf Newsletter/Feedback/Survey. Ohne Setzung wird die Captcha-Pruefung uebersprungen (Fail-open). | (aus Cloudflare-Dashboard, NICHT der Site-Key) |

**Wichtig:** Nach jeder Aenderung an Environment Variables muss Vercel **neu deployt** werden!

**Neuen CRON_SECRET setzen (einmalig):**

1. Vercel Dashboard -> Settings -> Environment Variables
2. Neue Variable: Name = `CRON_SECRET`, Value = ein langer zufaelliger String (z.B. via Passwort-Generator, mind. 32 Zeichen)
3. Neu deployen

### 6.2 Lokale Konfiguration

#### `.env` (im Projektordner, nicht in Git)

```
BREVO_API_KEY=xkeysib-...        # Nur fuer lokale `python main.py --auto`-Laeufe (der Montags-Cron nutzt das GitHub-Secret)
OPENAI_API_KEY=sk-proj-...       # Optional: wird auch aus config.json gelesen
CRON_SECRET=...                  # Nur fuer Vercel noetig, lokal nicht benoetigt
```

`BREVO_API_KEY` ist fuer die montaegliche E-Mail-Benachrichtigung an rosenhefter@gmail.com zustaendig. Den **automatischen** Montags-Lauf uebernimmt GitHub Actions (siehe 3.1); dort muss der Key als Repo-Secret unter *Settings -> Secrets and variables -> Actions* gesetzt sein. In der lokalen `.env` wird er nur fuer manuelle `python main.py --auto`-Laeufe gebraucht. Ohne Key wird die E-Mail uebersprungen (kein Fehler, nur kein Versand).

#### `config.json` (im Projektordner, nicht in Git)

| Feld                                | Beschreibung        | Wann aendern       |
| ----------------------------------- | ------------------- | ------------------ |
| `site.base_url`                     | Basis-URL der Seite | Bei Domain-Wechsel |
| `site.name`                         | Seitenname          | Bei Umbenennung    |
| `site.author`                       | Autoren             | Bei Aenderung      |
| `openai.api_key`                    | OpenAI API Key      | Bei Key-Erneuerung |
| `openai.model`                      | GPT-Modell          | Bei Modellwechsel  |
| `affiliate_links.amazon_tag`        | Amazon Partner-Tag  | Bei Tag-Aenderung  |
| `content_settings.unsplash_api_key` | Unsplash Key        | Bei Key-Erneuerung |

### 6.3 Brevo-Setup (Newsletter)

| Einstellung           | Wert                                                                |
| --------------------- | ------------------------------------------------------------------- |
| **Kontaktliste**      | Liste ID `3` ("Whisky Magazin Newsletter")                          |
| **DOI Template**      | Template ID `1` (Bestaetigungs-E-Mail mit `{{ doubleoptin }}` Link) |
| **Redirect nach DOI** | https://www.whisky-reise.com/danke.html                             |

**Pruefen:** https://app.brevo.com -> Kontakte -> Listen

---

## 7. Sicherheit & Wartung

### 7.1 Passwort-Rotation

Das Dashboard-Passwort sollte regelmaessig geaendert werden:

1. Vercel Dashboard -> Settings -> Environment Variables
2. `DASHBOARD_PASSWORD` aendern
3. Vercel neu deployen
4. Neues Passwort sicher notieren (z.B. Passwort-Manager)

**Achtung:** Alle aktiven Sessions werden nach dem Wechsel ungueltig (Token basiert auf dem Passwort).

### 7.2 GitHub Token erneuern

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

### 7.3 API-Key-Management

| Key              | Wo gespeichert                 | Ablauf                                  | Erneuern unter                                        |
| ---------------- | ------------------------------ | --------------------------------------- | ----------------------------------------------------- |
| OpenAI           | `config.json` (lokal) + Vercel | Laeuft nicht ab, kann widerrufen werden | https://platform.openai.com/api-keys                  |
| Unsplash         | `config.json` (lokal)          | Laeuft nicht ab                         | https://unsplash.com/oauth/applications               |
| Brevo            | `.env` (lokal) + Vercel        | Laeuft nicht ab                         | https://app.brevo.com -> Settings -> API Keys         |
| GitHub           | Vercel                         | Fine-grained: max 1 Jahr                | https://github.com/settings/tokens                    |
| DeepL            | Vercel                         | Laeuft nicht ab; Free: 500k Zchn/Mon.  | https://www.deepl.com/pro-account                     |
| Azure Translator | Vercel                         | Laeuft nicht ab; Free: 2 Mio. Zchn/Mon | https://portal.azure.com -> Cognitive Services        |

### 7.4 Sicherheitsfeatures (implementiert)

> **Audit-Stand 2026-04-26:** vollstaendiger Sicherheits- und Stabilitaets-Check abgeschlossen.
> 19 identifizierte Schwachstellen (S1–S19) sind code-seitig adressiert. Plan-Tasks T1–T10
> abgeschlossen. Live-Smokes erfolgreich (translate?status=1 → 401, Turnstile-Widget aktiv,
> Newsletter-DOI funktional). Test-Suite: `python -m pytest tests/` → 17 passed.


- **HMAC-SHA256 Token-Authentifizierung** mit **8-Stunden-Ablauf** und **`ADMIN_KEY_VERSION`-Mischung** (Inkrementieren = sofortige Session-Invalidierung).
- **Rate Limiting** auf Login (max. 5 Versuche / 15 Minuten — best-effort, da Vercel-Lambda keinen persistenten Speicher hat).
- **Cloudflare Turnstile (Captcha)** auf Newsletter-, Feedback- und Survey-Forms (siehe `TURNSTILE_SECRET_KEY`).
- **HTML-Sanitizer (`bleach`)** auf dem Render-Pfad fuer LLM-generierten Artikel-HTML (XSS-Schutz).
- **DOMPurify** im Admin-SPA fuer Vorschau-Modals.
- **SSRF-Whitelist** im `set_image`-Endpoint (nur `images.unsplash.com` / `plus.unsplash.com`).
- **GitHub-PUT mit 1x-Retry** bei SHA-Konflikten (Race-Condition zwischen GitHub Actions und Vercel-Cron entschaerft).
- **Newsletter-Tokens entkoppelt vom Brevo-Key** via `NEWSLETTER_TOKEN_SECRET` — Brevo-Key-Rotation bricht keine Unsubscribe-Links mehr.
- **CORS-Einschraenkung** auf `whisky-reise.com` und `localhost:8000`.
- **Content Security Policy** (getrennte Regeln fuer Public und Admin).
- **Path-Traversal-Schutz** (Dateinamen-Validierung per Regex).
- **CRON_SECRET** fuer Vercel Cron-Authentifizierung.
- **noindex/nofollow** auf Admin-Seiten.
- **Double Opt-In** fuer Newsletter (DSGVO-konform).
- **Cookie-Consent-Banner** auf allen oeffentlichen Seiten.

### 7.5 Notfall: Admin-Session widerrufen

Wenn du den Verdacht hast, dein Admin-Token wurde geleakt (Browser-Plugin, fremdes Geraet, geteilter Bildschirm):

1. Vercel Dashboard -> Settings -> Environment Variables
2. `ADMIN_KEY_VERSION` um 1 erhoehen (z. B. `1` -> `2`)
3. Vercel neu deployen ("Redeploy" auf letztem Deployment)
4. **Effekt:** Alle aktiven Browser-Tokens sind sofort 401 — du musst dich neu einloggen, ein Angreifer mit altem Token wird ausgesperrt. Das `DASHBOARD_PASSWORD` selbst bleibt unveraendert.

### 7.6 Schluessel-Rotation (Runbook)

Reihenfolge bei einem vermuteten Komplettleak (z. B. `.env` versehentlich gepostet):

1. **OpenAI**: https://platform.openai.com/api-keys -> alten Key `Revoke`, neuen erstellen, in Vercel als `OPENAI_API_KEY` eintragen.
2. **Brevo**: https://app.brevo.com -> Settings -> API Keys -> alten Key loeschen, neuen erstellen, in Vercel als `BREVO_API_KEY` eintragen. **Wichtig:** Da `NEWSLETTER_TOKEN_SECRET` unabhaengig ist, bleiben bestehende DOI-/Unsubscribe-Links gueltig.
3. **Unsplash**: https://unsplash.com/oauth/applications -> Anwendung -> Secret regenerieren, in Vercel als `UNSPLASH_API_KEY`.
4. **CRON_SECRET**: Vercel-Env neu setzen (langer Random-String, mind. 32 Bytes Base64).
5. **Admin-Sessions**: `ADMIN_KEY_VERSION` inkrementieren (siehe 7.5).
6. **GitHub-PAT**: Falls geleakt, in https://github.com/settings/tokens als `Revoke`, neuen Fine-Grained mit Contents R/W erstellen, in Vercel + Repo-Secrets eintragen.
7. Vercel **redeployen**, GitHub-Action `auto-generate.yml` einmal manuell triggern, um zu pruefen dass der neue Token greift.

### 7.7 Bekannte Einschraenkungen

- Rate Limiting auf Admin-Operationen ist In-Memory pro Lambda-Instanz und damit auf Vercel nur best-effort. Die HMAC + `KEY_VERSION` + Captcha auf Public-Forms sind die wirksamen Schutzschichten.
- Der Admin-Bereich nutzt `unsafe-inline` fuer JavaScript in der CSP, da das Dashboard ein Single-Page-HTML ist. Fuer die oeffentliche Seite ist `unsafe-inline` nur fuer Styles aktiv (benoetigt fuer Leaflet.js).

---

## 8. Fehlerbehebung

### 8.1 Haeufige Probleme

| Problem                                                             | Moegliche Ursache                       | Loesung                                                                                                      |
| ------------------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Dashboard zeigt "Fehler"                                            | GITHUB_TOKEN abgelaufen                 | Neuen Token in Vercel setzen + neu deployen                                                                  |
| Dashboard zeigt Nullen ueberall                                     | Env Vars fehlen oder falsch             | Vercel -> Settings -> Environment Variables pruefen (GITHUB_TOKEN, DASHBOARD_PASSWORD, BREVO_API_KEY)        |
| Artikel werden nicht veroeffentlicht                                | Keine freigegebenen Entwuerfe           | Im Artikel-Tab pruefen und freigeben                                                                         |
| Artikel werden nicht veroeffentlicht                                | Cron-Job laeuft nicht                   | Vercel Dashboard -> Cron Jobs pruefen                                                                        |
| Artikel ist im Dashboard "veroeffentlicht" aber nicht auf der Seite | `meta.slug` fehlte in der JSON-Datei    | `python main.py --build-v2` ausfuehren — der Builder normalisiert fehlende Slugs automatisch seit April 2026 |
| Artikel hat kein Bild                                               | `UNSPLASH_API_KEY` fehlt in Vercel      | In Vercel setzen + neu deployen; dann Artikel im Dashboard neu generieren                                    |
| E-Mail kommt nicht (montags)                                        | `BREVO_API_KEY` fehlt als GitHub-Secret | GitHub -> Repo -> Settings -> Secrets and variables -> Actions -> `BREVO_API_KEY` setzen                     |
| Montags keine Artikel generiert                                     | GitHub-Actions-Cron nicht gelaufen      | GitHub -> Actions -> "Auto-Generate Articles" -> letzten Run pruefen; ggf. manuell "Run workflow"            |
| /admin zeigt 404                                                    | Deployment veraltet                     | Vercel manuell neu deployen                                                                                  |
| Thema wird nicht gespeichert                                        | GITHUB_TOKEN abgelaufen                 | Neuen Token setzen + neu deployen                                                                            |
| Newsletter-Versand schlaegt fehl                                    | BREVO_API_KEY fehlt in Vercel           | In Vercel setzen + neu deployen                                                                              |
| KI-Texte werden nicht poliert                                       | OPENAI_API_KEY fehlt in Vercel          | In Vercel setzen + neu deployen                                                                              |
| Bilder fehlen auf der Seite                                         | Bild nicht in `site-v2/images/`         | Bild ablegen + `python main.py --build-v2`                                                                   |
| Website nicht aktuell                                               | Build nicht gelaufen                    | Manuell: `python main.py --build-v2` + `git push`                                                            |
| GitHub Actions Build schlaegt fehl                                  | `OPENAI_API_KEY` Secret fehlt in GitHub | GitHub -> Repo -> Settings -> Secrets -> `OPENAI_API_KEY` setzen                                             |
| Sprachumschalter erscheint nicht                                    | Site-Rebuild nach feature-Commit fehlt  | `python main.py --build-v2` + `git push` ausfuehren                                                         |
| Uebersetzung schlaegt fehl (502)                                    | `DEEPL_API_KEY` fehlt oder ungueltig    | In Vercel setzen; Free-Key endet auf `:fx`                                                                   |
| Uebersetzung schlaegt fehl (502), DeepL war gesetzt                 | DeepL Free-Quota erschoepft (500k/Mon.) | `AZURE_TRANSLATOR_KEY` + `AZURE_TRANSLATOR_REGION` in Vercel setzen                                         |
| Uebersetzung liefert 429                                            | Rate-Limit (10 Anf./Stunde/IP)          | 1 Stunde warten; fuer internen Test VPN/anderen Rechner nutzen                                               |
| Uebersetzung liefert alten Stand                                    | localStorage-Cache (24h) veraltet       | Browser-DevTools -> Application -> LocalStorage -> `tr_slug_lang` Eintrag loeschen                          |
| Glossar-Import zeigt keine Duplikat-Warnungen                       | Batch-Groesse zu klein                  | Mindestens 5+ Eintraege importieren; Duplikate werden nur gegen bestehende Eintraege erkannt                 |

### 8.2 Notfall-Prozeduren

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

## 9. Ordnerstruktur

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
|   +-- generate_article.py     KI-Artikelgenerierung
|   +-- subscribe.py            Newsletter-Anmeldung
|   +-- admin_glossary.py       Glossar-Verwaltung (CRUD + Import/Review)
|   +-- translate.py            KI-Uebersetzung (DeepL + Azure Fallback)
+-- articles/
|   +-- translations/           Gecachte Uebersetzungen (auto-generiert)
|       +-- en/slug.json        Englische Uebersetzungen
|       +-- fr/ nl/ es/ ja/     Weitere Sprachen
+-- data/
|   +-- glossary/
|       +-- countries.json      Laender-Daten
|       +-- regions.json        Regionen
|       +-- distilleries.json   Destillerien
|       +-- whiskies.json       Abfuellungen
|       +-- review/queue.json   Import-Review-Queue
|       +-- imports/            Rohe Import-Batches + Reports
+-- site-v2/                Gebaute Website (von Vercel deployed)
|   +-- admin/index.html    Admin-Dashboard
|   +-- artikel/            Artikel-HTML-Seiten
|   +-- kategorie/          Kategorie-Seiten
|   +-- whisky-glossar/     Glossar-Seiten (Laender, Regionen, Destillerien)
|   +-- images/             Bilder
|   +-- style.css           Globales Stylesheet
+-- .github/workflows/
|   +-- build.yml           Auto-Rebuild bei Artikel-Aenderungen (aktiv)
|   +-- auto-generate.yml   Wochentliche Artikel-Generierung (Mo 07:00 CEST) + manueller Trigger
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

## 10. Checklisten

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

- [ ] **GitHub Token** pruefen -- laeuft er bald ab? -> Erneuern (siehe 7.2)
- [ ] **API-Keys** pruefen -- alle noch gueltig?
- [ ] **DeepL Quota** pruefen: https://www.deepl.com/pro-account -> Nutzung im laufenden Monat (Warnung: nahe 500.000 Zeichen -> Azure Key hinterlegen)
- [ ] Datenschutzerklaerung aktualisieren falls noetig (neue Partner, Tracker)
- [ ] Content-Strategie ueberpruefen: Welche Artikel performen gut? Welche Themen fehlen?
- [ ] Neue Themen in die Queue eintragen (Dashboard -> Themen -> Neues Thema)
- [ ] Defekte Links pruefen (z.B. mit einem Online Dead Link Checker)
- [ ] **SEO-Grundcheck**: `curl -s https://www.whisky-reise.com/sitemap.xml | grep -c "<url>"` -- Anzahl sollte den tatsaechlichen Artikel+Kategorie+Kern-Seiten entsprechen, keine Legal-Seiten enthalten. Ausserdem: Google Search Console -> Abdeckung -> auf "Ausgeschlossen" pruefen, ob noindex-Seiten (impressum, datenschutz, suche) korrekt herausgefiltert sind.

---

## 11. Karten-Pflege: Destillerien

Die interaktive Karte (`/karte`) zeigt Destillerien aus dem Glossar – mit visueller Unterscheidung zwischen **besuchten** und **noch nicht besuchten** Orten.

### Wie Destillerien auf die Karte kommen

Quelle ist ausschließlich `data/glossary/distilleries.json`. Nur Einträge mit `published: true` und gültigen `coordinates.lat/lng` erscheinen als Marker.

### Besucht-Status (automatisch)

Der Besucht-Status wird **automatisch beim Build** abgeleitet — kein manuelles Feld nötig:

1. **Artikel-Matching:** Wenn `article.locations[]` einen Eintrag enthält, der zum Destillerie-Namen passt (z. B. `"Lagavulin Distillery"` → Destillerie `"Lagavulin"`), gilt sie als besucht.
2. **GPS-Proximity:** Wenn ein GPS-Stop aus dem `scotland-archive/` innerhalb von 500 m liegt, werden Besuchsjahre und Fotos übernommen.

→ **Eine Destillerie erscheint als „besucht" (goldenes 🥃), sobald mindestens ein verlinkter Artikel oder ein GPS-Jahr vorhanden ist.**

### Neue Destillerie auf die Karte bringen

1. Im **Admin → Glossar → Destillerien** einen neuen Eintrag anlegen oder importieren.
2. **Pflichtfelder für Karte:** `coordinates.lat` + `coordinates.lng` als Dezimalzahlen (z. B. `57.123`, `-3.456`). Ohne Koordinaten ist der Eintrag im Glossar sichtbar, aber **nicht auf der Karte**.
3. Eintrag auf `published: true` setzen und freigeben.
4. Build auslösen → Destillerie erscheint als graues „Geplant"-🥃 auf der Karte.

### Koordinaten für viele Einträge auf einmal nachziehen

```bash
python scripts/backfill_distillery_coords.py
```

Das Skript fragt Nominatim (OpenStreetMap) für alle Einträge ohne Koordinaten an (1 req/sec). Nicht auflösbare Fälle werden in `scripts/backfill_unresolved.txt` gelistet und müssen manuell im Admin eingetragen werden.

### Karte nach Besuch aktualisieren

1. **Reisebericht** schreiben und unter `article.locations[]` die Destillerien-Namen eintragen (exakt, z. B. `"Ardbeg Distillery"`).
2. Artikel publizieren.
3. Nächster Build → Destillerie wechselt automatisch zu goldenem 🥃 (besucht).

### Kartenfilter (Benutzer-Sicht)

| Toggle | Standard | Bedeutung |
|--------|----------|-----------|
| 🥃 Besucht | ✅ an | Destillerien mit verlinkem Reisebericht |
| 🥃 Geplant | ☐ aus | Alle anderen Glossar-Destillerien |
| Sehenswürdigkeiten | ✅ an | POIs aus manual-locations.json |

### Popup-Inhalt

- **Besucht:** Name, Region, Gründungsjahr, Kurzbeschreibung, „✓ Besucht: YYYY", verlinkte Reiseberichte, Button „Im Glossar ansehen"
- **Geplant:** Name, Region, Gründungsjahr, Kurzbeschreibung, „⌖ Noch nicht besucht", Button „Im Glossar ansehen"

---

## 11. Schnellreferenz

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

| Datei                        | Zweck             | Wann anfassen                          |
| ---------------------------- | ----------------- | -------------------------------------- |
| `config.json`                | API-Keys, URLs    | Bei Key-Erneuerung oder Domain-Wechsel |
| `data/products.json`         | Amazon-Produkte   | Neue Produkte hinzufuegen              |
| `data/manual-locations.json` | Karteneintraege   | Neue Destillerien/POIs                 |
| `articles/*.json`            | Artikel-Inhalte   | Artikel manuell bearbeiten             |
| `site_builder_v2.py`         | Website-Generator | Bei Design/Layout-Aenderungen          |
| `vercel.json`                | Vercel-Config     | Bei Deployment-Aenderungen             |

---

## 12. Rechtliches (DSGVO / TMG)

### Pflichtseiten (alle vorhanden)

- **Impressum** (`/impressum.html`) -- Pflicht nach TMG Paragraph 5
- **Datenschutzerklaerung** (`/datenschutz.html`) -- Pflicht nach DSGVO
- **Cookie-Consent-Banner** -- Erscheint bei erstem Besuch

### Bei Aenderungen beachten

| Aenderung                 | Datenschutzerklaerung aktualisieren? | Impressum aktualisieren? |
| ------------------------- | ------------------------------------ | ------------------------ |
| Neuer Affiliate-Partner   | Ja                                   | Nein                     |
| Neues Analytics-Tool      | Ja + Cookie-Banner                   | Nein                     |
| Neuer Newsletter-Anbieter | Ja                                   | Nein                     |
| Umzug / neue Adresse      | Nein                                 | Ja                       |
| Neuer Hoster              | Ja                                   | Nein                     |

### Newsletter (Double Opt-In)

Der Newsletter nutzt DSGVO-konformes Double Opt-In:

1. Nutzer traegt E-Mail auf der Website ein
2. Brevo sendet Bestaetigungs-E-Mail (Template ID 1)
3. Erst nach Klick auf Bestaetigungslink wird der Kontakt aktiv
4. Abmeldelink in jeder Newsletter-E-Mail (automatisch von Brevo)

---

## 12. Beta-Tester-Kampagne: Landingpage, Fragebogen & Verlosung

Stand: April 2026

### Uebersicht

Fuer den Launch wurde eine Beta-Tester-Kampagne aufgebaut, die per WhatsApp an Freunde und Bekannte verschickt wird. Ziel: ehrliches Erstnutzer-Feedback sammeln und gleichzeitig Newsletter-Abonnenten gewinnen.

### Dateien

| Datei | Zweck |
| --- | --- |
| `site-v2/umfrage.html` | Landingpage (WhatsApp-Link, Verlosung, CTA) |
| `site-v2/fragebogen.html` | Fragebogen (10 Fragen + Name/E-Mail + Newsletter-Opt-in) |
| `site-v2/danke-feedback.html` | Danke-Seite nach dem Absenden |

### URLs

| Was | URL |
| --- | --- |
| Landingpage | https://www.whisky-reise.com/umfrage.html |
| Fragebogen | https://www.whisky-reise.com/fragebogen.html |
| Danke-Seite | https://www.whisky-reise.com/danke-feedback.html |

### Workflow fuer den Nutzer

1. WhatsApp-Nachricht mit dem Link zu `/umfrage.html` verschicken
2. Nutzer sieht Landingpage mit Verlosungs-Infos und klickt "Jetzt Feedback geben"
3. Nutzer fuellt 10 Fragen aus, gibt Name + E-Mail ein, kann Newsletter-Opt-in auswaehlen
4. Formular wird an Formspree gesendet, Nutzer landet auf `/danke-feedback.html`
5. Steffen und Elmar werten Antworten im Formspree-Dashboard aus

### WhatsApp-Nachricht (Template zum Kopieren)

```
Hey [Name]!

Ich baue gerade ein Whisky-Magazin und wuerde mich riesig ueber dein
ehrliches Feedback freuen - auch wenn du kein Whisky-Experte bist.

Dauert nur 3 Minuten - und du kannst ein persoenliches Whisky-Tasting
mit uns gewinnen!

https://www.whisky-reise.com/umfrage.html

Danke!!
```

### Formspree (Antworten auswerten)

| Aktion | Wo |
| --- | --- |
| Dashboard aufrufen | https://formspree.io -> einloggen |
| Einzelne Antworten lesen | Dashboard -> Formular "myklpaqy" -> Submissions |
| Alle Antworten exportieren | Dashboard -> Export -> CSV herunterladen -> in Excel/Google Sheets oeffnen |
| E-Mail-Benachrichtigung | Kommt automatisch nach jeder neuen Einsendung |

**Formspree-Endpunkt:** `https://formspree.io/f/myklpaqy`

**Kostenloses Kontingent:** 50 Einsendungen/Monat. Fuer mehr: Upgrade auf Formspree Basic (8 USD/Monat).

### Verlosung auswerten

Die Gewinner werden manuell aus den Formspree-Antworten ausgewaehlt. Kriterien:
- Qualitaet und Ausfuehrlichkeit des Freitextfeldes (Frage 4: vermisste Themen)
- Hinweise auf konkrete Verbesserungen
- Allgemeine Nuetzlichkeit des Feedbacks

Vorgehen:
1. CSV-Export aus Formspree herunterladen
2. In Google Sheets importieren
3. Freitextantworten manuell lesen und Top 3 bestimmen
4. Gewinner per E-Mail benachrichtigen (Adresse ist in den Formulardaten)

### Newsletter-Opt-in aus dem Fragebogen

Wenn der Nutzer die Checkbox "Monatlichen Newsletter erhalten" angehaekt laesst (Standard: angehaekt), erscheint im Formspree-Eintrag das Feld `newsletter: Ja`.

Diese E-Mail-Adressen muessen manuell in Brevo importiert werden:
1. CSV-Export aus Formspree
2. Spalten filtern: nur Zeilen wo `newsletter = Ja`
3. E-Mail-Adressen + Namen in Brevo importieren (Kontakte -> Importieren)
4. Liste: "Beta-Tester-Newsletter" (oder bestehende Hauptliste)

### Foto auf der Landingpage aendern

Das Eyecatcher-Foto auf `/umfrage.html` und `/fragebogen.html` liegt unter:

```
site-v2/images/authors-steffen-elmar.jpg
```

Um ein neues Foto zu verwenden:
1. Neues Foto als `authors-steffen-elmar.jpg` speichern (ueberschreibt das alte)
2. Empfohlene Groesse: mindestens 400x400px, quadratisches Format
3. `git add site-v2/images/authors-steffen-elmar.jpg` -> commit -> push

### Design-Details

Das Design der Landingpage und des Fragebogens folgt dem Standard-Brand:
- **Farben:** Amber `#C8963E`, Cream `#FAFAF7`, Dark `#1A1A1A`
- **Schriften:** Fraunces (Headings), Inter (Body)
- **Stylesheet:** `/style.css` (gemeinsam mit dem Rest der Website)
- **OG-Tags:** Optimiert fuer WhatsApp-Link-Preview (Titel, Beschreibung, Foto)
