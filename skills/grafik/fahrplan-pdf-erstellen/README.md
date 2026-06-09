# Fahrplan → PDF

Erzeugt aus einer JSON-Datei eine DIN-A4-PDF im Stil eines gedruckten
Linien-Fahrplans (Bus/Bahn). Die Eingabe ist frei wählbar, der gleiche
Renderer funktioniert für beliebige Linien.

## Installation

```bash
pip install weasyprint
```

## Aufruf

```bash
python3 fahrplan_pdf.py beispiel_223.json -o Fahrplan_223.pdf
# optional zusätzlich das HTML zur Kontrolle:
python3 fahrplan_pdf.py beispiel_223.json -o out.pdf --html out.html
# optional zusätzlich Illustrator-/Vektor-Formate:
python3 fahrplan_pdf.py beispiel_223.json -o out.pdf --ai --svg
```

Ausgabeformate:
- `--ai` → Illustrator-kompatible `.ai` (PDF-Container, **Text bleibt editierbar**).
- `--svg` → reine Vektor-SVG via `pdftocairo` (**Text in Pfade umgewandelt**).

`beispiel_223.json` ist die nachgebaute Beispielseite (Linie 223).
`build_beispiel.py` zeigt, wie man so eine JSON-Datei aus Mustern
programmatisch erzeugt (praktisch bei vielen gleichförmigen Spalten).

## JSON-Schema

```jsonc
{
  "line": "223",                       // Liniennummer (groß im Kopf)
  "icon": "bus",                       // "bus" | "train" | "none"
  "title": "RE Hbf – … – Marl Mitte",  // Linientitel
  "accent": "#e2001a",                 // Farbe der roten Kopflinien
  "footnote": "[phone] = TaxiBus …",   // Fußnote ([phone] => Telefonsymbol)

  "stops": [                           // Haltestellen, Reihenfolge = Tabellenzeilen
    { "name": "RE Hbf",     "bold": true,  "symbol": null },
    { "name": "Sternwarte", "bold": false, "symbol": null },
    { "name": "Marl Mitte", "bold": true,  "symbol": "S"  }   // "S"/"U" => Kringel
  ],

  "blocks": [                          // ein Block = eine Zeile aus 1..n Sektionen
    { "sections": [ <Sektion Mo–Fr>, <Sektion Sa> ] },   // nebeneinander
    { "sections": [ <Sektion So> ] }                     // volle Breite
  ]
}
```

### Sektion (ein Tagestyp)

```jsonc
{
  "title": "Montag–Freitag",
  "color": "#3aaa35",        // Farbe des Titelbalkens + Zebra-Streifen
  "columns": [ <Spalte>, … ] // Fahrten von links nach rechts
}
```

### Spaltentypen

**Zeitspalte** (Standard) – eine Fahrt. `cells` hat genau so viele Einträge
wie es Haltestellen gibt; leere Zellen als `""` oder `null`.

```jsonc
{ "header": "phone",   // optional: Telefon-Icon über der Spalte (TaxiBus)
  "cells": ["6.12","15","16", … ,"6.56"] }
```

**Dreieck-/Richtungsspalte** – schmale Spalte mit ▼ oben und ▲ unten.

```jsonc
{ "type": "triangle", "color": "#3aaa35" }
```

**Intervallspalte** – senkrechter Text über die ganze Höhe ("alle 30 Min.").

```jsonc
{ "type": "interval", "text": "alle 30 Min." }
```

## Hinweise

- Volle Uhrzeiten (`6.12`) und Anschlussminuten (`15`) sind einfach Strings;
  fettgedruckte Haltestellen bekommen die Startzeit automatisch fett.
- Mehrere Sektionen in einem Block werden gleich breit nebeneinander gelegt.
- Spaltenbreiten/Schriftgrößen stehen oben im CSS-Block in `fahrplan_pdf.py`
  (`col.col-stop`, `.data-row td` usw.) und lassen sich dort anpassen.
```
```
