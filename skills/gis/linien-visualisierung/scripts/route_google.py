#!/usr/bin/env python3
"""
Compute the driving route through a list of bus stops using the Google Routes API
(routes.googleapis.com/directions/v2:computeRoutes).

The Routes API is the current Google routing API. The legacy "Directions API" is
deprecated for new projects and may not be enabled. If you get SERVICE_DISABLED,
enable Routes API in the Cloud Console for the project the key belongs to.

Limit: 25 intermediate waypoints per request → 27 stops max per call. The script
splits longer routes into segments and stitches the polylines together.

Token-Suchreihenfolge (erstes Treffer gewinnt):
    1. Umgebungsvariable TOKEN (oder GOOGLE_MAPS_API_KEY, GOOGLE_API_KEY, GMAPS_KEY)
    2. .env im aktuellen Arbeitsverzeichnis (projekt-spezifisch)
    3. Globale Konfig (system-übergreifend) — siehe global_config_paths():
         macOS:   ~/Library/Application Support/bc-claude/linien-visualisierung/.env
         Linux:   ~/.config/bc-claude/linien-visualisierung/.env
                  ($XDG_CONFIG_HOME/bc-claude/...) wenn gesetzt
         Windows: %APPDATA%\\bc-claude\\linien-visualisierung\\.env
       Plus universeller Fallback ~/.config/bc-claude/linien-visualisierung/.env.

Usage:
    python3 route_google.py --stops stops.csv --output route_google.json
    python3 route_google.py --stops stops.csv --output out.json --env-key TOKEN
"""
import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
MAX_WAYPOINTS = 25  # = 27 total points per call (origin + 25 intermediates + dest)


def global_config_paths():
    """Return [(label, Path), ...] of candidate global config locations,
    in priority order. The first entry is the preferred write location for
    this OS; later entries are read fallbacks for portability."""
    home = Path.home()
    candidates = []

    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA')
        if appdata:
            candidates.append(('Windows %APPDATA%', Path(appdata)))
    elif sys.platform == 'darwin':
        candidates.append(('macOS Application Support',
                           home / 'Library' / 'Application Support'))

    xdg = os.environ.get('XDG_CONFIG_HOME')
    if xdg:
        candidates.append(('$XDG_CONFIG_HOME', Path(xdg)))

    # Universal fallback — works on any OS, also matches Linux convention.
    candidates.append(('~/.config', home / '.config'))

    seen = set()
    out = []
    for label, base in candidates:
        path = base / 'bc-claude' / 'linien-visualisierung' / '.env'
        if path not in seen:
            seen.add(path)
            out.append((label, path))
    return out


def preferred_global_path():
    """The path to write a new token to on this OS."""
    return global_config_paths()[0][1]


def _read_key_from_env_file(path, env_key):
    """Return the value of env_key from a .env file, or None."""
    try:
        if not Path(path).exists():
            return None
    except OSError:
        return None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            if k.strip() == env_key:
                return v.strip().strip('"').strip("'")
    return None


def load_env_token(env_key='TOKEN', env_path='.env'):
    """Look up the API key in this order: env var → CWD .env → global config(s).
    Returns (token, source) where source describes where it came from, or
    (None, None) if nothing was found."""
    if env_key in os.environ:
        return os.environ[env_key], f'env:{env_key}'
    for alt in ('GOOGLE_MAPS_API_KEY', 'GOOGLE_API_KEY', 'GMAPS_KEY'):
        if alt in os.environ:
            return os.environ[alt], f'env:{alt}'
    val = _read_key_from_env_file(env_path, env_key)
    if val:
        return val, f'cwd:{env_path}'
    for label, path in global_config_paths():
        val = _read_key_from_env_file(path, env_key)
        if val:
            return val, f'global ({label}): {path}'
    return None, None


def call_routes_api(points, api_key):
    body = {
        "origin": {"location": {"latLng": {"latitude": points[0]['lat'], "longitude": points[0]['lon']}}},
        "destination": {"location": {"latLng": {"latitude": points[-1]['lat'], "longitude": points[-1]['lon']}}},
        "intermediates": [
            {"location": {"latLng": {"latitude": p['lat'], "longitude": p['lon']}}}
            for p in points[1:-1]
        ],
        "travelMode": "DRIVE",
        "polylineEncoding": "ENCODED_POLYLINE",
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": (
                "routes.duration,routes.distanceMeters,"
                "routes.polyline.encodedPolyline,"
                "routes.legs.distanceMeters,routes.legs.duration"
            ),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}


def decode_polyline(s):
    """Decode Google's encoded polyline format. Returns list of [lat, lon]."""
    coords, i, lat, lng = [], 0, 0, 0
    while i < len(s):
        for j in range(2):
            shift, result = 0, 0
            while True:
                b = ord(s[i]) - 63; i += 1
                result |= (b & 0x1f) << shift; shift += 5
                if b < 0x20: break
            d = ~(result >> 1) if result & 1 else result >> 1
            if j == 0: lat += d
            else: lng += d
        coords.append([lat * 1e-5, lng * 1e-5])
    return coords


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stops', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--env-key', default='TOKEN', help='env var / .env key name')
    p.add_argument('--env-file', default='.env')
    args = p.parse_args()

    api_key, source = load_env_token(args.env_key, args.env_file)
    if not api_key:
        searched = [f"env var '{args.env_key}'", f"'{args.env_file}'"]
        for label, path in global_config_paths():
            searched.append(f"{path} ({label})")
        preferred = preferred_global_path()
        msg = [
            "Kein Google Maps API Token gefunden.",
            "  Gesucht in:",
        ] + [f"    - {s}" for s in searched] + [
            "",
            f"  → Bitte den Token einmalig speichern unter:",
            f"     {preferred}",
            f"     mit Inhalt: TOKEN=<dein-key>",
            "",
            "  Oder OSRM statt Google nutzen (route_osrm.py).",
        ]
        raise SystemExit("\n".join(msg))
    print(f"Token-Quelle: {source}", file=sys.stderr)

    stops = []
    with open(args.stops, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not row.get('x') or not row.get('y'):
                print(f"  skipping (no coords): {row['haltestelle']}", file=sys.stderr)
                continue
            stops.append({
                'name': row['haltestelle'],
                'lat': float(row['y']),
                'lon': float(row['x']),
            })

    if len(stops) < 2:
        raise SystemExit("Need at least 2 stops with coordinates")

    # Split into segments of max MAX_WAYPOINTS + 2 points, with 1-point overlap
    seg_size = MAX_WAYPOINTS + 2  # = 27
    segments = []
    i = 0
    while i < len(stops):
        end = min(i + seg_size, len(stops))
        segments.append(stops[i:end])
        if end >= len(stops):
            break
        i = end - 1  # overlap by one point

    all_coords = []
    total_dist = 0
    total_time = 0
    leg_distances = []
    for idx, seg in enumerate(segments, 1):
        print(f"Segment {idx}/{len(segments)}: {len(seg)} points "
              f"({seg[0]['name']} → {seg[-1]['name']})", file=sys.stderr)
        res = call_routes_api(seg, api_key)
        if 'error' in res:
            raise SystemExit(f"Google API error:\n{res['error']}")
        if not res.get('routes'):
            raise SystemExit(f"No route returned: {json.dumps(res)[:300]}")
        route = res['routes'][0]
        coords = decode_polyline(route['polyline']['encodedPolyline'])
        if idx > 1 and all_coords:
            coords = coords[1:]
        all_coords.extend(coords)
        total_dist += route['distanceMeters']
        total_time += int(route['duration'].rstrip('s'))
        for leg in route.get('legs', []):
            leg_distances.append(leg['distanceMeters'])

    out = {
        'coords': all_coords,
        'distance_km': round(total_dist / 1000, 2),
        'duration_min': round(total_time / 60),
        'leg_distances_m': leg_distances,
        'engine': 'google-routes',
    }
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(out, f)
    print(f"→ {out['distance_km']} km · {out['duration_min']} min · "
          f"{len(all_coords)} polyline points → {args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()
