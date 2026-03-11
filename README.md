# 🥃 Whisky Magazin

**Automatischer Website-Generator mit KI-Content-Pipeline**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-whisky--magazin.vercel.app-blue)](https://whisky-magazin.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)](https://www.python.org/)
[![Deploy](https://img.shields.io/badge/Hosting-Vercel-black)](https://vercel.com)

Ein vollautomatisches System, das KI-generierte Blog-Artikel zu den Themen Whisky und Reisen erstellt und daraus eine komplette, fertige statische Website baut – kein WordPress, kein Server-Wissen nötig.

---

## 🚀 Live-Demo

👉 **[whisky-magazin.vercel.app](https://whisky-magazin.vercel.app)**

---

## ✨ Features

- **KI-generierte Artikel** via OpenAI GPT-4o (1.200–2.500 Wörter, SEO-optimiert)
- **Automatische Affiliate-Links** (Amazon, Tradedoubler)
- **Statische HTML-Website** – blitzschnell, kein Backend
- **73 vorbereitete Themen** für ca. 6 Monate Content
- **Kategorie-Seiten** (Whisky, Reise, Lifestyle, Natur, Urlaub)
- **Sitemap** für Google-Indexierung
- **Lokaler Webserver** zur Vorschau
- **Einfache Windows-Batch-Dateien** zum Starten

---

## ⚡ Quick Start

### Voraussetzungen

- Python **3.9 oder höher** ([Download](https://www.python.org/downloads/))
- OpenAI API-Key ([Hier erstellen](https://platform.openai.com/api-keys))
- Git (optional)

### Installation

```bash
# 1. Repository klonen
git clone https://github.com/derhefter/whisky-magazin.git
cd whisky-magazin

# 2. Setup ausführen (erstellt venv + installiert Pakete)
setup.bat

# 3. Konfiguration anlegen
copy config.example.json config.json
# Öffne config.json und trage deinen OpenAI API-Key ein

# 4. Starten
starten.bat
```

---

## 🖥️ Verwendung

### Interaktives Menü (empfohlen)

```bash
python main.py
```

### Kommandozeile

```bash
python main.py --generate        # 1 Artikel generieren
python main.py --generate -n 3  # 3 Artikel generieren
python main.py --build           # Website neu bauen
python main.py --auto -n 3       # Artikel generieren + Website bauen
python main.py --serve           # Lokalen Webserver starten (localhost:8080)
python main.py --stats           # Statistiken anzeigen
python main.py --test            # OpenAI-Verbindung testen
```

---

## 📁 Projektstruktur

```
whisky-magazin/
├── main.py               # Hauptprogramm & CLI
├── content_generator.py  # KI-Artikelgenerierung (OpenAI)
├── site_builder.py       # Statischer Website-Generator
├── topic_library.py      # 73 Themenvorschläge
├── config.example.json   # Konfigurationsvorlage
├── requirements.txt      # Python-Abhängigkeiten
├── setup.bat             # Windows-Setup (einmalig)
├── starten.bat           # Windows-Starter
├── vercel.json           # Vercel-Deployment-Konfiguration
├── articles/             # Generierte Artikel (JSON)
└── site/                 # Fertige Website (HTML)
    ├── index.html
    ├── artikel/
    ├── kategorie/
    └── sitemap.xml
```

---

## ⚙️ Konfiguration (`config.json`)

| Einstellung | Beschreibung | Standard |
|---|---|---|
| `openai.api_key` | Dein OpenAI API-Key | – |
| `openai.model` | KI-Modell | `gpt-4o` |
| `openai.temperature` | Kreativität (0.0–1.0) | `0.7` |
| `site.name` | Name der Website | `Whisky Magazin` |
| `site.base_url` | URL für Online-Hosting | `""` |
| `min_word_count` | Mindestwörter pro Artikel | `1200` |
| `max_word_count` | Maximalwörter pro Artikel | `2500` |

> **Wichtig:** Trage nach dem Deployment die echte URL als `base_url` ein und baue die Website neu mit `python main.py --build`.

---

## 💰 Kosten

| Posten | Kosten |
|---|---|
| OpenAI API (12 Artikel/Monat) | ca. 1–2 EUR/Monat |
| Hosting (Vercel/Netlify/GitHub Pages) | kostenlos |
| Domain (optional) | ca. 10 EUR/Jahr |

---

## 📖 Ausführliche Anleitung

Die vollständige Dokumentation (Hosting-Optionen, FAQ, Einnahmen-Übersicht) findest du in der **[ANLEITUNG.md](./ANLEITUNG.md)**.

---

## 🛠️ Tech Stack

- **Python 3.9+** – Backend-Logik & Content-Generierung
- **OpenAI API** – KI-Artikelgenerierung (GPT-4o)
- **HTML/CSS** – Statische Website-Ausgabe
- **Vercel** – Hosting & Deployment

---

## 📄 Lizenz

Dieses Projekt ist für den privaten Gebrauch. Alle generierten Inhalte unterliegen den Nutzungsbedingungen der OpenAI API.
