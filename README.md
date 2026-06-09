# KI-Workshop Baumgardt

Sammlung aller Materialien aus den Workshops: Präsentationen, Live-Beispiele und einsatzbereite Claude-Skills.

## Was ist wo?

```
workshop/
├── presentation/          Folien der Workshops (PDF + PPTX)
│   ├── KI-Workshop_Baumgardt.*              GIS-Workshop
│   └── KI-Workshop_Baumgardt_Grafik.*       Grafik-Workshop
├── claude-settings/       Screenshots zu Claude-Konfiguration (Computer Use etc.)
├── skills/                Die im Workshop gebauten Skills (Quellen + .skill-Bundles)
│   ├── general/
│   │   ├── redmine/                 Redmine-API-Zugriff (Tickets, Zeiten, Projekte)
│   │   └── redmine.skill            gepacktes Bundle zum Verteilen
│   ├── gis/
│   │   ├── linien-visualisierung/   Fahrplan-PDF → interaktive Karte
│   │   └── linien-visualisierung.skill   gepacktes Bundle
│   └── grafik/
│       ├── fahrplan-pdf-erstellen/  Fahrplan-Quelle → neu gesetzte DIN-A4-PDF-Tabelle
│       └── fahrplan-pdf-erstellen.skill   gepacktes Bundle
└── live-examples/         Was wir live gebaut haben — als Referenz
    ├── gis/linien-visualisierung-final/
    │                      Linie B100 Puderbach–Neuwied: Roh-PDF, Zwischen-CSV,
    │                      Routing-JSON und die fertige Leaflet-Karte
    │                      (100_karte.html im Browser öffnen)
    └── grafik/fahrplan-tabellen/
                           Linie 223: Quell-PDFs, JSON, Renderer und fertige
                           Ausgabe (PDF, SVG, Illustrator)
```

### Die Skills im Detail

**`skills/gis/linien-visualisierung/`** — Wandelt einen Bus-/Bahn-Fahrplan-PDF in eine interaktive Karte um. Pipeline: PDF → Text → Haltestellen-CSV → Koordinaten (aus Master-CSV oder Geocoding) → Routing (Google Routes API und/oder OSRM) → Leaflet-HTML. Iterativ und dialoggetrieben — die Skripte unter `scripts/` sind Referenzimplementierungen, nicht starre Pipeline. Details siehe `SKILL.md` im Skill-Ordner.

**`skills/grafik/fahrplan-pdf-erstellen/`** — Erzeugt aus einer Fahrplan-Quelle (PDF, Scan, Bild) eine neu gesetzte DIN-A4-Fahrplantabelle als PDF im Stil gedruckter Linienfahrpläne. Pipeline: Quelle einlesen → Haltestellen, Tagestypen und Zeiten extrahieren → JSON nach Schema → HTML/CSS + WeasyPrint → druckfertige PDF (optional auch `.ai` und `.svg`). Dialoggetrieben — Extrakt wird vor dem Rendern bestätigt. Details siehe `SKILL.md` im Skill-Bundle bzw. `README.md` im Quellordner.

**`skills/general/redmine/`** — Spricht die Redmine-Instanz unter `remi.bc-management.eu` über die REST-API an: Tickets abfragen/anlegen/updaten, Zeiten buchen, Projekte und Wiki lesen. Bündelt die OpenAPI-Spec (`openapi.json`) und die Credentials (`.env`). Vor erstem Einsatz `.env.example` → `.env` kopieren und Token eintragen.

## Installation

### 1. Claude Code installieren

Die aktuelle Installationsanleitung steht auf der offiziellen Seite — Installationswege ändern sich gelegentlich, deshalb dort nachschauen statt hier eine veraltete Befehlszeile abzuschreiben:

→ <https://code.claude.com/docs/de/setup>

Beim ersten Start einmal mit dem Anthropic-Account authentifizieren. Alternativen (Desktop-App, IDE-Plugins) sind in der Präsentation kurz erwähnt.

### 2. Skills installieren

**Einfachste Variante:** `.skill`-Datei doppelklicken — Claude Desktop öffnet das Bundle direkt und installiert den Skill ins lokale Verzeichnis. Funktioniert plattformübergreifend, kein Terminal nötig.

Alternativ den Skill-Quellordner aus diesem Repo nach `~/.claude/skills/` kopieren oder symlinken — praktisch, wenn man die Skills selbst weiterentwickeln will.

In neuer Claude-Session prüfen, ob die Skills geladen sind — sie tauchen in der Skill-Liste auf und werden automatisch getriggert, wenn dein Prompt zur Description passt.

### 3. Skill-Konfiguration

**Redmine:** im installierten Skill-Ordner die `.env.example` zu `.env` kopieren und den API-Token eintragen. Den Token holst du dir im Redmine unter *Mein Konto → API-Zugriffsschlüssel*. Wenn du nicht weißt, wo der Skill-Ordner liegt, frag einfach Claude — der findet das selbst raus und legt die Datei für dich an.

**Linien-Visualisierung:** kein Setup nötig. Wenn du Google Routes API nutzen willst, fragt der Skill beim ersten Einsatz nach dem Token und merkt ihn sich für künftige Sessions. Ohne Token läuft alles über OSRM kostenlos weiter.

Für die Linien-Visualisierung wird außerdem `pdftotext` (aus dem Poppler-Paket) und Python 3 gebraucht — wenn beides fehlt, sagt Claude beim ersten Einsatz Bescheid und schlägt einen passenden Installationsweg für dein Betriebssystem vor.

**Fahrplan-PDF erstellen:** einmalig `pip install weasyprint`. Bei text-basierten PDF-Quellen zusätzlich `pdftotext` (Poppler); für `--svg`-Ausgabe `pdftocairo`. Bild- und Scan-Quellen brauchen nur WeasyPrint — Claude liest die Tabelle direkt aus dem Bild.

## Erste Schritte

Frag Claude nach einer der folgenden Aufgaben — die Skills springen automatisch an:

- *"Welche offenen Aufgaben habe ich in Redmine?"* → Redmine-Skill
- *"Leg ein Ticket im Projekt X an: …"* → Redmine-Skill
- *"Hier ist ein Fahrplan-PDF — visualisier mir den Linienverlauf auf einer Karte"* → Linien-Visualisierungs-Skill
- *"Setz mir diesen Fahrplan als saubere PDF-Tabelle nach"* → Fahrplan-PDF-Skill

**GIS-Beispiel:** `live-examples/gis/linien-visualisierung-final/` — `100_karte.html` im Browser öffnen, um zu sehen, was am Ende rauskommt.

**Grafik-Beispiel:** `live-examples/grafik/fahrplan-tabellen/` — Quell-PDFs unter `source/`, nachgebautes JSON (`beispiel_223.json`) und fertige Ausgabe (`Fahrplan_223.pdf`, `.svg`, `.ai`).

## Präsentationen

| Workshop | Datei |
|---|---|
| GIS | `presentation/KI-Workshop_Baumgardt.pdf` (oder `.pptx` zum Bearbeiten) |
| Grafik | `presentation/KI-Workshop_Baumgardt_Grafik.pdf` (oder `.pptx`) |
