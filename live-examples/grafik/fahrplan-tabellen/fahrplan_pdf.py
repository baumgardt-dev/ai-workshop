#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fahrplan_pdf.py
===============
Erzeugt aus einer JSON-Fahrplandatei eine DIN-A4-PDF im Stil eines
Linien-Fahrplans (Bus/Bahn), wie er in gedruckten Fahrplanbüchern steht.

Aufruf:
    python3 fahrplan_pdf.py EINGABE.json [-o AUSGABE.pdf]

Benötigt: weasyprint  (pip install weasyprint)

Das JSON-Schema ist bewusst flexibel gehalten, sodass auch andere
Linien / Fahrpläne abgebildet werden können. Siehe README.md.
"""

import argparse
import html
import json
import os
import sys


# --------------------------------------------------------------------------
# Farb-Hilfen
# --------------------------------------------------------------------------
def _hex_to_rgb(hexstr):
    hexstr = hexstr.lstrip("#")
    if len(hexstr) == 3:
        hexstr = "".join(c * 2 for c in hexstr)
    return tuple(int(hexstr[i:i + 2], 16) for i in (0, 2, 4))


def _mix_white(hexstr, amount):
    """Mischt eine Farbe Richtung Weiß. amount=0 -> Originalfarbe, 1 -> weiß."""
    r, g, b = _hex_to_rgb(hexstr)
    r = round(r + (255 - r) * amount)
    g = round(g + (255 - g) * amount)
    b = round(b + (255 - b) * amount)
    return f"rgb({r},{g},{b})"


# --------------------------------------------------------------------------
# Symbole
# --------------------------------------------------------------------------
def _stop_symbol_html(symbol):
    """Kleines Symbol hinter einem Haltestellennamen (z.B. S-Bahn-Kringel)."""
    if not symbol:
        return ""
    if symbol.upper() == "S":
        return ('<span class="sym sym-s">S</span>')
    if symbol.upper() == "U":
        return ('<span class="sym sym-u">U</span>')
    # generisches Symbol: einfach als Text
    return f'<span class="sym sym-generic">{html.escape(symbol)}</span>'


BUS_SVG = (
    '<svg viewBox="0 0 64 32" class="vehicle-icon" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="2" y="3" width="54" height="20" rx="3" fill="#000"/>'
    '<rect x="6" y="7" width="10" height="8" fill="#fff"/>'
    '<rect x="19" y="7" width="10" height="8" fill="#fff"/>'
    '<rect x="32" y="7" width="10" height="8" fill="#fff"/>'
    '<rect x="45" y="7" width="8" height="8" fill="#fff"/>'
    '<circle cx="16" cy="25" r="5" fill="#000"/>'
    '<circle cx="44" cy="25" r="5" fill="#000"/>'
    '</svg>'
)

TRAIN_SVG = (
    '<svg viewBox="0 0 64 32" class="vehicle-icon" xmlns="http://www.w3.org/2000/svg">'
    '<rect x="6" y="2" width="46" height="22" rx="6" fill="#000"/>'
    '<rect x="11" y="6" width="16" height="9" fill="#fff"/>'
    '<rect x="31" y="6" width="16" height="9" fill="#fff"/>'
    '<circle cx="17" cy="27" r="4" fill="#000"/>'
    '<circle cx="41" cy="27" r="4" fill="#000"/>'
    '<rect x="2" y="22" width="6" height="3" fill="#000"/>'
    '<rect x="50" y="22" width="6" height="3" fill="#000"/>'
    '</svg>'
)


def _vehicle_icon(icon):
    if icon == "train":
        return TRAIN_SVG
    if icon == "none":
        return ""
    return BUS_SVG


# --------------------------------------------------------------------------
# HTML-Erzeugung
# --------------------------------------------------------------------------
def _render_section(section, stops):
    """Rendert eine Tages-Sektion (z.B. Montag–Freitag) als HTML-Tabelle."""
    color = section.get("color", "#666666")
    title = section.get("title", "")
    columns = section.get("columns", [])
    n_stops = len(stops)

    stripe_a = "#ffffff"
    stripe_b = _mix_white(color, 0.82)

    # --- Kopfzeile der Sektion (Tagestyp) ---
    parts = []
    parts.append(f'<table class="sec" style="--accent:{color};">')
    # colgroup: erste Spalte = Haltestellen, danach je eine pro Fahrt-Spalte
    parts.append("<colgroup>")
    parts.append('<col class="col-stop"/>')
    for col in columns:
        cls = "col-interval" if col.get("type") == "interval" else (
            "col-tri" if col.get("type") == "triangle" else "col-time")
        parts.append(f'<col class="{cls}"/>')
    parts.append("</colgroup>")

    # Titelbalken über die ganze Breite
    parts.append(
        f'<thead><tr class="sec-title"><th colspan="{len(columns) + 1}">'
        f'{html.escape(title)}</th></tr>'
    )

    # Marker-Zeile (Telefon-Icons / obere Dreiecke)
    marker_cells = ['<th class="mk-stop"></th>']
    for col in columns:
        ctype = col.get("type")
        if ctype == "interval":
            marker_cells.append('<th class="mk"></th>')
        elif ctype == "triangle":
            marker_cells.append(
                f'<th class="mk tri" style="color:{col.get("color", color)}">&#9660;</th>'
            )
        else:
            if col.get("header") == "phone":
                marker_cells.append('<th class="mk">&#9742;</th>')
            else:
                marker_cells.append('<th class="mk"></th>')
    parts.append('<tr class="mk-row">' + "".join(marker_cells) + "</tr></thead>")

    # --- Datenzeilen (Haltestellen) ---
    parts.append("<tbody>")
    interval_emitted = set()  # Spalten-Indizes, deren Interval-Zelle schon gesetzt wurde

    for r, stop in enumerate(stops):
        stripe = stripe_b if (r % 2 == 1) else stripe_a
        row_cls = "data-row"
        bold = stop.get("bold")
        name = html.escape(stop.get("name", ""))
        indent = "" if bold else "stop-indent"
        sym = _stop_symbol_html(stop.get("symbol"))
        namecell = (
            f'<td class="stopname {indent} {"b" if bold else ""}" '
            f'style="background:{stripe}">{name}{sym}</td>'
        )
        cells = [namecell]

        for ci, col in enumerate(columns):
            ctype = col.get("type")
            if ctype == "interval":
                if ci not in interval_emitted:
                    interval_emitted.add(ci)
                    txt = html.escape(col.get("text", ""))
                    cells.append(
                        f'<td class="interval" rowspan="{n_stops}">'
                        f'<div class="interval-txt">{txt}</div></td>'
                    )
                # in Folgezeilen keine Zelle (rowspan deckt ab)
                continue
            if ctype == "triangle":
                glyph = ""
                col_color = col.get("color", color)
                if r == 0:
                    glyph = "&#9660;"        # ▼ oben
                elif r == n_stops - 1:
                    glyph = "&#9650;"        # ▲ unten
                cells.append(
                    f'<td class="tri" style="background:{stripe};color:{col_color}">{glyph}</td>'
                )
                continue
            # normale Zeit-Spalte
            vals = col.get("cells", [])
            val = vals[r] if r < len(vals) else ""
            val = "" if val is None else str(val)
            big = "big" if (bold and val) else ""
            cells.append(
                f'<td class="time {big}" style="background:{stripe}">{html.escape(val)}</td>'
            )

        parts.append(f'<tr class="{row_cls}">' + "".join(cells) + "</tr>")

    parts.append("</tbody></table>")
    return "".join(parts)


def build_html(data):
    line = html.escape(str(data.get("line", "")))
    title = html.escape(data.get("title", ""))
    accent = data.get("accent", "#e2001a")
    icon = _vehicle_icon(data.get("icon", "bus"))
    stops = data.get("stops", [])
    footnote = data.get("footnote", "")

    # Blöcke: jeder Block enthält 1..n Sektionen nebeneinander
    blocks = data.get("blocks")
    if blocks is None:
        # Rückwärtskompatibel: flache Liste von Sektionen -> je ein Block
        blocks = [{"sections": [s]} for s in data.get("sections", [])]

    block_html = []
    for block in blocks:
        secs = block.get("sections", [])
        cells = "".join(
            f'<div class="sec-wrap">{_render_section(s, stops)}</div>' for s in secs
        )
        block_footnote = block.get("footnote", footnote)
        fn = (
            f'<div class="footnote">{_render_inline(block_footnote)}</div>'
            if block_footnote else ""
        )
        block_html.append(f'<div class="block"><div class="sec-grid">{cells}</div>{fn}</div>')

    css = _CSS.replace("__ACCENT__", accent)

    doc = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8"><style>{css}</style></head>
<body>
  <header class="page-head">
    <div class="head-icon">{icon}</div>
    <div class="head-line">{line}</div>
    <div class="head-title">{title}</div>
  </header>
  {''.join(block_html)}
</body></html>"""
    return doc


def _render_inline(text):
    """Erlaubt ein paar Inline-Ersetzungen in Fußnoten (Telefonsymbol)."""
    text = html.escape(text)
    text = text.replace("[phone]", "&#9742;").replace("{phone}", "&#9742;")
    return text


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
_CSS = """
@page {
    size: A4 portrait;
    margin: 10mm 8mm 10mm 8mm;
}
* { box-sizing: border-box; }
body {
    font-family: "Liberation Sans", "Arial", "DejaVu Sans", sans-serif;
    color: #000;
    margin: 0;
    -weasy-hyphens: none;
}

/* ---------- Kopf ---------- */
.page-head {
    border-top: 3px solid __ACCENT__;
    border-bottom: 3px solid __ACCENT__;
    padding: 3px 0;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.head-icon { width: 52px; flex: 0 0 auto; }
.vehicle-icon { width: 48px; height: 24px; display: block; }
.head-line {
    font-size: 26pt;
    font-weight: 700;
    flex: 0 0 auto;
    line-height: 1;
}
.head-title {
    font-size: 13pt;
    font-weight: 700;
    line-height: 1.05;
}

/* ---------- Block / Sektionen ---------- */
.block { margin-bottom: 10px; }
.sec-grid {
    display: flex;
    gap: 6px;
    align-items: flex-start;
}
.sec-wrap { flex: 1 1 0; min-width: 0; }

table.sec {
    border-collapse: collapse;
    width: 100%;
    table-layout: fixed;
}
col.col-stop  { width: 118px; }
col.col-time  { width: auto; }
col.col-tri   { width: 14px; }
col.col-interval { width: 16px; }

/* Titelbalken */
.sec-title th {
    background: var(--accent);
    color: #fff;
    font-size: 9pt;
    font-weight: 700;
    text-align: center;
    padding: 2px 0;
    letter-spacing: .2px;
}

/* Marker-Zeile (Telefon/Dreiecke) */
.mk-row th {
    height: 12px;
    font-size: 8pt;
    text-align: center;
    padding: 0;
    font-family: "DejaVu Sans", sans-serif;
    font-weight: normal;
}
.mk-row th.tri { font-size: 8pt; }

/* Datenzellen */
.data-row td {
    font-size: 7.4pt;
    padding: 0.7px 2px;
    white-space: nowrap;
    line-height: 1.18;
}
td.stopname {
    text-align: left;
    overflow: hidden;
    text-overflow: ellipsis;
}
td.stopname.stop-indent::before { content: "– "; }
td.stopname.b { font-weight: 700; }
td.time {
    text-align: right;
    font-variant-numeric: tabular-nums;
    padding-right: 4px;
}
td.time.big { font-weight: 700; }

/* Dreiecke / Richtungs-Spalte */
td.tri {
    text-align: center;
    font-family: "DejaVu Sans", sans-serif;
    font-size: 8pt;
    padding: 0;
}

/* Intervallspalte ("alle 30 Min.") */
td.interval {
    text-align: center;
    vertical-align: middle;
    padding: 0;
    background: #fff;
}
.interval-txt {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    font-size: 7pt;
    white-space: nowrap;
    margin: 0 auto;
}

/* Haltestellen-Symbole */
.sym {
    display: inline-block;
    margin-left: 3px;
    font-size: 6.6pt;
    font-weight: 700;
    line-height: 1;
}
.sym-s {
    background: #0a8f3c; color: #fff;
    border-radius: 50%;
    width: 10px; height: 10px;
    text-align: center;
}
.sym-u {
    background: #1d4ed8; color: #fff;
    border-radius: 2px;
    padding: 0 2px;
}

/* Fußnote */
.footnote {
    font-size: 6.6pt;
    margin-top: 3px;
    font-family: "DejaVu Sans", "Liberation Sans", sans-serif;
}
"""


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Fahrplan-JSON -> PDF (DIN A4)")
    ap.add_argument("input", help="Eingabe-JSON")
    ap.add_argument("-o", "--output", help="Ausgabe-PDF (Default: gleicher Name .pdf)")
    ap.add_argument("--html", help="optional: HTML zusätzlich speichern")
    ap.add_argument("--ai", nargs="?", const="__auto__",
                    help="zusätzlich eine Illustrator-kompatible .ai-Datei schreiben "
                         "(PDF-basiert, Text bleibt editierbar). Optional Pfad.")
    ap.add_argument("--svg", nargs="?", const="__auto__",
                    help="zusätzlich eine .svg-Datei schreiben (reine Vektorgrafik, "
                         "Text in Pfade umgewandelt). Optional Pfad.")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as fh:
        data = json.load(fh)

    out = args.output or os.path.splitext(args.input)[0] + ".pdf"
    base = os.path.splitext(out)[0]
    doc_html = build_html(data)

    if args.html:
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(doc_html)

    from weasyprint import HTML
    HTML(string=doc_html).write_pdf(out)
    print(f"PDF geschrieben: {out}")

    # ---- Illustrator-kompatible .ai (PDF-Container) ----
    # Eine .ai-Datei ab Illustrator 9 ist ein PDF-Container. Illustrator öffnet
    # diese PDF-basierte Datei und behandelt Text als editierbaren Text und
    # Rechtecke/Linien als echte Vektorobjekte.
    if args.ai is not None:
        ai_path = base + ".ai" if args.ai == "__auto__" else args.ai
        with open(out, "rb") as src, open(ai_path, "wb") as dst:
            dst.write(src.read())
        print(f"AI geschrieben:  {ai_path}")

    # ---- reine Vektor-SVG (Text als Pfade) ----
    if args.svg is not None:
        import shutil
        import subprocess
        svg_path = base + ".svg" if args.svg == "__auto__" else args.svg
        tool = shutil.which("pdftocairo")
        if tool:
            subprocess.run([tool, "-svg", out, svg_path], check=True)
            print(f"SVG geschrieben: {svg_path}")
        else:
            print("SVG übersprungen: 'pdftocairo' (poppler-utils) nicht gefunden.",
                  file=sys.stderr)


if __name__ == "__main__":
    main()
