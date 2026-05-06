#!/usr/bin/env python3
"""
Add coordinates to a stops CSV.

Two modes:
  --master <csv>   Match stops against a master coordinate table (e.g. a transit
                   association's stop database). Reports unmatched and ambiguous
                   stops to stderr so the caller can confirm with the user.
  --geocode        Fall back to Nominatim geocoding via OpenStreetMap. Slower,
                   rate-limited (1 request/second), and accuracy varies.

Stops CSV format (in/out): haltestelle, x, y, linie
Master CSV format (auto-detected): looks for a 'title' or 'name' column for the
stop name and 'centerx'/'lon'/'longitude' + 'centery'/'lat'/'latitude' for coords.

Usage:
    python3 match_coords.py --stops stops.csv --master vrm_haltestellen.csv
    python3 match_coords.py --stops stops.csv --geocode
    python3 match_coords.py --stops stops.csv --master m.csv --map "Foo=Town, Foo"
"""
import argparse
import csv
import re
import sys
import time
import urllib.parse
import urllib.request
import json


def normalize(s):
    """Normalize a stop name for matching: lowercase, collapse whitespace, strip
    common punctuation differences (Straße/Str., comma)."""
    s = s.lower()
    s = re.sub(r'straße', 'str', s)
    s = re.sub(r'\bstr\.', 'str', s)
    s = re.sub(r'[.,]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def detect_master_columns(fieldnames):
    """Return (name_col, x_col, y_col) for a master CSV."""
    fl = [f.lower() for f in fieldnames]
    name = None
    for c in ('title', 'name', 'stop_name', 'haltestelle'):
        if c in fl:
            name = fieldnames[fl.index(c)]; break
    x = None
    for c in ('centerx', 'lon', 'longitude', 'x'):
        if c in fl:
            x = fieldnames[fl.index(c)]; break
    y = None
    for c in ('centery', 'lat', 'latitude', 'y'):
        if c in fl:
            y = fieldnames[fl.index(c)]; break
    if not (name and x and y):
        raise SystemExit(f"Master CSV missing required columns. Found: {fieldnames}")
    return name, x, y


def load_master(path):
    """Return dict normalized_name → (raw_title, x, y) and list of (raw_title, x, y) for fallback search."""
    by_norm = {}
    rows = []
    with open(path, encoding='utf-8') as f:
        r = csv.DictReader(f)
        name_col, x_col, y_col = detect_master_columns(r.fieldnames)
        for row in r:
            title = (row[name_col] or '').strip().strip('"')
            if not title or not row[x_col] or not row[y_col]:
                continue
            entry = (title, row[x_col], row[y_col])
            rows.append(entry)
            n = normalize(title)
            if n not in by_norm:
                by_norm[n] = entry
    return by_norm, rows


def match_against_master(stop_name, by_norm, rows):
    """Return (matched_title, x, y, score) where score is one of:
    'exact', 'normalized', 'substring', None (no match)."""
    n_stop = normalize(stop_name)

    # 1. Exact normalized match
    if n_stop in by_norm:
        title, x, y = by_norm[n_stop]
        return (title, x, y, 'exact' if title == stop_name else 'normalized')

    # 2. Try with comma between first word and rest (City Stop → "City, Stop")
    parts = stop_name.split(None, 1)
    if len(parts) == 2:
        with_comma = f"{parts[0]}, {parts[1]}"
        n_alt = normalize(with_comma)
        if n_alt in by_norm:
            title, x, y = by_norm[n_alt]
            return (title, x, y, 'normalized')

    # 3. Substring: master title ends with the stop name
    candidates = []
    for title, x, y in rows:
        if n_stop in normalize(title):
            candidates.append((title, x, y))
    if len(candidates) == 1:
        title, x, y = candidates[0]
        return (title, x, y, 'substring')
    if len(candidates) > 1:
        # ambiguous — prefer shortest title
        candidates.sort(key=lambda c: len(c[0]))
        title, x, y = candidates[0]
        return (title, x, y, 'substring-ambiguous')

    return (None, None, None, None)


def geocode_nominatim(query, lang='de'):
    """Return (lon, lat) from Nominatim or (None, None)."""
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode({
        'q': query,
        'format': 'json',
        'limit': '1',
        'accept-language': lang,
    })
    req = urllib.request.Request(url, headers={'User-Agent': 'linien-visualisierung/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if data:
            return data[0]['lon'], data[0]['lat']
    except Exception as e:
        print(f"  geocode error for '{query}': {e}", file=sys.stderr)
    return None, None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stops', required=True, help='input/output stops CSV')
    p.add_argument('--master', help='master coordinate CSV')
    p.add_argument('--geocode', action='store_true', help='use Nominatim geocoding')
    p.add_argument('--map', action='append', default=[],
                   help='manual mapping "stop=master title" (repeatable)')
    p.add_argument('--region-hint', default='',
                   help='string appended to geocoding queries (e.g. ", Germany")')
    args = p.parse_args()

    if not args.master and not args.geocode:
        raise SystemExit("Provide either --master <csv> or --geocode")

    manual_map = {}
    for m in args.map:
        if '=' in m:
            k, v = m.split('=', 1)
            manual_map[k.strip()] = v.strip()

    rows_out = []
    needs_confirmation = []  # (stop, master_title, score)
    unmatched = []

    with open(args.stops, encoding='utf-8') as f:
        r = csv.DictReader(f)
        stops = list(r)

    if args.master:
        by_norm, master_rows = load_master(args.master)
        for row in stops:
            name = row['haltestelle']
            if name in manual_map:
                target_norm = normalize(manual_map[name])
                if target_norm in by_norm:
                    title, x, y = by_norm[target_norm]
                    row['x'], row['y'] = x, y
                    rows_out.append(row)
                    continue
            title, x, y, score = match_against_master(name, by_norm, master_rows)
            if score in ('exact',):
                row['x'], row['y'] = x, y
            elif score in ('normalized', 'substring'):
                row['x'], row['y'] = x, y
                if normalize(title) != normalize(name):
                    needs_confirmation.append((name, title, score))
            elif score == 'substring-ambiguous':
                row['x'], row['y'] = x, y
                needs_confirmation.append((name, title, score))
            else:
                unmatched.append(name)
            rows_out.append(row)

    if args.geocode:
        for row in rows_out if rows_out else stops:
            if row.get('x'):
                continue
            q = row['haltestelle'] + args.region_hint
            print(f"  geocoding: {q}", file=sys.stderr)
            lon, lat = geocode_nominatim(q)
            if lon and lat:
                row['x'], row['y'] = lon, lat
            else:
                if row['haltestelle'] not in unmatched:
                    unmatched.append(row['haltestelle'])
            time.sleep(1.0)  # Nominatim policy
        if not rows_out:
            rows_out = stops

    # Write back
    with open(args.stops, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['haltestelle', 'x', 'y', 'linie'])
        w.writeheader()
        for row in rows_out:
            w.writerow({k: row.get(k, '') for k in ('haltestelle', 'x', 'y', 'linie')})

    if needs_confirmation:
        print("\nHinweis: Folgende Treffer weichen leicht ab — bitte mit Nutzer prüfen:", file=sys.stderr)
        for name, title, score in needs_confirmation:
            print(f"  '{name}'  →  '{title}'  ({score})", file=sys.stderr)
    if unmatched:
        print(f"\nKeine Koordinaten gefunden für ({len(unmatched)}):", file=sys.stderr)
        for n in unmatched:
            print(f"  {n}", file=sys.stderr)
    matched = sum(1 for r in rows_out if r.get('x'))
    print(f"\n{matched}/{len(rows_out)} stops with coordinates → {args.stops}", file=sys.stderr)


if __name__ == '__main__':
    main()
