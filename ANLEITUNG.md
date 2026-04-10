# Betriebsanleitung — Whisky Magazin (whisky-reise.com)

Stand: April 2026

---

## Übersicht

Das Whisky Magazin läuft vollautomatisch:
- **Jeden Montag 07:00 Uhr** generiert ein Windows-Task 2 neue Artikel-Entwürfe
- Die Entwürfe landen im Admin-Dashboard zur Prüfung/Freigabe
- **Mittwoch + Samstag 10:00 Uhr CEST** veröffentlicht Vercel freigegebene Artikel automatisch
- Bei jeder Generierung kommt eine E-Mail an **rosenhefter@gmail.com**

---

## Admin-Dashboard

**URL:** https://www.whisky-reise.com/admin

Login: Passwort aus Vercel → Settings → Environment Variables → `DASHBOARD_PASSWORD`

### Tabs

| Tab | Funktion |
|---|---|
| Übersicht | 4 Kennzahlen (Abonnenten, Entwürfe, Themen offen/erledigt) — klickbar |
| Newsletter | Brevo-Abonnenten-Liste |
| Artikel | Entwürfe verwalten (Bearbeiten / Freigeben / Ablehnen) |
| Themen | Themen-Queue für den Generator |

### Artikel-Workflow

1. Montags: Windows-Scheduler generiert 2 Artikel → erscheinen im "Artikel"-Tab als **Ausstehend**
2. Du prüfst, bearbeitest (Titel/Teaser/Inhalt) oder gibst frei
3. Status **Freigegeben** → wird beim nächsten Vercel-Cron veröffentlicht (Mi/Sa 10:00)
4. Der GitHub Actions-Workflow baut die Website neu und Vercel deployed automatisch

### Themen verwalten

- 50 vorbereitete Themen (Frühling/Sommer/Herbst/Winter/Ostern/Weihnachten/Silvester)
- **Filter**: nach Saison und Status filtern
- **Neues Thema**: Button oben rechts → Titel eingeben → Speichern
- **Erledigt markieren**: wenn ein Artikel zum Thema veröffentlicht wurde
- **Löschen**: Papierkorb-Icon

---

## Automatische Generierung

### Windows Task Scheduler (lokal)

- **Task-Name:** `WhiskyMagazin-AutoGenerate`
- **Zeitplan:** Jeden Montag 07:00 Uhr
- **Befehl:** `python main.py --auto -n 2`
- **Log:** `magazin.log` im Projektordner

#### Manuell ausführen (z.B. für Tests):
```
cd "C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin"
python main.py --auto -n 3
```

Das erstellt Entwürfe, pusht zu GitHub und schickt eine E-Mail.

### Vercel Cron-Jobs (automatische Veröffentlichung)

Konfiguriert in `vercel.json`:
- **Mittwoch** 08:00 UTC (= 10:00 CEST): `/api/admin_publish`
- **Samstag** 08:00 UTC (= 10:00 CEST): `/api/admin_publish`

Der Cron nimmt den ältesten **freigegebenen** Entwurf und veröffentlicht ihn.

---

## E-Mail-Benachrichtigung

Jedes Mal wenn `python main.py --auto` läuft:
- Brevo Transactional API sendet HTML-E-Mail an `rosenhefter@gmail.com`
- Betreff: "Neue Whisky-Artikel bereit zur Freigabe"
- Inhalt: Titel + Kategorie + Wortanzahl + Link zum Dashboard
- Konfiguration: `.env` Datei im Projektordner (`BREVO_API_KEY=...`)

---

## Vercel-Konfiguration

Projekt: `derhefter/whisky-magazin-v2` auf GitHub
Production Branch: `main`

### Erforderliche Environment Variables (Vercel → Settings → Environment Variables):

| Variable | Beschreibung |
|---|---|
| `DASHBOARD_PASSWORD` | Login-Passwort für /admin |
| `GITHUB_TOKEN` | Fine-grained PAT mit `read+write` auf das Repo |
| `GITHUB_REPO` | `derhefter/whisky-magazin-v2` |
| `GITHUB_BRANCH` | `main` (Standard, muss nicht gesetzt werden) |
| `BREVO_API_KEY` | Für Newsletter-Statistiken im Dashboard |
| `BREVO_LIST_ID` | Brevo-Listen-ID (z.B. `3`) |

**Wichtig:** Nach jeder Änderung an Env Vars → Vercel neu deployen!

---

## Lokale Entwicklung

```bash
cd "C:\Users\steff\Documents lokal\Business-Ideen\Whisky_Ideen\whisky-magazin"

# Artikel manuell generieren (als Entwurf)
python main.py --auto -n 1

# Website lokal bauen
python main.py --build-v2

# Lokalen Webserver starten
python main.py --serve-v2

# Verbindung testen
python main.py --test
```

---

## Ordnerstruktur

```
whisky-magazin/
├── articles/               veröffentlichte Artikel (JSON)
│   └── drafts/             Entwürfe (vom Dashboard verwaltet)
├── data/
│   └── topics_queue.json   Themen-Queue für Generator
├── api/                    Vercel Serverless Functions
│   ├── admin_auth.py           Login/Token
│   ├── admin_data.py           Dashboard-Daten
│   ├── admin_articles.py       Artikel bearbeiten/freigeben/ablehnen
│   ├── admin_topics.py         Themen-Queue verwalten
│   ├── admin_publish.py        Vercel Cron: Artikel veröffentlichen
│   └── subscribe.py            Newsletter-Anmeldung
├── site-v2/                gebaute Website (von Vercel deployed)
│   └── admin/index.html    Admin-Dashboard
├── main.py                 Hauptskript (Generator + Builder)
├── content_generator.py    GPT-4o Artikel-Generator
├── notifier.py             E-Mail (Brevo Transactional API)
├── site_builder_v2.py      statischer Site-Builder
├── vercel.json             Vercel-Konfiguration (Crons, Routing)
└── config.json             OpenAI API Key + Konfiguration
```

---

## Häufige Probleme

| Problem | Ursache | Lösung |
|---|---|---|
| Dashboard zeigt Nullen | GITHUB_TOKEN abgelaufen | Neuen Token in Vercel setzen + neu deployen |
| Artikel-Aktionen ohne Reaktion | Vercel auf falscher Branch | Vercel → Settings → Git → `main` als Production Branch |
| E-Mail kommt nicht | `.env` fehlt | `.env` Datei prüfen: `BREVO_API_KEY=xkeysib-...` |
| /admin zeigt 404 | Deployment veraltet | Vercel manuell neu deployen |
| Thema wird nicht gespeichert | GITHUB_TOKEN abgelaufen | Neuen Token setzen + neu deployen |

---

## GitHub Actions

`.github/workflows/build.yml` läuft automatisch wenn:
- Dateien in `articles/*.json` geändert werden (neue veröffentlichte Artikel)
- `data/topics_queue.json` geändert wird

Dann: `site_builder_v2.py` baut `site-v2/` neu → Vercel deployed automatisch.
