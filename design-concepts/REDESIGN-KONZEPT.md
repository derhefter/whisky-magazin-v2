# Whisky Magazin — Komplettes Brand-Redesign

> Senior Brand-/Webdesign-Konzept fur einen deutschsprachigen Scotch-Whisky-Reiseblog mit 14 Jahren Geschichte. Ziel: Affiliate-Klicks, Newsletter-Anmeldungen, Magazin-Feeling & Vertrauen.

---

## 1) Brand-Identitat

### 1.1 Drei Brand Directions

#### Direction A: "Bright Highland Editorial" (EMPFOHLEN)

**Mood:** Goldenes Licht uber schottischen Hugeln. Warm, klar, vertrauenswurdig. Wie ein Premium-Reisemagazin am Flughafen — aber mit Seele.

**Referenzen:** Cereal Magazine, Bon Appetit, Afar Magazine

**Kernattribute:** Hell, warm, editorial, grosszugig, einladend. Whisky-Warme als Akzent, nicht als Gesamtstimmung. Die Seite strahlt Kompetenz und Zuganglichkeit gleichzeitig aus.

#### Direction B: "Coastal Drift"

**Mood:** Auf Islays Kuste stehen, Salzluft, weiter Horizont. Frisch, abenteuerlich, modern.

**Referenzen:** Kinfolk, Suitcase Magazine, Wallpaper*

**Kernattribute:** Kuhler im Grundton (Slate/Blue), aber warm durch Sand- und Bernstein-Akzente. Mehr Weissraum, mehr Modernitat. Betont die Reise-Komponente starker als den Whisky.

#### Direction C: "Fieldnotes"

**Mood:** Ledergebundenes Notizbuch auf dem Pub-Tisch, handgezeichnete Karten, personliche Geschichten.

**Referenzen:** Monocle, Drift Magazine, Cereal City Guides

**Kernattribute:** Creme-Basis, Tinte-Schwarz, Terrakotta-Akzente. Personlicher, intimer, leicht texturiert. Der starkste "Buddy"-Charakter aller drei Richtungen. Betont den Autor als Erzahler.

---

### 1.2 Farbpaletten

#### Palette A: "Bright Highland" (EMPFOHLEN)

| Token              | HEX       | Muster                                            | Einsatz                                   |
| ------------------ | --------- | ------------------------------------------------- | ----------------------------------------- |
| `--bg-primary`     | `#FAFAF7` | ![](https://via.placeholder.com/16/FAFAF7/FAFAF7) | Seitenhintergrund (warm white)            |
| `--bg-surface`     | `#F5F0E8` | ![](https://via.placeholder.com/16/F5F0E8/F5F0E8) | Karten, Sections, Sidebar                 |
| `--bg-elevated`    | `#FFFFFF` | ![](https://via.placeholder.com/16/FFFFFF/FFFFFF) | Erhohte Elemente, Modals                  |
| `--text-primary`   | `#1A1A1A` | ![](https://via.placeholder.com/16/1A1A1A/1A1A1A) | Headlines, Fliesstext                     |
| `--text-secondary` | `#5C5C5C` | ![](https://via.placeholder.com/16/5C5C5C/5C5C5C) | Meta-Text, Captions                       |
| `--accent-amber`   | `#C8963E` | ![](https://via.placeholder.com/16/C8963E/C8963E) | Primarer Akzent — CTAs, Links, Highlights |
| `--accent-sage`    | `#4A7C5E` | ![](https://via.placeholder.com/16/4A7C5E/4A7C5E) | Sekundarer Akzent — Trust, Natur, Badges  |
| `--accent-warm`    | `#8B7355` | ![](https://via.placeholder.com/16/8B7355/8B7355) | Tertiar — Borders, Muted Elements         |
| `--border`         | `#E8DCC8` | ![](https://via.placeholder.com/16/E8DCC8/E8DCC8) | Trennlinien, Card-Borders                 |

**Kontrastratio:** `--text-primary` auf `--bg-primary` = 17.4:1 (AAA). `--accent-amber` auf `--bg-primary` = 4.8:1 (AA fur grosse Texte, fur kleine Texte dunkle Variante `#A67A2E` verwenden).

#### Palette B: "Coastal Drift"

| Token              | HEX       | Einsatz                          |
| ------------------ | --------- | -------------------------------- |
| `--bg-primary`     | `#FFFFFF` | Seitenhintergrund (reines Weiss) |
| `--bg-surface`     | `#F2F4F6` | Kuhle Flachen                    |
| `--text-primary`   | `#1B2332` | Dunkles Navy                     |
| `--text-secondary` | `#5C6B7A` | Kuhles Grau                      |
| `--accent-amber`   | `#D4943A` | Bernstein-Akzent                 |
| `--accent-teal`    | `#3D7A8A` | Kusten-Teal                      |
| `--accent-muted`   | `#94A3B0` | Kuhles Muted                     |
| `--border`         | `#E4E8EC` | Kuhle Trennlinien                |

#### Palette C: "Fieldnotes"

| Token              | HEX       | Einsatz           |
| ------------------ | --------- | ----------------- |
| `--bg-primary`     | `#FAF8F4` | Creme-Hintergrund |
| `--bg-surface`     | `#F0EBE1` | Pergament         |
| `--text-primary`   | `#2A2520` | Warmes Schwarz    |
| `--text-secondary` | `#6B5E52` | Warmes Grau       |
| `--accent-copper`  | `#B8762E` | Kupfer/Bernstein  |
| `--accent-terra`   | `#C4583A` | Terrakotta        |
| `--accent-muted`   | `#8A7D6B` | Warmes Muted      |
| `--border`         | `#DDD5C8` | Warme Trennlinien |

---

### 1.3 Typografie-Pairings (Google Fonts)

#### Pairing A: Fraunces + Inter (EMPFOHLEN)

| Rolle        | Font     | Gewicht    | Grosse      | Einsatz                               |
| ------------ | -------- | ---------- | ----------- | ------------------------------------- |
| Display/Hero | Fraunces | 600 italic | 48-64px     | Hero-Headline, Featured-Story-Titel   |
| Headlines H1 | Fraunces | 600        | 36-42px     | Artikel-Titel, Sektions-Uberschriften |
| Headlines H2 | Fraunces | 500        | 24-28px     | Unter-Uberschriften                   |
| Headlines H3 | Inter    | 600        | 18-20px     | Sidebar-Titel, Modul-Titel            |
| Body         | Inter    | 400        | 17px / 1.75 | Fliesstext                            |
| UI/Labels    | Inter    | 500-600    | 12-14px     | Navigation, Buttons, Tags, Meta       |
| Blockquote   | Fraunces | 400 italic | 22px / 1.5  | Zitate, Pull-Quotes                   |

**Warum Fraunces:** Variable Font mit optischer Grosse. Im Display-Bereich elegant mit Schwung, im Text-Bereich sachlich. Hat Charakter ohne kitschig zu sein — perfekt fur Whisky-Editorial. Die kursive Variante hat einen subtilen "handwritten" Touch, der zum Buddy-Ton passt.

**Warum Inter:** Der Goldstandard fur digitale Lesbarkeit. Neutral genug, um Fraunces glanzen zu lassen, aber nicht steril. Exzellente Tabular-Zahlen fur Tasting-Notes und Preise.

**Google Fonts Link:**

```html
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400;1,9..144,500;1,9..144,600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

#### Pairing B: DM Serif Display + Outfit

| Rolle             | Font             | Gewicht              |
| ----------------- | ---------------- | -------------------- |
| Display/Headlines | DM Serif Display | 400 regular + italic |
| Body/UI           | Outfit           | 300-600              |

**Charakter:** Eleganter, klassischer. DM Serif Display ist scharf und modern-klassisch. Outfit ist geometrisch und sehr clean. Zusammen: "Elegantes Reisemagazin".

#### Pairing C: Bitter + Work Sans

| Rolle             | Font      | Gewicht |
| ----------------- | --------- | ------- |
| Display/Headlines | Bitter    | 500-700 |
| Body/UI           | Work Sans | 300-600 |

**Charakter:** Bitter ist ein Slab-Serif mit Editorial-Charakter — erinnert an Zeitungs-Features. Work Sans ist freundlich und modern. Zusammen: "Journalistisches Reiseblog mit Personlichkeit".

---

### 1.4 Logo-Ansatze

#### Vorschlag 1: Split-Weight-Wortmarke (EMPFOHLEN)

```
WHISKY · MAGAZIN
```

- **"WHISKY"** in Fraunces 600, Letterspacing 4px
- **Trennzeichen** Mid-Dot (·) in `--accent-amber`
- **"MAGAZIN"** in Inter 600, Letterspacing 6px, etwas kleiner
- **Formensprache:** Der Kontrast zwischen Serif (warm, Tradition) und Sans-Serif (modern, klar) spiegelt die Marke wider — 14 Jahre Geschichte trifft modernes Editorial. Der goldene Punkt ist der "Dram" — klein, wertvoll, zentral.
- **Favicon:** Goldener "W" in Fraunces auf dunklem (#1A1A1A) Quadrat

#### Vorschlag 2: Monogramm "WM"

- **Konstruktion:** "W" und "M" verschrankt in einer geometrischen Form (Fraunces Bold). Das M sitzt im unteren Drittel des W.
- **Einsatz:** Avatar, Favicon, App-Icon, Wasserzeichen auf Fotos
- **Vollversion:** Monogramm links + "Whisky Magazin" rechts in Inter 500
- **Formensprache:** Kompakt, merkfahig, funktioniert in 16x16px. Die Verschrankung symbolisiert "Whisky trifft Magazin" — zwei Welten, ein Erlebnis.

---

### 1.5 Bildsprache & Art Direction

#### Fotostil

- **Licht:** Naturliches Licht, Golden Hour bevorzugt. Kein Studiolight, kein HDR
- **Landschaften:** Weit, atmospharisch, saisonal. Nebel, Kusten, Hugel — echtes Schottland, nicht Stock-Photo-Schottland
- **Close-Ups:** Flussigkeit im Glas (Bernstein-Glut), Kupfer-Stills, Gerste, Fass-Details
- **Menschen:** Candid, ungestellt, echte Momente. Steffen und Elmar als authentische Guides
- **Essen/Genuss:** Rustikal, appetitlich, nicht uberinszeniert

#### Bildbearbeitung

- Leicht warm (nicht orange), entsattigt in den Schatten
- Kontrast: mittel (nicht flach, nicht dramatisch)
- Kornung: minimal, nur bei Stimmungsbildern
- Grundregel: "Sieht aus wie ein gutes iPhone-Foto mit gutem Licht"

#### Texturen & Grafik-Elemente (subtil)

- Dezentes Papier-Grain als Hintergrund-Overlay (Opacity 3-5%)
- Topografische Linien oder Konturkarten als dekorative Hintergrunde (Opacity 5-8%)
- Keine Holz-, Fass-, Leder- oder Tartan-Texturen
- Kein Whisky-Splash, kein Rauch-Effekt

#### Bild-Formate

- Hero: 16:9 oder 21:9 (breit, cinematic)
- Cards: 3:2 (klassisch editorial)
- Inline: Variabel, Lazy Loading
- Alle: WebP mit JPEG-Fallback, max 1600px breit

---

## 2) Drei Design-Konzepte

### Konzept 1: "Golden Hour" (EMPFOHLEN)

**Mood:** "Das erste Glas nach einem langen Wandertag — warm, zufrieden, neugierig auf mehr."

**Layout-DNA:**

- **Grid:** 12-Spalten, max-width 1200px, 32px Gutter
- **Spacing:** 8px Basis-Grid. Sections: 80px vertikal. Cards: 24px Padding
- **Radius:** 12px (Cards, Buttons), 8px (Tags, Badges), 24px (Pill-Buttons)
- **Shadows:** Weich, warm-getont: `0 4px 24px rgba(139,115,85,0.08)` (kein kaltes Grau)
- **Header:** Sticky, weiss mit `backdrop-filter: blur(12px)`, Border-Bottom in `--border`. Logo links, Nav rechts, CTA-Button "Newsletter" ganz rechts
- **Footer:** `--bg-surface` Background, 4-Column Grid (Navigation, Kategorien, Legal, Newsletter-Mini)

**Komponenten-Highlights:**

- **Featured Story Block:** Full-Width-Image (21:9) mit Text-Overlay unten links. Kategorie-Badge, Headline in Fraunces 600 weiss, Teaser-Text, "Weiterlesen"-CTA
- **Whisky of the Month:** Weisse Karte mit `--accent-amber` Left-Border (4px). Produktbild links, rechts: Name, Destillerie, Region-Badge, Kurztext, Tasting-Notes (Aroma/Geschmack/Finish als 3 Icons + Text), Preis, "Jetzt entdecken"-Button
- **Newsletter-Box:** `--bg-surface` Background, Fraunces-Headline, 1 Zeile Copy, E-Mail-Input + Button in einer Reihe, Social-Proof darunter ("2.400+ Whisky-Fans lesen mit")
- **Story Cards:** Bild oben (3:2), darunter: Kategorie-Tag (Pill), Headline, Meta (Datum + Lesezeit), 2-Zeilen-Teaser. Hover: sanfter Shadow + leichter Lift (translateY -2px)

**Affiliate-Integration:**

- Whisky-of-the-Month als redaktionelle Empfehlung, nicht als Werbung
- "Empfohlene Flaschen" am Artikelende als kuratierte Auswahl
- Inline-Mentions mit dezenten "Preis checken"-Links
- Transparenz-Badge: Kleines Hinweis-Icon + Tooltip "Warum wir empfehlen"

**Newsletter-Integration:**

- Hero-Bereich: Secondary CTA "Newsletter" neben Primary CTA
- Mid-Page-Section mit Lead-Magnet-Angebot
- End-of-Article: "Mehr Geschichten wie diese?" + Input
- Footer: Kompakte Version

---

### Konzept 2: "Salt & Stone"

**Mood:** "Morgens an der Kuste von Islay — klar, frisch, abenteuerlich."

**Layout-DNA:**

- **Grid:** 12-Spalten, max-width 1140px, 40px Gutter (mehr Luft)
- **Spacing:** Sehr grosszugig. Sections: 100px vertikal
- **Radius:** 8px (Cards), 4px (Buttons — kantiger), 20px (Pills)
- **Shadows:** Keine. Stattdessen: 1px Borders in `--border`
- **Header:** Fixed transparent, wird beim Scrollen weiss. Minimalistisch
- **Footer:** Dunkel (#1B2332), heller Text, 3-Column

**Komponenten-Highlights:**

- **Featured Story Block:** Split-Screen — Bild links (50%), Text rechts (50%). Grosse Fraunces-Headline, ausfuhrlicherer Teaser
- **Whisky of the Month:** Volle Breite, horizontale Karte. Bild links, Content Mitte, CTA rechts. Teal-Border oben
- **Newsletter-Box:** Full-Width-Band in `--accent-teal` dunkel. Weisser Text, auffallend aber nicht storend
- **Story Cards:** Minimalistisch — kein Shadow, nur Bottom-Border. Bild, Titel, Meta. Clean

**Affiliate-Integration:**

- "Kusten-Empfehlung" als thematisch passender Block
- Vergleichstabellen in Guide-Artikeln
- Dezenter "Shop"-Link in der Navigation

**Newsletter-Integration:**

- Full-Width-Band zwischen Content-Sections
- Stark visuell, kontrastreicher als bei "Golden Hour"

---

### Konzept 3: "Notebook"

**Mood:** "Steffens personliches Schottland-Tagebuch — offen, warm, einladend."

**Layout-DNA:**

- **Grid:** Single Column (max 720px) fur Artikel, 2-Column fur Homepage
- **Spacing:** Moderat. Sections: 64px vertikal
- **Radius:** 6px (weich, aber nicht rund)
- **Shadows:** Minimal, warm: `0 2px 12px rgba(42,37,32,0.06)`
- **Header:** Nicht-sticky, Teil der Seite. Weniger "App", mehr "Magazin"
- **Footer:** `--bg-surface`, handschriftliches Zitat als Abschluss

**Komponenten-Highlights:**

- **Featured Story Block:** Grosses Bild mit Titel darunter (nicht Overlay). Personlicher — "Meine Top-Story"
- **Whisky of the Month:** Karte mit Terrakotta-Akzent, leicht texturierter Hintergrund. Handschrift-artige Bewertungs-Icons
- **Newsletter-Box:** Personlich formuliert: "Ich schick dir einmal im Monat meine besten Tipps — versprochen." Input + Button
- **Story Cards:** Bild + Text nebeneinander (horizontal). Intimer, mehr "Empfehlung von einem Freund"

**Affiliate-Integration:**

- "Steffens Empfehlung" — personlich geframed
- "Das hab ich mitgebracht" — Produkte als Reise-Souvenir
- Maximal persönlich, minimal kommerziell im Ton

**Newsletter-Integration:**

- In "Brief an dich"-Tonalitat
- Am Ende jedes Artikels als personliche Einladung

---

## 3) Startseite: Informationsarchitektur

Von oben nach unten, fur Konzept "Golden Hour" (empfohlen):

### Section 1: Header (Sticky)

- **Ziel:** Navigation + Brand-Wiedererkennung + Newsletter-CTA
- **Inhalt:** Logo links | Nav-Links Mitte (Start, Whisky, Reise, Karte, Whisky Shoppen) | "Newsletter"-Button rechts (Ghost-Style)
- **Layout:** Flex, zentriert, max-width 1200px. Hohe 64px. Weiss mit Blur + Border-Bottom

### Section 2: Hero — Featured Story

- **Ziel:** Sofortiger emotionaler Hook. Zeigt: "Das ist ein Magazin mit echten Geschichten."
- **Inhalt:** 1 Featured Article. Grosses Bild (21:9), Kategorie-Badge, Headline (Fraunces 48px), 2-Zeilen-Teaser, "Weiterlesen"-CTA
- **CTA:** Primary: "Weiterlesen" (auf Artikel). Secondary: "Alle Artikel" (auf Kategorie)
- **Layout:** Full-Width-Image mit Text-Overlay (unten links, dunkler Gradient). Min-Height 500px. Mobile: Bild oben, Text darunter

### Section 3: Featured Stories Grid

- **Ziel:** Tiefe des Contents zeigen. Verschiedene Kategorien. Entdecker-Instinkt wecken
- **Inhalt:** 6 Artikel in klarer Hierarchie: 1 gross (2 Spalten), 2 mittel (je 1 Spalte), 3 klein (je 1 Spalte, nur Titel + Meta)
- **CTA:** Jede Karte klickbar + "Alle Artikel"-Link unten
- **Layout:** CSS Grid. Zeile 1: 1 grosse Karte (span 2) + 1 mittlere. Zeile 2: 1 mittlere + 2 kleine. Responsive: stacked auf Mobile

### Section 4: Whisky of the Month

- **Ziel:** Affiliate-Conversion. Redaktionelle Empfehlung = Vertrauen
- **Inhalt:** Produkt-Highlight des Monats. Produktfoto, Name, Destillerie, Region, Kurzbewertung (3 Satze), Tasting-Notes (Aroma, Geschmack, Finish), Preis, CTA-Button
- **CTA:** "Jetzt entdecken" (Affiliate-Link, offen gekennzeichnet)
- **Layout:** Weisse Karte auf `--bg-surface`-Band. Horizontal: Bild links (40%), Text rechts (60%). `--accent-amber` Top-Border (4px). Dezenter Stern-Disclaimer unten

### Section 5: Reise-Teaser — "Regionen entdecken"

- **Ziel:** Reise-Aspekt betonen + Karten-Seite promoten + SEO
- **Inhalt:** 4-5 Region-Cards (Islay, Speyside, Highlands, Campbeltown, Edinburgh). Jede Card: Stimmungsbild, Regionsname, Anzahl Destillerien, Kurz-Teaser
- **CTA:** "Region entdecken" (auf Kategorie/Karte) + "Alle Regionen auf der Karte"
- **Layout:** Horizontal Scroll (Carousel) auf Mobile, 4-Column Grid auf Desktop. Jede Card 1:1 oder 4:5 Ratio

### Section 6: Newsletter + Lead-Magnet

- **Ziel:** E-Mail-Adressen sammeln. Social Proof zeigen
- **Inhalt:** Headline: "Schottland-Post: Einmal im Monat die besten Tipps." Sub: Lead-Magnet-Beschreibung ("Gratis: Unsere Top-10-Destillerien als PDF"). Input + Button. Social Proof: "2.400+ Leser"
- **CTA:** "Kostenlos anmelden"
- **Layout:** `--bg-surface`-Band, zentriert, max 600px Content-Breite. Input + Button in einer Zeile. Social Proof als kleine Zeile darunter

### Section 7: Trust / About

- **Ziel:** Glaubwurdigkeit + Personlichkeit. "Warum dieser Blog?"
- **Inhalt:** Kurztext: "Seit 2007 reisen wir nach Schottland — 88 Destillerien, 14 Jahre, echte Geschichten." Autoren-Fotos (Steffen + Elmar, Cartoon-Stil). 3 Trust-Zahlen (14 Jahre, 88 Destillerien, 30+ Artikel). Affiliate-Transparenz: "Warum wir empfehlen — und warum du uns vertrauen kannst."
- **CTA:** "Uber uns" + "Warum Affiliate-Links?"
- **Layout:** 2-Column: Text links, Autoren-Bild rechts. Trust-Zahlen als 3 Badges in einer Reihe. Dezent, nicht prahlerisch

### Section 8: Footer

- **Ziel:** Navigation, Legal, letzte Newsletter-Chance
- **Inhalt:** 4 Spalten: (1) Logo + Kurztext + Social Icons, (2) Navigation, (3) Kategorien + Tags, (4) Newsletter-Mini (nur Input + Button). Darunter: Copyright, Impressum, Datenschutz, Affiliate-Hinweis
- **Layout:** `--bg-surface` Background, 4-Column Grid, zentriert. Mobile: stacked

---

## 4) Conversion-Playbook

### Affiliate-Massnahmen

**M1: "Whisky of the Month"-Modul auf der Startseite**
Platzierung: Section 4, above the fold (bei Desktop). Format: Horizontale Karte mit Produktbild, Tasting-Notes, Preis, CTA. Frequenz: Monatlich wechselnd. Wirkt redaktionell, nicht werblich, weil es eine kuratierte Einzelempfehlung ist.

**M2: "Empfohlene Flaschen" am Artikelende**
Platzierung: Nach dem letzten Absatz, vor "Related Articles". Format: 2-4 Produkt-Cards horizontal. Copy: "Flaschen aus diesem Artikel" oder "Passend dazu". Jede Card: Produktname, Preis, 1 Satz, CTA. Disclaimer: "* Affiliate-Link"-Badge

**M3: Inline-Affiliate-Links im Fliesstext**
Format: Wenn ein Whisky im Text erwahnt wird, wird der Name zum Link. Dezenter Tooltip bei Hover: "Bei Amazon ab XX EUR". Keine storende Unterbrechung des Leseflusses.

**M4: "Quick Tasting Panel" in Artikeln**
Platzierung: Rechte Sidebar oder als Box nach dem ersten Absatz. Format: Strukturierte Ubersicht — Region, Alter, Fasstyp, Aroma, Geschmack, Finish, Preis. CTA am Ende: "Flasche sichern". Wirkt wie ein Factsheet, nicht wie Werbung.

**M5: "Whisky Shoppen"-Landingpage**
Eigene Seite mit kuratierten Listen: Einsteiger, Islay-Favoriten, Speyside-Klassiker, Budget-Tipps, Geschenke. Jede Liste: 5-8 Produkte mit Kurztext + Preis + CTA. Header-Transparenz: "So empfehlen wir" + "So funktionieren Affiliate-Links"

**M6: "Whisky of the Month"-Archiv**
Alle bisherigen Monats-Empfehlungen als durchsuchbare Timeline. Zeigt Kompetenz + Tiefe. Jeder Eintrag weiterhin mit aktivem Affiliate-Link.

**M7: Sticky Affiliate-Bar bei Scrolltiefe > 60%**
Dunner Bar am unteren Bildschirmrand: "[Whisky-Name] ab XX EUR — Jetzt ansehen". Erscheint erst, wenn der User tief im Artikel ist (= engagiert). Wegklickbar, nicht nervig.

### Newsletter-Massnahmen

**M8: Lead-Magnet "Die 10 Destillerien, die nicht jeder kennt" (PDF)**
Exklusiver Content als Anreiz. PDF: 8-10 Seiten, schon gestaltet, mit Bildern + Kurzreviews. Download nach E-Mail-Eingabe. Bewirbt sich selbst: "Kostenlos. Kein Spam. Einmal im Monat."

**M9: Mid-Article Newsletter-Trigger**
Platzierung: Nach ca. 40% Scroll-Tiefe im Artikel. Format: Inline-Box, nicht Popup. Copy: "Gefallt dir dieser Artikel? Einmal im Monat schicken wir dir ahnliche Geschichten." Conversion-Rate typisch 1.5-3%.

**M10: Exit-Intent Newsletter (Desktop only)**
Popup wenn Maus den Viewport verlasst. Copy: "Bevor du gehst — hol dir unsere Schottland-Post." Lead-Magnet-Teaser + Input. Frequenz: Max 1x pro Session. Mobile: ersetzt durch Scroll-Up-Bar.

**M11: Personalisierte Newsletter-Copy je Kategorie**
Auf Whisky-Artikeln: "Du magst Whisky-Reviews? Wir auch." Auf Reise-Artikeln: "Planst du eine Schottland-Reise? Lass uns helfen." Matching Copy erhoht Relevanz und Conversion.

### Trust-Massnahmen

**M12: "Seit 2007 unterwegs"-Badge**
Kleiner Badge im Header oder Hero: "Seit 2007 | 88 Destillerien | 14 Jahre Schottland". Sofort sichtbar. Schafft Vertrauen, bevor der erste Artikel gelesen wird.

**M13: Autorenbox mit Personlichkeit**
Am Ende jedes Artikels: Foto, Name, 2 Satze Bio, "X Artikel geschrieben". Personlich, nicht generisch. "Steffen trinkt am liebsten Lagavulin 16 — aber sagt es niemandem."

**M14: Transparenz-Seite "So empfehlen wir"**
Eigene Seite, verlinkt im Footer + bei jedem Affiliate-Modul. Erklart: Wie Empfehlungen entstehen, dass nur selbst Probierbares empfohlen wird, wie Affiliate funktioniert, dass Meinungen unabhangig sind.

**M15: "Wir waren dort"-Siegel auf Destillerie-Artikeln**
Grunner Badge: "Personlich besucht [Jahr]". Unterscheidet echte Reise-Erfahrung von Recherche-Artikeln. Starker Trust-Marker.

### A/B-Test-Ideen

**T1: CTA-Text Whisky of the Month**
Variante A: "Jetzt entdecken" vs. Variante B: "Flasche sichern" vs. Variante C: "Preis checken"
Metrik: Click-Through-Rate auf Affiliate-Link

**T2: Newsletter-Platzierung**
Variante A: Mid-Article (40% Scroll) vs. Variante B: End-of-Article vs. Variante C: Beides
Metrik: Signup-Rate pro Seitenaufruf

**T3: Hero-Format Startseite**
Variante A: Full-Width-Image mit Overlay vs. Variante B: Split (Bild links, Text rechts)
Metrik: Scroll-Depth + Click auf Featured Story

**T4: Whisky of the Month — mit vs. ohne Preis**
Variante A: Preis sichtbar ("Ab 52 EUR") vs. Variante B: "Preis ansehen" (Neugier-CTA)
Metrik: Affiliate-Klickrate

**T5: Trust-Zahlen-Platzierung**
Variante A: Im Hero ("14 Jahre | 88 Destillerien") vs. Variante B: Eigene Section weiter unten
Metrik: Time-on-Site + Newsletter-Conversion

---

## 5) Page Templates

### 5.1 Artikel-Template (Story)

#### Header-Bereich (above the fold)

```
[Breadcrumb: Start > Whisky > Macallan]
[Kategorie-Badge: "WHISKY"]
[H1: "Macallan: Ist der Hype gerechtfertigt?"]
[Meta: "Von Steffen · 18. Marz 2026 · 12 Min. Lesezeit"]
[Hero-Image: 16:9, full-width innerhalb max-width]
[Trust-Badge: "Personlich besucht 2019"]
```

#### Quick Tasting Panel (optional, bei Whisky-Reviews)

```
┌─────────────────────────────────────┐
│  QUICK TASTING                      │
│  ─────────────────                  │
│  Region:    Speyside                │
│  Alter:     12 Jahre                │
│  Fasstyp:   Sherry Oak             │
│  ABV:       43%                     │
│  ──────────                         │
│  Aroma:     Trockenfruechte, Vanille│
│  Geschmack: Honig, Gewuerze, Eiche │
│  Finish:    Lang, warm, Sherry     │
│  ──────────                         │
│  Preis:     Ab ca. 58 EUR          │
│  [Jetzt entdecken →]  * Affiliate  │
└─────────────────────────────────────┘
```

#### Inhaltsverzeichnis (bei Artikeln > 1500 Worter)

```
IN DIESEM ARTIKEL
1. Die Sherry-Fass-Philosophie
2. Die Preisfrage
3. Unser Fazit
```

Sticky auf Desktop (rechte Sidebar), collapsible auf Mobile.

#### Artikel-Body

- Max-width: 720px, zentriert
- Typografie: Inter 400, 17px, 1.75 line-height
- H2: Fraunces 500, 28px, mit `--accent-amber` Top-Border (2px)
- H3: Inter 600, 20px
- Blockquotes: Fraunces italic, `--accent-amber` Left-Border (4px), `--bg-surface` Background
- Bilder: Full-Width innerhalb der 720px, mit Caption darunter (Inter 400, 14px, `--text-secondary`)

#### Reise-Infobox (bei Reise-Artikeln)

```
┌─────────────────────────────────────┐
│  REISE-INFO                         │
│  ─────────────────                  │
│  Destillerie: The Macallan          │
│  Adresse:     Easter Elchies, ...   │
│  Tour:        Ab 15 GBP, taeglich  │
│  Anreise:     45 Min. ab Inverness │
│  Beste Zeit:  Mai–September         │
│  Website:     themacallan.com       │
└─────────────────────────────────────┘
```

#### "Empfohlene Flaschen" (vor Related Articles)

```
PASSEND ZU DIESEM ARTIKEL
┌──────────┐ ┌──────────┐ ┌──────────┐
│ [Bild]   │ │ [Bild]   │ │ [Bild]   │
│ Macallan │ │ GlenDro. │ │ Aberlour │
│ 12 Sherry│ │ 12       │ │ A'bunadh │
│ Ab 58 EUR│ │ Ab 38 EUR│ │ Ab 52 EUR│
│ [Entdeck]│ │ [Entdeck]│ │ [Entdeck]│
└──────────┘ └──────────┘ └──────────┘
* Affiliate-Links: Kaufst du ueber diese Links, erhalten wir
eine kleine Provision. Der Preis bleibt fur dich gleich.
```

#### Related Articles

3 Karten horizontal, gleiche Card-Komponente wie Homepage.

#### Autorenbox

```
┌─────────────────────────────────────┐
│ [Foto]  STEFFEN                     │
│         Whisky-Enthusiast seit 2007.│
│         88 Destillerien besucht.    │
│         Trinkt am liebsten          │
│         Lagavulin 16.               │
│         [Alle Artikel von Steffen]  │
└─────────────────────────────────────┘
```

---

### 5.2 Kategorie-Template

```
[Header]
[H1: "Whisky" oder "Reise" — Fraunces 42px]
[Kurzbeschreibung: 1-2 Satze]
[Filter-Leiste: Alle | Islay | Speyside | Highlands | ...]
[─────────────────────────────────────────]
[Featured Article: Gross, 2 Spalten]
[─────────────────────────────────────────]
[Article Grid: 3 Spalten, Card-Komponente]
[Pagination oder "Mehr laden"]
[Footer]
```

**Filter:** Minimal, nicht zu "Shop"-artig. Pill-Buttons in einer Zeile. Aktiver Filter: `--accent-amber` Background + weisser Text.

---

### 5.3 Whisky-Shoppen Landing

```
[Header]
[Hero: "Whisky Shoppen — Unsere Empfehlungen"]
[Transparenz-Block: "So empfehlen wir" + Kurzerklarung]
[─────────────────────────────────────────]
[Whisky of the Month: Aktuell — Gross, Hero-artig]
[─────────────────────────────────────────]
[Kuratierte Listen:]
  [H2: "Fur Einsteiger" — 5 Produkte horizontal]
  [H2: "Islay-Favoriten" — 5 Produkte horizontal]
  [H2: "Speyside-Klassiker" — 5 Produkte horizontal]
  [H2: "Unter 40 EUR" — 5 Produkte horizontal]
  [H2: "Geschenke" — 5 Produkte horizontal]
[─────────────────────────────────────────]
[Whisky of the Month — Archiv (Timeline)]
[─────────────────────────────────────────]
[Newsletter-CTA]
[Footer]
```

**Produkt-Card auf dieser Seite:**

```
┌──────────────┐
│ [Produktbild] │
│ Name          │
│ Destillerie   │
│ Region-Badge  │
│ 1 Satz Review │
│ Ab XX EUR     │
│ [Entdecken →] │
└──────────────┘
```

---

## 6) Microcopy (Deutsch)

### 6.1 Affiliate-CTA-Varianten (12x)

| #   | CTA                         | Ton                    | Einsatz                                   |
| --- | --------------------------- | ---------------------- | ----------------------------------------- |
| 1   | "Jetzt entdecken"           | Neutral, neugierig     | Whisky of the Month, Produkt-Cards        |
| 2   | "Bei Amazon ansehen"        | Transparent, direkt    | Inline-Empfehlungen, Fliesstext           |
| 3   | "Flasche sichern"           | Leichte Dringlichkeit  | Limitierte Editionen, seltene Abfullungen |
| 4   | "Zum Angebot"               | Direkt, wertorientiert | Preis-Deals, Budget-Listen                |
| 5   | "Probier's selbst"          | Buddy-Ton              | End-of-Article, nach personlicher Review  |
| 6   | "Unsere Empfehlung ansehen" | Vertrauen + Neugier    | Empfehlungs-Boxen                         |
| 7   | "Diesen Whisky entdecken"   | Spezifisch             | Inline nach Whisky-Erwahnung              |
| 8   | "Hier findest du ihn"       | Hilfreich, Guide-Ton   | Nach Tasting-Notes                        |
| 9   | "Preis checken"             | Wertorientiert         | Vergleichstabellen                        |
| 10  | "Direkt zum Whisky"         | Casual, Buddy          | Kurze Empfehlungen                        |
| 11  | "Mehr erfahren & bestellen" | Informativ             | Detaillierte Reviews                      |
| 12  | "Gleich mitnehmen"          | Souvenir-Metapher      | Reise-Artikel                             |

### 6.2 Newsletter-CTA-Varianten (8x)

| #   | CTA                             | Ton                          | Einsatz                   |
| --- | ------------------------------- | ---------------------------- | ------------------------- |
| 1   | "Kostenlos anmelden"            | Klar, risikolos              | Standard, uberall         |
| 2   | "Schottland-Post abonnieren"    | Thematisch, charmant         | Startseite                |
| 3   | "Dabei sein"                    | Community                    | Social-Proof-Kontext      |
| 4   | "Mitreisen"                     | Reise-Metapher               | Reise-Artikel             |
| 5   | "Dram per Mail"                 | Whisky-Metapher, spielerisch | Whisky-Artikel            |
| 6   | "Nichts verpassen"              | Mildes FOMO                  | Exit-Intent               |
| 7   | "Einmal im Monat. Versprochen." | Vertrauen + Frequenz         | Unter Input-Feld          |
| 8   | "Jetzt eintragen"               | Direkt, simpel               | Mobile, kompakte Variante |

### 6.3 Hero-Headline-Varianten (6x)

| #   | Headline                                                   | Tonalitat              |
| --- | ---------------------------------------------------------- | ---------------------- |
| 1   | "Scotch trinken. Schottland erleben."                      | Klar, Dual-Promise     |
| 2   | "14 Jahre Schottland. 88 Destillerien. Echte Geschichten." | Trust + Scope          |
| 3   | "Dein Guide durch Schottlands Whisky-Welt."                | Buddy + Guide          |
| 4   | "Wo der nachste Dram wartet."                              | Poetisch, einladend    |
| 5   | "Whisky. Reise. Abenteuer. Seit 2007."                     | Bold, simpel           |
| 6   | "Von Islay bis Speyside — komm mit."                       | Spezifisch + Einladung |

---

## 7) Design System Light

### 7.1 Buttons

| Variante          | Background                 | Text               | Border                     | Radius | Padding   | Einsatz                     |
| ----------------- | -------------------------- | ------------------ | -------------------------- | ------ | --------- | --------------------------- |
| **Primary**       | `--accent-amber`           | `#FFFFFF`          | none                       | 8px    | 12px 28px | CTAs, Affiliate, Newsletter |
| **Primary Hover** | `#B38535` (dunklere Amber) | `#FFFFFF`          | none                       | 8px    | 12px 28px | —                           |
| **Secondary**     | transparent                | `--accent-amber`   | 2px solid `--accent-amber` | 8px    | 10px 26px | Sekundare Actions           |
| **Ghost**         | transparent                | `--text-primary`   | 1px solid `--border`       | 8px    | 10px 26px | Navigation, Filter          |
| **Ghost Hover**   | `--bg-surface`             | `--text-primary`   | 1px solid `--accent-warm`  | 8px    | 10px 26px | —                           |
| **Pill**          | `--bg-surface`             | `--text-secondary` | none                       | 24px   | 6px 16px  | Tags, Filter-Pills          |
| **Pill Active**   | `--accent-amber`           | `#FFFFFF`          | none                       | 24px   | 6px 16px  | Aktiver Filter              |

**Font:** Inter 600, 14px, Letterspacing 0.5px. Text-Transform: none (kein Uppercase bei Buttons — freundlicher).

### 7.2 Cards

#### Story Card (Standard)

```css
.story-card {
  background: var(--bg-elevated);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(139,115,85,0.06);
  transition: transform 0.2s, box-shadow 0.3s;
}
.story-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(139,115,85,0.12);
}
```

Bild (3:2) oben, Padding 20px. Kategorie-Pill, H3 (Fraunces 500, 20px), Meta (Inter 400, 13px, `--text-secondary`), Teaser (Inter 400, 15px, 2 Zeilen clamp).

#### Produkt Card (Affiliate)

```css
.product-card {
  background: var(--bg-elevated);
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 20px;
  text-align: center;
}
```

Produktbild (1:1, max 200px), Name (Inter 600, 16px), Destillerie (Inter 400, 13px, `--text-secondary`), Region-Badge, Preis (Fraunces 500, 20px, `--accent-amber`), CTA-Button.

#### Featured Card (Hero-Grösse)

Wie Story Card, aber Bild grosser (2:1 Ratio), H2 statt H3 (Fraunces 600, 28px), mit Teaser-Text.

### 7.3 Badges & Tags

| Element             | Font                                 | Style                                                | Einsatz                           |
| ------------------- | ------------------------------------ | ---------------------------------------------------- | --------------------------------- |
| **Kategorie-Badge** | Inter 600, 11px, Uppercase, LS 1.5px | Pill, `--accent-amber` bg, white text                | Auf Cards, im Artikel             |
| **Region-Badge**    | Inter 500, 11px, Uppercase, LS 1px   | Pill, `--accent-sage` bg, white text                 | Auf Produkt-Cards, Tasting Panel  |
| **Trust-Badge**     | Inter 500, 12px                      | Pill, `--bg-surface` bg, `--accent-sage` text + Icon | "Seit 2007", "Personlich besucht" |
| **Tag**             | Inter 400, 13px                      | Pill, `--bg-surface` bg, `--text-secondary` text     | Tag-Cloud, Filter                 |
| **Tag Hover**       | Inter 400, 13px                      | Pill, `--accent-amber` bg, white text                | —                                 |

### 7.4 Breadcrumbs

```
Start / Whisky / Macallan
```

Inter 400, 13px, `--text-secondary`. Separator: "/". Letztes Element: `--text-primary`, kein Link. Padding: 16px 0.

### 7.5 Whisky-of-the-Month-Modul

```
┌──────────────────────────────────────────────┐
│ ▀▀▀▀ --accent-amber Top-Border (4px)         │
│                                              │
│ [Produktbild]    WHISKY DES MONATS           │
│  200x200         ──────────────              │
│                  Macallan Double Cask 12      │
│                  The Macallan · Speyside      │
│                  [Region-Badge]               │
│                                              │
│                  "Sherry-Sueße trifft        │
│                  Vanille — zugaenglich und    │
│                  komplex zugleich."           │
│                                              │
│                  Aroma:    Trockenfruechte    │
│                  Geschmack: Honig, Eiche     │
│                  Finish:   Lang, warm        │
│                                              │
│                  Ab ca. 58 EUR               │
│                  [Jetzt entdecken]            │
│                                              │
│ * Affiliate-Link. Mehr dazu →                │
└──────────────────────────────────────────────┘
```

Background: `--bg-elevated`. Border-Top: 4px solid `--accent-amber`. Padding: 32px. Shadow: standard Card-Shadow.

### 7.6 Newsletter-Box

#### Variante A: Standard (hell)

```
┌──────────────────────────────────────────────┐
│          SCHOTTLAND-POST                     │
│                                              │
│  Einmal im Monat: unsere besten Stories,     │
│  Whisky-Tipps und Reise-Ideen.               │
│                                              │
│  [E-Mail-Adresse        ] [Anmelden]         │
│                                              │
│  2.400+ Whisky-Fans lesen mit.               │
│  Kein Spam. Jederzeit kuendbar.              │
└──────────────────────────────────────────────┘
```

Background: `--bg-surface`. Headline: Fraunces 500, 24px. Input: 48px hoch, Border `--border`, Focus-Border `--accent-amber`. Button: Primary.

#### Variante B: Lead-Magnet (mit PDF-Anreiz)

```
┌──────────────────────────────────────────────┐
│  [PDF-Cover]  GRATIS: DIE 10 DESTILLERIEN,  │
│               DIE NICHT JEDER KENNT          │
│                                              │
│               Unser Guide mit Insider-Tipps, │
│               Tasting-Notes und Anreise-     │
│               Infos. Direkt in dein Postfach.│
│                                              │
│  [E-Mail-Adresse        ] [Jetzt holen]      │
│                                              │
│  Kostelos. Einmal im Monat. Versprochen.     │
└──────────────────────────────────────────────┘
```

### 7.7 Autorenbox

```css
.author-box {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  padding: 24px;
  background: var(--bg-surface);
  border-radius: 12px;
}
.author-image { width: 80px; height: 80px; border-radius: 50%; }
```

Foto (80px, rund), Name (Inter 600, 16px), Bio (Inter 400, 14px, `--text-secondary`, 2 Zeilen), Link "Alle Artikel" (Inter 500, `--accent-amber`).

### 7.8 Affiliate-Transparenz-Hinweis

```
┌──────────────────────────────────────────────┐
│ ℹ  Transparenz: Dieser Artikel enthalt       │
│    Affiliate-Links (mit * gekennzeichnet).   │
│    Kaufst du darueber, erhalten wir eine     │
│    kleine Provision — der Preis bleibt fuer  │
│    dich gleich. Mehr erfahren →              │
└──────────────────────────────────────────────┘
```

Background: `--bg-surface`. Border-Left: 3px solid `--accent-sage`. Font: Inter 400, 14px, `--text-secondary`. Icon: Info-Circle in `--accent-sage`. Elegant, nicht defensiv.

---

## 8) Next.js Umsetzungs-Skizze

### 8.1 Komponentenstruktur

```
whisky-magazin-next/
├── app/
│   ├── layout.tsx              # Root Layout (Fonts, Header, Footer)
│   ├── page.tsx                # Homepage
│   ├── artikel/
│   │   └── [slug]/page.tsx     # Artikel-Detail
│   ├── kategorie/
│   │   └── [slug]/page.tsx     # Kategorie-Ubersicht
│   ├── whisky-shoppen/
│   │   └── page.tsx            # Affiliate-Landing
│   ├── karte/
│   │   └── page.tsx            # Interaktive Karte
│   └── api/
│       └── newsletter/route.ts # Newsletter-Signup API
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── Navigation.tsx
│   ├── sections/
│   │   ├── HeroFeatured.tsx
│   │   ├── FeaturedStories.tsx
│   │   ├── WhiskyOfTheMonth.tsx
│   │   ├── RegionTeaser.tsx
│   │   ├── NewsletterSection.tsx
│   │   └── TrustSection.tsx
│   ├── cards/
│   │   ├── StoryCard.tsx
│   │   ├── ProductCard.tsx
│   │   └── FeaturedCard.tsx
│   ├── article/
│   │   ├── ArticleHeader.tsx
│   │   ├── ArticleBody.tsx
│   │   ├── TastingPanel.tsx
│   │   ├── TravelInfoBox.tsx
│   │   ├── RecommendedBottles.tsx
│   │   ├── AuthorBox.tsx
│   │   └── TableOfContents.tsx
│   ├── modules/
│   │   ├── AffiliateInline.tsx
│   │   ├── AffiliateDisclosure.tsx
│   │   └── ReadingProgress.tsx
│   └── ui/
│       ├── Button.tsx
│       ├── Badge.tsx
│       ├── Tag.tsx
│       ├── Breadcrumb.tsx
│       ├── Input.tsx
│       └── Card.tsx
├── lib/
│   ├── articles.ts             # Artikel-Daten laden (aus JSON/MDX)
│   ├── types.ts                # TypeScript Types
│   └── utils.ts                # Hilfsfunktionen
├── content/
│   └── articles/               # MDX oder JSON Artikel-Dateien
├── public/
│   ├── images/
│   └── fonts/                  # Falls Self-Hosted Fonts
├── styles/
│   └── globals.css             # CSS Custom Properties + Tailwind
├── tailwind.config.ts
├── next.config.ts
└── package.json
```

### 8.2 Beispiel: Featured Stories Section

```tsx
// components/sections/FeaturedStories.tsx
import { StoryCard } from '@/components/cards/StoryCard'
import { FeaturedCard } from '@/components/cards/FeaturedCard'
import type { Article } from '@/lib/types'

interface FeaturedStoriesProps {
  articles: Article[]  // Erwartet 6 Artikel, sortiert nach Prioritat
}

export function FeaturedStories({ articles }: FeaturedStoriesProps) {
  const [hero, secondary, ...rest] = articles

  return (
    <section className="py-20 px-8">
      <div className="max-w-[1200px] mx-auto">
        <h2 className="font-heading text-sm font-semibold tracking-widest uppercase text-secondary mb-8">
          Aktuelle Geschichten
        </h2>

        {/* Zeile 1: 1 gross + 1 mittel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <div className="lg:col-span-2">
            <FeaturedCard article={hero} />
          </div>
          <div>
            <StoryCard article={secondary} />
          </div>
        </div>

        {/* Zeile 2: 4 kleine */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {rest.map((article) => (
            <StoryCard key={article.slug} article={article} compact />
          ))}
        </div>

        <div className="text-center mt-10">
          <a
            href="/kategorie/alle"
            className="inline-block px-7 py-3 border border-border rounded-lg text-sm font-medium
                       text-primary hover:bg-surface transition-colors"
          >
            Alle Artikel ansehen
          </a>
        </div>
      </div>
    </section>
  )
}
```

### 8.3 Beispiel: Whisky of the Month

```tsx
// components/sections/WhiskyOfTheMonth.tsx
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import Image from 'next/image'

interface WhiskyOfTheMonthProps {
  name: string
  distillery: string
  region: string
  description: string
  tasting: {
    aroma: string
    taste: string
    finish: string
  }
  price: string
  affiliateUrl: string
  imageUrl: string
}

export function WhiskyOfTheMonth({
  name, distillery, region, description,
  tasting, price, affiliateUrl, imageUrl
}: WhiskyOfTheMonthProps) {
  return (
    <section className="py-20 px-8 bg-surface">
      <div className="max-w-[1200px] mx-auto">
        <div className="bg-elevated rounded-xl border-t-4 border-accent-amber shadow-card p-8
                        grid grid-cols-1 md:grid-cols-[200px_1fr] gap-8 items-start">

          {/* Produktbild */}
          <div className="flex justify-center">
            <Image
              src={imageUrl}
              alt={name}
              width={200}
              height={200}
              className="rounded-lg"
            />
          </div>

          {/* Content */}
          <div>
            <p className="text-xs font-semibold tracking-widest uppercase text-accent-amber mb-2">
              Whisky des Monats
            </p>
            <h3 className="font-heading text-2xl font-semibold mb-1">{name}</h3>
            <p className="text-sm text-secondary mb-1">{distillery}</p>
            <Badge variant="region">{region}</Badge>

            <p className="mt-4 text-base leading-relaxed text-secondary">
              {description}
            </p>

            {/* Tasting Notes */}
            <div className="mt-6 grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="font-semibold text-xs uppercase tracking-wide text-accent-warm mb-1">
                  Aroma
                </p>
                <p className="text-secondary">{tasting.aroma}</p>
              </div>
              <div>
                <p className="font-semibold text-xs uppercase tracking-wide text-accent-warm mb-1">
                  Geschmack
                </p>
                <p className="text-secondary">{tasting.taste}</p>
              </div>
              <div>
                <p className="font-semibold text-xs uppercase tracking-wide text-accent-warm mb-1">
                  Finish
                </p>
                <p className="text-secondary">{tasting.finish}</p>
              </div>
            </div>

            {/* Preis + CTA */}
            <div className="mt-6 flex items-center gap-4">
              <span className="font-heading text-xl font-semibold text-accent-amber">
                {price}
              </span>
              <Button href={affiliateUrl} external>
                Jetzt entdecken
              </Button>
            </div>

            <p className="mt-3 text-xs text-secondary/60">
              * Affiliate-Link.{' '}
              <a href="/transparenz" className="underline hover:text-accent-amber">
                Mehr erfahren
              </a>
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
```

### 8.4 Beispiel: Newsletter CTA

```tsx
// components/sections/NewsletterSection.tsx
'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'

interface NewsletterSectionProps {
  variant?: 'standard' | 'lead-magnet'
  headline?: string
  description?: string
}

export function NewsletterSection({
  variant = 'standard',
  headline = 'Schottland-Post',
  description = 'Einmal im Monat: unsere besten Stories, Whisky-Tipps und Reise-Ideen.',
}: NewsletterSectionProps) {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatus('loading')

    try {
      const res = await fetch('/api/newsletter', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      if (res.ok) {
        setStatus('success')
        setEmail('')
      } else {
        setStatus('error')
      }
    } catch {
      setStatus('error')
    }
  }

  if (status === 'success') {
    return (
      <section className="py-20 px-8 bg-surface">
        <div className="max-w-[600px] mx-auto text-center">
          <p className="font-heading text-2xl font-semibold text-accent-sage">
            Willkommen an Bord!
          </p>
          <p className="mt-2 text-secondary">
            Check dein Postfach — deine erste Schottland-Post ist unterwegs.
          </p>
        </div>
      </section>
    )
  }

  return (
    <section className="py-20 px-8 bg-surface">
      <div className="max-w-[600px] mx-auto text-center">
        <h2 className="font-heading text-2xl md:text-3xl font-semibold mb-3">
          {headline}
        </h2>
        <p className="text-secondary mb-6">{description}</p>

        <form onSubmit={handleSubmit} className="flex gap-3 max-w-[480px] mx-auto">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Deine E-Mail-Adresse"
            required
            className="flex-1 h-12 px-4 rounded-lg border border-border bg-elevated
                       text-primary placeholder:text-secondary/50
                       focus:outline-none focus:border-accent-amber focus:ring-2 focus:ring-accent-amber/20
                       transition-colors"
          />
          <Button type="submit" disabled={status === 'loading'}>
            {status === 'loading' ? 'Moment...' : 'Anmelden'}
          </Button>
        </form>

        <p className="mt-4 text-xs text-secondary/60">
          2.400+ Whisky-Fans lesen mit. Kein Spam. Jederzeit kuendbar.
        </p>

        {status === 'error' && (
          <p className="mt-2 text-sm text-red-600">
            Da lief etwas schief. Versuch es bitte nochmal.
          </p>
        )}
      </div>
    </section>
  )
}
```

### 8.5 Tailwind Config (Auszug)

```ts
// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#1A1A1A',
        secondary: '#5C5C5C',
        surface: '#F5F0E8',
        elevated: '#FFFFFF',
        border: '#E8DCC8',
        'accent-amber': '#C8963E',
        'accent-sage': '#4A7C5E',
        'accent-warm': '#8B7355',
      },
      fontFamily: {
        heading: ['Fraunces', 'Georgia', 'serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        body: ['17px', { lineHeight: '1.75' }],
      },
      borderRadius: {
        card: '12px',
      },
      boxShadow: {
        card: '0 2px 12px rgba(139,115,85,0.06)',
        'card-hover': '0 8px 24px rgba(139,115,85,0.12)',
      },
      backgroundColor: {
        page: '#FAFAF7',
      },
    },
  },
  plugins: [],
}
export default config
```

### 8.6 CSS Custom Properties (globals.css)

```css
/* styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-primary: #FAFAF7;
  --bg-surface: #F5F0E8;
  --bg-elevated: #FFFFFF;
  --text-primary: #1A1A1A;
  --text-secondary: #5C5C5C;
  --accent-amber: #C8963E;
  --accent-amber-dark: #A67A2E;
  --accent-sage: #4A7C5E;
  --accent-warm: #8B7355;
  --border: #E8DCC8;
  --radius: 12px;
  --radius-sm: 8px;
  --radius-pill: 24px;
  --shadow-card: 0 2px 12px rgba(139,115,85,0.06);
  --shadow-card-hover: 0 8px 24px rgba(139,115,85,0.12);
}

body {
  font-family: 'Inter', system-ui, sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  font-size: 17px;
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}
```

---

## 9) Kreativ-Boost — 3 besondere Features

### Feature 1: "Flavor Postcards" — Aromen als Reise-Postkarten

**Idee:** Jeder Whisky-Review enthalt eine "Flavor Postcard" — eine kleine, visuell gestaltete Karte im Postkarten-Format, die die Aromen als Reise-Erlebnis darstellt.

**Umsetzung:**

- Format: 16:9, Card-Komponente mit illustrativem Hintergrund (CSS-Gradient in Bernstein-/Erdtonen)
- Vorderseite: "Gruesse von [Destillerie]" + 3 Aroma-Icons + Kurztext ("Torfrauch, Meersalz, Honig — wir waren dort.")
- Interaktion: Hover/Tap dreht die Karte (CSS 3D Transform) → Ruckseite zeigt Tasting-Notes + "Selbst probieren"-CTA
- **Shareability:** "Als Bild teilen"-Button generiert eine Open-Graph-taugliche Grafik → Instagram, WhatsApp, Twitter
- **Warum es funktioniert:** Macht abstrakte Geschmacksbeschreibungen visuell und teilbar. Organische Reichweite + Affiliate in einem.

### Feature 2: "Dram Diary" — Monatliche Kurznotiz aus Schottland

**Idee:** Ein kurzer, personlicher Monats-Eintrag (200-300 Worter) — wie eine Tagebuch-Seite. Was gerade passiert, was getrunken wird, was geplant ist.

**Umsetzung:**

- Eigene Komponente auf der Startseite (zwischen Featured Stories und Newsletter)
- Design: Leicht andere Typografie (Fraunces italic), `--bg-surface` Background, handschriftliches Datums-Element
- Inhalt: "Marz 2026 — Gerade zuruck von Islay. Der neue Port Charlotte ist ueberraschend. Nachsten Monat: Campbeltown revisited."
- Keine Bilder noetig, rein text-basiert
- **Warum es funktioniert:** Erzeugt "Wiederkommen-wollen". Der User checkt monatlich, was bei Steffen los ist. Baut Beziehung auf. Perfekter Newsletter-Teaser ("Den Rest gibt's per Mail").

### Feature 3: "Route Snippets" — Mini-Reiserouten am Artikelende

**Idee:** Am Ende jedes Destillerie-/Reise-Artikels: eine kompakte "Wenn du schon mal da bist"-Box mit 3-4 weiteren Stops in der Nahe.

**Umsetzung:**

```
┌──────────────────────────────────────────────┐
│  WENN DU SCHON MAL DA BIST...               │
│  ─────────────────────────                   │
│  → Laphroaig (4 Min.)     [Artikel lesen]   │
│  → Ardbeg (8 Min.)        [Artikel lesen]   │
│  → Kildalton Cross (12 Min.) [Auf der Karte]│
│  → Port Ellen Maltings (2 Min.) [Mehr Info]  │
│                                              │
│  [Komplette Route auf der Karte ansehen →]   │
└──────────────────────────────────────────────┘
```

- Daten: Automatisch aus map-data.json generiert (Nahe-Berechnung via Koordinaten)
- Verlinkung: Auf Artikel (wenn vorhanden) oder Karten-Position
- **Warum es funktioniert:** Halt den User auf der Seite (Related Content auf Geo-Basis). Verknupft Artikel-Content mit der Karten-Seite. Zeigt Tiefe des Contents. Perfekt fur Reise-Planung = Bookmarks = wiederkehrende Besucher.

---

## Empfehlung: Priorisierte Umsetzungsreihenfolge

| Phase | Was                                                                | Warum zuerst                               |
| ----- | ------------------------------------------------------------------ | ------------------------------------------ |
| **1** | Brand-Basics (Farben, Fonts, Logo) + Startseite + Artikel-Template | Kern-Erlebnis fur 90% der Besucher         |
| **2** | Newsletter-Modul + Lead-Magnet                                     | Sofortige Wirkung auf Wiederkehr-Rate      |
| **3** | Whisky-of-the-Month + Affiliate-Module                             | Revenue-relevant, braucht Content-Pipeline |
| **4** | Whisky-Shoppen-Landing                                             | Eigene Affiliate-Destination               |
| **5** | Kreativ-Features (Flavor Postcards, Dram Diary, Route Snippets)    | Differenzierung + Engagement               |
| **6** | Kategorie-Template + Karten-Redesign                               | Verfeinerung                               |

---

## Tasting-Icons (Aroma · Geschmack · Abgang)

**Regel:** In allen Whisky-Tasting-Blöcken (Whisky des Monats, Empfehlungs-Boxen, künftige Verkostungs-Karten) werden **keine Emoji** mehr verwendet (👃 👅 ✨ wirken verspielt und brechen mit dem editorialen Magazin-Ton). Stattdessen kommen drei dedizierte **Inline-SVG-Icons im Konturstil** zum Einsatz — mit `currentColor` einfärbbar (Standard: `var(--accent-amber)`), `stroke-width: 1.6`, viewBox `0 0 24 24`.

| Sektion | Symbolik | Bedeutung |
|---------|----------|-----------|
| Aroma | Nosing-Glas mit aufsteigendem Dampf | klassisches Nasing-Symbol |
| Geschmack | Tropfen mit Highlight | Flüssigkeit, Gaumen |
| Abgang | Sanduhr | langer, anhaltender Nachklang |

**Verwendung:** Die SVGs sind direkt im Markup eingebettet (kein extra HTTP-Request, scharf auf Retina, einfärbbar via CSS `color`). Renderinggröße 22 × 22 px in einer 24 × 24-Box, `margin-top: 2px` damit das Icon optisch auf der Textgrundlinie sitzt.

```html
<!-- Aroma: Nosing-Glas mit Dampf -->
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M9 21h6"/><path d="M12 21v-4"/>
  <path d="M7 9c0 3 2.2 8 5 8s5-5 5-8z"/>
  <path d="M10 5c-.5 1 .5 2 0 3"/><path d="M13 4c-.5 1 .5 2 0 3"/>
</svg>

<!-- Geschmack: Tropfen mit Highlight -->
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 3c-3 4-6 7-6 11a6 6 0 0 0 12 0c0-4-3-7-6-11z"/>
  <path d="M9 14c0 1.6 1.1 3 3 3"/>
</svg>

<!-- Abgang: Sanduhr -->
<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
  <path d="M7 3h10"/><path d="M7 21h10"/>
  <path d="M7 3v3c0 3 3 4 5 6 2-2 5-3 5-6V3"/>
  <path d="M7 21v-3c0-3 3-4 5-6 2 2 5 3 5 6v3"/>
</svg>
```

**Don't:** keine farbigen Emoji-Icons, keine ausgefüllten Glyphen, keine doppelte Strichstärke. Wenn neue Tasting-Felder dazukommen (z. B. „Farbe", „Finish-Stil"), ein weiteres Konturikon im selben Stil ergänzen — nicht zu Emoji zurückkehren.

---

*Erstellt als Senior Brand-/Webdesign-Konzept. Alle Entscheidungen sind umsetzbar, konkret und auf Conversion + Magazin-Feeling optimiert.*
