#!/usr/bin/env python3
"""
Compute the driving route through bus stops using the public OSRM instance.
Free, no API key required.

Public OSRM (router.project-osrm.org) is a community service — fine for
prototypes and personal projects, but for production load consider hosting
your own or using a commercial provider.

Usage:
    python3 route_osrm.py --stops stops.csv --output route_osrm.json
"""
import argparse
import csv
import json
import sys
import urllib.error
import urllib.request


BASE = "https://router.project-osrm.org/route/v1/driving/"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stops', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--profile', default='driving',
                   help='OSRM profile (driving/cycling/walking; public OSRM only has driving)')
    args = p.parse_args()

    points = []
    with open(args.stops, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not row.get('x') or not row.get('y'):
                print(f"  skipping (no coords): {row['haltestelle']}", file=sys.stderr)
                continue
            points.append((row['x'], row['y']))

    if len(points) < 2:
        raise SystemExit("Need at least 2 stops with coordinates")

    coord_str = ";".join(f"{lon},{lat}" for lon, lat in points)
    url = f"https://router.project-osrm.org/route/v1/{args.profile}/{coord_str}?overview=full&geometries=geojson"

    print(f"OSRM request: {len(points)} points", file=sys.stderr)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"OSRM HTTP error {e.code}: {e.read().decode()[:300]}")

    if data.get('code') != 'Ok':
        raise SystemExit(f"OSRM error: {data}")

    route = data['routes'][0]
    coords = [[lat, lon] for lon, lat in route['geometry']['coordinates']]
    out = {
        'coords': coords,
        'distance_km': round(route['distance'] / 1000, 2),
        'duration_min': round(route['duration'] / 60),
        'leg_distances_m': [leg['distance'] for leg in route['legs']],
        'engine': 'osrm',
    }
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(out, f)
    print(f"→ {out['distance_km']} km · {out['duration_min']} min · "
          f"{len(coords)} polyline points → {args.output}", file=sys.stderr)


if __name__ == '__main__':
    main()
