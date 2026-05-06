---
name: linien-visualisierung
description: Wandelt einen Bus- oder Bahn-Linienfahrplan (PDF) in eine interaktive Karte des Linienverlaufs um. Trigger immer dann, wenn ein Linienfahrplan, Busfahrplan, Bahnfahrplan, Haltestellenplan, Liniennetz, Streckenfahrplan oder ähnliches PDF vorliegt und der Linienverlauf, die Haltestellen oder die Strecke kartografisch visualisiert werden soll. Auch triggern bei Formulierungen wie "Linie auf Karte zeigen", "Haltestellen geocodieren", "Buslinie XY visualisieren", "Fahrtweg berechnen", "Strecke routen" — selbst wenn das Wort "Skill" nicht fällt. Erwartet ein PDF mit lesbarem Text (kein Scan); optional eine CSV mit Haltestellen-Stammdaten (Name + Koordinaten) als Geokoordinatenquelle und/oder eine .env mit Google Maps API Token. Liefert eine CSV der Haltestellen mit Koordinaten und eine interaktive Leaflet-HTML-Karte mit dem berechneten Fahrtweg via Google Routes API und/oder OSRM.
---

# Linienvisualisierung

PDF → interaktive Karte mit Linienverlauf. Der Workflow ist **iterativ und dialoggetrieben** — wichtig ist die Logik der einzelnen Schritte, nicht das stumpfe Ausführen von Skripten.

## Grundhaltung

Die mitgelieferten Skripte unter `scripts/` sind **Referenzimplementierungen**, die für ein spezifisches PDF-Layout (VRM Westerwald, Verkehrsbetrieb Rhein-Westerwald) funktionieren. Andere Verkehrsverbünde haben andere Layouts: andere Zeitformate, andere Tabellenstruktur, andere Hierarchie-Markierungen. **Nie blind ein Skript laufen lassen und annehmen, das Ergebnis stimmt.** Stattdessen:

1. Die Eingabedatei kurz **inspizieren** (Read-Tool, ein paar Zeilen) bevor Code läuft.
2. Skript laufen lassen oder Logik inline schreiben, je nachdem was besser passt.
3. Zwischenergebnis **prüfen** — sieht die Stop-Liste plausibel aus? Sind Koordinaten dabei? Macht die Route geografisch Sinn?
4. Bei Abweichungen mit dem Nutzer **abstimmen**, nicht raten.

Wenn ein Skript nicht zum PDF-Format passt, schreib die Parser-Logik inline in einem Python-Snippet (mit den Heuristiken aus diesem Dokument) oder pass das Skript für den Einzelfall an. Beides ist okay. Das Ziel ist eine korrekte Karte, nicht ein Skript, das durchläuft.

## Wann anwenden

Sobald der Nutzer ein Fahrplan-PDF hat (Bus, Bahn, Tram) und den Linienverlauf, die Haltestellen oder den Fahrtweg auf einer Karte sehen will. Funktioniert nur bei textbasierten PDFs (kein gescannter Bildtyp).

## Workflow

```
PDF
 │
 ├─[1] pdftotext -layout                    → linie.txt
 │
 ├─[2] Stops extrahieren (Heuristik)        → linie_haltestellen.csv  (x,y leer)
 │     ↳ mit Nutzer abstimmen
 │
 ├─[3] Koordinaten ergänzen                  → linie_haltestellen.csv  (mit x,y)
 │     a) aus Master-CSV (vrm_haltestellen.csv etc.) ODER
 │     b) Geocoding (Nominatim/Google)
 │     ↳ Abweichungen mit Nutzer klären
 │
 ├─[4] Liniennummer ergänzen                 → linie_haltestellen.csv  (vollständig)
 │
 ├─[5] Routing                                → linie_route_*.json
 │     a) Google Routes API (mit Token)
 │     b) OSRM (kostenlos, immer verfügbar)
 │     ↳ beides geht parallel
 │
 └─[6] Leaflet-HTML rendern                  → linie_karte.html
```

## Eingaben — vor dem Start klären

- **PDF-Pfad**
- **Master-CSV mit Haltestellen** (optional) — wenn vorhanden, viel präziser als Geocoding. Spalten typisch: Name + Lon/Lat. Beispiel: `vrm_haltestellen.csv` mit Spalten `title,centerx,centery`.
- **Google Maps API Token** (optional) — für Google Routes API. Such-Reihenfolge:
  1. Umgebungsvariable `TOKEN` (oder `GOOGLE_MAPS_API_KEY`, `GOOGLE_API_KEY`, `GMAPS_KEY`)
  2. `.env` im aktuellen Workspace (projekt-spezifisch)
  3. Globale Konfig (system-übergreifend, einmalig pro Nutzer):
     - **macOS:** `~/Library/Application Support/bc-claude/linien-visualisierung/.env`
     - **Linux:** `~/.config/bc-claude/linien-visualisierung/.env` (oder `$XDG_CONFIG_HOME/bc-claude/...`)
     - **Windows:** `%APPDATA%\bc-claude\linien-visualisierung\.env`
     - Universeller Fallback (alle OS): `~/.config/bc-claude/linien-visualisierung/.env`

  Ohne Token läuft alles über OSRM weiter — Google ist optional.

### Token-Setup — frag einmal, dann nie wieder

Das Verhalten zur Laufzeit:

1. Vor dem Routing-Schritt prüfen, ob ein Token verfügbar ist (env var, Workspace-`.env`, OS-typische globale `.env`).
2. **Wenn nichts da ist:** den Nutzer **genau einmal** fragen — kurze, klare Frage, keine technischen Details.
3. Den eingegebenen Token mit dem Helfer-Script `scripts/save_token.py` speichern. Es legt den Token an der OS-typischen Stelle ab und ist plattformübergreifend (macOS / Linux / Windows).
4. Anschließend `route_google.py` laufen lassen — der Token wird jetzt aus der frisch geschriebenen `.env` gelesen.
5. Bei künftigen Läufen (gleiche oder andere Projekte) findet der Skript den Token automatisch und fragt nicht mehr nach.

**Beispielablauf:**

```bash
# 1. Token-Ziel anzeigen (zur Info)
python3 scripts/save_token.py --print-path
# → /Users/.../Library/Application Support/bc-claude/linien-visualisierung/.env

# 2. Token speichern (Argument oder via stdin, je nachdem wie der Nutzer ihn liefert)
python3 scripts/save_token.py "AIzaSy..."
# oder:
echo "AIzaSy..." | python3 scripts/save_token.py -

# 3. Routing wie gewohnt — Token wird automatisch geladen
python3 scripts/route_google.py --stops linie_haltestellen.csv --output linie_route_google.json
```

**Cowork-Kontext (wichtig):** wenn der Skill in Cowork läuft, sieht die Sandbox `~/Library/Application Support/...` standardmäßig nicht — der Sandbox-Home ist isoliert. Damit der Token in **künftigen** Cowork-Sessions gefunden wird, muss Claude den OS-Pfad **einmal** als Verzeichnis verbinden:

```
- Pfad ermitteln:  python3 scripts/save_token.py --print-path
- Verzeichnis-Übergeordneten anlegen (wenn noch nicht da, via Bash auf Host)
- request_cowork_directory(<eltern-pfad>)  → Nutzer bestätigt einmal
- Token mit save_token.py speichern (jetzt sichtbar für Sandbox)
```

In Cowork-spezifischen Setups ist alternativ auch eine Workspace-`.env` ein vollwertiger Weg. Die OS-globale Variante ist der schönere Default für Claude Code und für Nutzer, die mehrere Linien in verschiedenen Ordnern visualisieren.

**Wenn der Nutzer einen Token in einer Workspace-`.env` hat:** nichts tun, der existierende Wert wird vorrangig benutzt. Nicht ungefragt in den globalen Pfad kopieren — das ist Privatsache des Nutzers.

Wenn der Nutzer nicht ausdrücklich etwas zur Master-CSV oder zur .env sagt, kurz im Workspace und an den globalen Pfaden nachsehen — die Dateien sind oft schon da.

---

## Schritt 1 — PDF zu Text

```bash
pdftotext -layout input.pdf input.txt
```

`-layout` ist wichtig: ohne diesen Flag werden Tabellenspalten zu Fließtext verschmolzen. Falls `pdftotext` fehlt, Paket `poppler-utils` installieren.

**Verifizieren:** kurz `head -40 input.txt` anschauen. Wenn nur Sonderzeichen und kaum Buchstaben rauskommen, ist es vermutlich ein Scan-PDF — Workflow stoppen, Nutzer informieren, OCR ist ein anderer Workflow (`ocrmypdf`, `tesseract`).

---

## Schritt 2 — Haltestellen extrahieren

**Ziel:** eine eindeutige, geordnete Liste aller physischen Haltestellen der Linie.

### Kern-Heuristik (Layout-Text der meisten Fahrplan-PDFs)

- Eine **Stop-Zeile** hat: `<Name>` + 2+ Leerzeichen + `<Uhrzeit>`. Uhrzeit-Muster ist meist `HH.MM` oder `HH:MM`.
- Zeilen, die mit `- ` (Bindestrich + Leerzeichen) beginnen, **erben den Stadt-Prefix** der vorigen Zeile mit vollem Namen (`Puderbach Verbandsgemeinde` → `- Hölzchens Mühle` wird zu `Puderbach Hölzchens Mühle`).
- `an` / `ab` am Zeilenende sind Ankunfts/Abfahrts-Marker derselben Haltestelle — die zweite Zeile ist redundant für den Linienverlauf.
- **Bussteig-Suffix** (einzelner Großbuchstabe am Ende, z.B. `A`, `B`, `D`, `H`) markiert Bussteigseiten. Beim Zusammenführen der Richtungen normalisieren — sonst zählt jede Bussteigseite als eigene Haltestelle.
- PDFs haben oft mehrere Tabellen (Mo-Fr, Sa, So, beide Richtungen). Stop-Liste über alle Tabellen sammeln und per Erst-Vorkommen deduplizieren.

### Referenzimplementierung

```bash
python3 scripts/extract_stops.py linie.txt linie_haltestellen.csv
# --keep-platform behält Bussteig-Suffix (selten gewünscht)
```

Output: CSV mit Spalten `haltestelle, x, y, linie` (x/y/linie zunächst leer).

### Format-Variationen, die abweichen können

Wenn das Skript komische Ergebnisse liefert (zu wenige Stops, falsche Reihenfolge, fehlende Stadtnamen, viele leere Zeilen), liegt es meist an einem dieser Punkte. **In dem Fall die Logik inline neu schreiben** — die Heuristiken oben sind der Kern, das Drumherum lässt sich anpassen:

- **Anderes Zeitformat** (`15h30`, `1530`, `15:30 Uhr`): Regex anpassen.
- **Tabulator-getrennte Spalten** statt Leerzeichen: das Skript erwartet 2+ Spaces.
- **Andere Hierarchie-Markierung** (Einrückung statt `- `, Punkt statt Bindestrich): die `head.startswith('- ')`-Logik anpassen.
- **Mehrere Linien in einem PDF** (z.B. Linie 5 und 7 zusammen): erst nach Linien-Header (`B 100`, `Linie 5` o.Ä.) splitten, dann pro Linie extrahieren.
- **Spalten-Layout statt Zeilen-Layout** (Stops in Spalten, Zeiten in Zeilen): pdftotext-Output anders parsen, oder mit `-table` versuchen.
- **Englische/französische `arr`/`dep`** statt `an`/`ab`.

Für komplett anderes Layout: ein Inline-Python-Snippet schreiben, das die Heuristiken oben sinngemäß umsetzt. Ist meist 30–50 Zeilen Code.

### Verifizieren mit dem Nutzer

Nach Extraktion die Liste **vorzeigen** (Anzahl + die ersten 5 und letzten 5 Stops, oder die ganze Liste wenn sie kurz ist) und auf Plausibilität prüfen lassen, **bevor** Schritt 3 läuft. Wenn der Nutzer Korrekturen hat, einarbeiten.

---

## Schritt 3 — Koordinaten ergänzen

### Variante A: Master-CSV vorhanden

Master-CSVs aus dem Verkehrsverbund haben typischerweise tausende Haltestellen mit Koordinaten. Spalten heißen oft `title`, `centerx`, `centery` (oder `name`, `lon`, `lat`).

```bash
python3 scripts/match_coords.py --stops linie_haltestellen.csv \
                                --master vrm_haltestellen.csv
```

Das Skript probiert in dieser Reihenfolge:
1. **Exakter Match** auf normalisiertem Namen (lowercase, Whitespace, `Straße`/`Str.` egalisiert).
2. **Komma-Variante**: aus `Stadt Stop` wird `Stadt, Stop` (häufiges Muster in Master-CSVs).
3. **Substring-Match**: Master-Eintrag enthält den Stop-Namen.

**Bei Nicht-Treffern oder leichten Abweichungen** — die häufigsten Muster in der Praxis:
- Stadtteile als zusätzlicher Prefix in Master-CSV (`Wienau Flemmer` vs. `Dierdorf, Wienau, Flemmer`)
- Andere Stadt-Zuordnung (`Gladbach Haus am Pilz` vs. `Neuwied, Haus am Pilz`)
- Abkürzungen (`Straße` vs. `Str.`)
- Schreibvarianten (`ß` vs. `ss`, Bindestriche, Leerzeichen)

→ **dem Nutzer eine Tabelle mit Vorschlägen zeigen**, einzeln bestätigen lassen, dann mit `--map "alter Name=neuer Name"` (mehrfach möglich) oder direkt CSV editieren.

Wenn die Master-CSV ein ganz anderes Format hat (z.B. GeoJSON, GTFS stops.txt, XML), entweder das Skript anpassen oder die CSV einmalig in das erwartete Format konvertieren — beides ist legitim.

### Variante B: Keine Master-CSV — Geocoding

```bash
python3 scripts/match_coords.py --stops linie_haltestellen.csv --geocode \
        --region-hint ", Germany"
```

Nutzt Nominatim (OpenStreetMap), kostenlos aber rate-limited (1 req/sec). Genauigkeit ist mäßig — Haltestellennamen sind oft mehrdeutig. Ergebnisse stichprobenartig prüfen.

Alternative: Google Geocoding API über das gleiche Token wie für Routing — falls Nominatim zu ungenau ist, kann ein angepasstes Skript stattdessen Google verwenden. Endpoint: `https://maps.googleapis.com/maps/api/geocode/json?address=…&key=…`.

### Verifizieren

Nach dem Match: **wie viele Treffer, wie viele Lücken**. Bei Lücken: gemeinsam mit Nutzer durchgehen.

---

## Schritt 4 — Liniennummer ergänzen

Aus dem PDF-Header übernehmen (`B 100`, `Linie 7`, `RE 25`, `Tram 2`). Einfach in die `linie`-Spalte schreiben.

---

## Schritt 5 — Routing

Echter Fahrtweg im Straßennetz, nicht Luftlinie.

### Google Routes API

```bash
python3 scripts/route_google.py --stops linie_haltestellen.csv \
                                --output linie_route_google.json
```

Wichtig:
- Nutzt die **neue Routes API** (`routes.googleapis.com/directions/v2:computeRoutes`), nicht die deprecated Legacy Directions API.
- Routes API muss im Google Cloud Projekt **aktiviert** sein.
- Maximal 25 Zwischenpunkte pro Request — bei mehr Stops splittet das Skript automatisch in Etappen mit 1-Punkt-Überlappung.

Typische Stolpersteine — bei diesen Fehlermeldungen den Nutzer informieren statt stumm zu retryen:
- `SERVICE_DISABLED` → Routes API in der Cloud Console aktivieren (Link kommt in der Fehlermeldung mit).
- `IP address restriction` → Key entweder ohne IP-Restriktion betreiben oder die ausführende IP zur Allowlist hinzufügen. Bei Cowork-Sandbox ist die IP nicht stabil, deshalb ist eine HTTP-Referrer-Restriktion hier praktikabler.
- `OVER_DAILY_LIMIT` / `OVER_QUERY_LIMIT` → Quota erschöpft, am nächsten Tag wieder oder OSRM-Fallback.

### OSRM (immer verfügbar)

```bash
python3 scripts/route_osrm.py --stops linie_haltestellen.csv \
                              --output linie_route_osrm.json
```

Nutzt die öffentliche Instanz `router.project-osrm.org`. Für deutsche Straßennetze in der Regel sehr brauchbar, kostenlos, kein Key. Gut als Fallback oder zum Vergleich neben Google.

Beide Output-JSONs haben dasselbe Schema:
```json
{ "coords": [[lat, lon], ...], "distance_km": 43.5, "duration_min": 77, "engine": "..." }
```

### Wenn beides geht

Beide gleichzeitig laufen lassen und dem Nutzer als Vergleich zeigen. Unterschiede entstehen häufig in Innenstadt-Schleifen (Einbahnstraßen) und bei der Straßenwahl außerorts.

---

## Schritt 6 — Karte rendern

```bash
python3 scripts/render_map.py \
        --stops linie_haltestellen.csv \
        --routes linie_route_google.json linie_route_osrm.json \
        --output linie_karte.html \
        --title "Linie B 100" \
        --subtitle "Puderbach – Neuwied"
```

Erzeugt eine eigenständige HTML mit Leaflet, OpenStreetMap-Tiles, nummerierten Markern und togglebaren Routen-Layern.

Bei Sonderwünschen (eigene Tile-Quelle, eigene Farben, andere Marker, Cluster bei vielen Stops): das Skript ist klein und gut lesbar — direkt in der HTML-Generierung anpassen oder die HTML-Datei nachträglich editieren.

---

## Outputs (Konvention)

Alles im Workspace-Ordner ablegen, Dateinamen mit Linienkennung als Prefix, damit mehrere Linien parallel funktionieren:

- `100_haltestellen.csv` — finale Liste mit Koordinaten und Linie
- `100_route_google.json` (optional)
- `100_route_osrm.json` (optional)
- `100_karte.html` — die fertige Karte

---

## Iteration mit dem Nutzer

Dieser Workflow lebt vom Dialog. Praktische Ankerpunkte:

- **Nach Schritt 2:** Stop-Liste + Anzahl zeigen, Plausibilität prüfen lassen.
- **Nach Schritt 3:** Match-Statistik (`X/Y mit Koordinaten`), Abweichungen explizit nennen, Bestätigung holen.
- **Nach Schritt 5:** Streckenlänge, Fahrzeit. Auffälligkeiten (z.B. Routing nimmt eine unplausible Strecke) zeigen.
- **Am Ende:** Map-Link, kurze Statistik. Anbieten, Polylinien-Probleme zu glätten (Innenstadt-Schleifen → zwei separate Routen für Hin/Rück, etc.).

Bei API-Fehlern oder unerwarteten Daten: nicht stumm retryen, sondern dem Nutzer Optionen anbieten.

---

## Bekannte Edge Cases

- **Scan-PDFs**: pdftotext liefert leeren oder unsinnigen Output. OCR-Workflow (anderer Skill).
- **Mehrere Linien in einem PDF**: vor der Extraktion splitten oder mehrfach durchlaufen, jeweils den richtigen Abschnitt parsen.
- **Innenstadt-Schleifen**: Hin- und Rückrichtung haben unterschiedliche Routen im Stadtkern. Eine zusammengeführte Polyline zeigt dort einen Zickzack. Wenn das stört: Nutzer fragen, ob zwei separate Polylines (Hin/Rück) gewünscht sind.
- **Halt am gleichen Bahnhof, verschiedene Bussteige**: standardmäßig zu einem Eintrag normalisiert. Falls beide Bussteige getrennt erscheinen sollen, `--keep-platform` setzen.
- **Sehr lange Linien (>200 Stops)**: Google Routes API muss in mehrere Etappen, OSRM-URL kann zu lang werden — dann OSRM-Anfrage per POST oder lokale OSRM-Instanz.
- **Bedarfshaltestellen** (B-Stellen, nur auf Anforderung): in der Tabelle oft mit Klammer oder `B`-Symbol markiert. Standardmäßig wie normale Stops behandeln; falls der Nutzer sie ausschließen will, Filter ergänzen.

---

## Skript-Übersicht

| Skript | Zweck | Inputs | Output |
|---|---|---|---|
| `scripts/extract_stops.py` | Layout-Text → Stops-CSV | `.txt` | CSV mit `haltestelle,x,y,linie` |
| `scripts/match_coords.py` | Stops + Master-CSV / Geocoding → Stops mit Koordinaten | CSV | dieselbe CSV (in-place) |
| `scripts/route_google.py` | Stops → Google-Route-JSON | CSV, `.env` | JSON |
| `scripts/route_osrm.py` | Stops → OSRM-Route-JSON | CSV | JSON |
| `scripts/render_map.py` | Stops + Routen → Leaflet-HTML | CSV, JSON(s) | HTML |
| `scripts/save_token.py` | Token an OS-typischer Stelle persistieren (einmalig) | Token | `.env` an OS-globalem Pfad |

Alle Skripte sind in einer Datei, kein Build, nur Python 3 stdlib + `pdftotext` (CLI). Können als Vorlage benutzt oder per Inline-Snippet ersetzt werden.
