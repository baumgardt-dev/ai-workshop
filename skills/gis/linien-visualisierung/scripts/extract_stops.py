#!/usr/bin/env python3
"""
Extract bus/train stop list from a layout-preserved text dump of a timetable PDF.

Strategy: walk every line of the text. A stop row is one that has at least one
time entry (HH.MM or HH:MM) preceded by 2+ spaces — this picks up rows in any of
the timetable variants (Mon-Fri, Sat, Sun, both directions). Each stop is
recorded the first time it appears; later occurrences (same stop in a different
direction or weekday table) are deduplicated.

Heuristics applied to the stop name:
  - Rows starting with "- xxx" inherit the town prefix from the most recent
    full-name row.
  - "an"/"ab" markers indicate arrival/departure of the same physical stop —
    redundant for the route, dropped.
  - Single uppercase letter at end of name = bus platform (Bussteig). Stripped
    by default so direction A and direction B merge to one entry. Use
    --keep-platform to preserve them.

This produces a single list of unique physical stops in route order. For PDFs
with one-way city loops, the order may have the loop stops out of geographic
sequence — flag that to the user when displaying the list.

Usage:
    python3 extract_stops.py <input-text> <output-csv> [--keep-platform]
"""
import re
import sys
import csv
import argparse


TIME_RE = re.compile(r'\d{1,2}[.:]\d{2}')
ROW_RE = re.compile(r'^(.*?)\s{2,}\d{1,2}[.:]\d{2}')


def parse_stops_from_text(text, keep_platform=False):
    """Return a deduplicated list of stops in first-occurrence order."""
    current_town = None
    seen_bases = set()
    stops_in_order = []

    def base(name):
        if keep_platform:
            return name
        # Strip trailing single uppercase letter (bus platform) when preceded by space
        return re.sub(r'\s+[A-Z]$', '', name)

    for ln in text.splitlines():
        if not TIME_RE.search(ln):
            # Page numbers, blank lines, headers — keep current_town across them.
            continue
        m = ROW_RE.search(ln)
        if not m:
            continue
        head = m.group(1).strip()
        # strip trailing "an" / "ab" markers
        head = re.sub(r'\s+(an|ab)\s*$', '', head)
        if head.startswith('- '):
            stop = head[2:].strip()
            if not current_town:
                # Page-break or unusual order put a "- xxx" before any anchor.
                # Skip rather than emit a town-less stop.
                continue
            full = f"{current_town} {stop}"
        else:
            parts = head.split(None, 1)
            current_town = parts[0]
            full = head
        b = base(full)
        if b in seen_bases:
            continue
        seen_bases.add(b)
        stops_in_order.append(b)
    return stops_in_order


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', help='layout text file from pdftotext -layout')
    p.add_argument('output', help='output CSV path')
    p.add_argument('--keep-platform', action='store_true',
                   help='keep bus platform suffix (single uppercase letter)')
    args = p.parse_args()

    with open(args.input, encoding='utf-8') as f:
        text = f.read()

    stops = parse_stops_from_text(text, keep_platform=args.keep_platform)

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['haltestelle', 'x', 'y', 'linie'])
        for s in stops:
            w.writerow([s, '', '', ''])

    print(f"{len(stops)} stops extracted → {args.output}", file=sys.stderr)
    for i, s in enumerate(stops, 1):
        print(f"{i:>2}. {s}", file=sys.stderr)


if __name__ == '__main__':
    main()
