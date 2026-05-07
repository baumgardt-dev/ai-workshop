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


def _derive_geojson_path(output_json_path):
    """Replace .json suffix with .geojson, or append .geojson if no .json suffix."""
    if output_json_path.lower().endswith('.json'):
        return output_json_path[:-5] + '.geojson'
    return output_json_path + '.geojson'


def write_geojson(path, engine, line_coords, stops, distance_km, duration_min):
    """Write a FeatureCollection with one LineString (the route) and one Point per stop.

    line_coords: list of [lon, lat] in GeoJSON order (as returned by OSRM/Google).
    stops: list of dicts with name, lon, lat, linie.
    """
    features = [{
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': [[lon, lat] for lon, lat in line_coords],
        },
        'properties': {
            'engine': engine,
            'distance_km': distance_km,
            'duration_min': duration_min,
            'kind': 'route',
        },
    }]
    for i, s in enumerate(stops, 1):
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [s['lon'], s['lat']],
            },
            'properties': {
                'name': s['name'],
                'order': i,
                'linie': s.get('linie', ''),
                'kind': 'stop',
            },
        })
    fc = {'type': 'FeatureCollection', 'features': features}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(fc, f, ensure_ascii=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stops', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--geojson', default=None,
                   help='GeoJSON output path (default: --output mit .geojson statt .json)')
    p.add_argument('--profile', default='driving',
                   help='OSRM profile (driving/cycling/walking; public OSRM only has driving)')
    args = p.parse_args()

    stops = []
    with open(args.stops, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not row.get('x') or not row.get('y'):
                print(f"  skipping (no coords): {row['haltestelle']}", file=sys.stderr)
                continue
            stops.append({
                'name': row['haltestelle'],
                'lon': float(row['x']),
                'lat': float(row['y']),
                'linie': row.get('linie', ''),
            })

    if len(stops) < 2:
        raise SystemExit("Need at least 2 stops with coordinates")

    coord_str = ";".join(f"{s['lon']},{s['lat']}" for s in stops)
    url = f"https://router.project-osrm.org/route/v1/{args.profile}/{coord_str}?overview=full&geometries=geojson"

    print(f"OSRM request: {len(stops)} points", file=sys.stderr)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"OSRM HTTP error {e.code}: {e.read().decode()[:300]}")

    if data.get('code') != 'Ok':
        raise SystemExit(f"OSRM error: {data}")

    route = data['routes'][0]
    coords = [[lat, lon] for lon, lat in route['geometry']['coordinates']]
    distance_km = round(route['distance'] / 1000, 2)
    duration_min = round(route['duration'] / 60)
    out = {
        'coords': coords,
        'distance_km': distance_km,
        'duration_min': duration_min,
        'leg_distances_m': [leg['distance'] for leg in route['legs']],
        'engine': 'osrm',
    }
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(out, f)
    print(f"→ {out['distance_km']} km · {out['duration_min']} min · "
          f"{len(coords)} polyline points → {args.output}", file=sys.stderr)

    geojson_path = args.geojson or _derive_geojson_path(args.output)
    write_geojson(
        path=geojson_path,
        engine='osrm',
        line_coords=route['geometry']['coordinates'],
        stops=stops,
        distance_km=distance_km,
        duration_min=duration_min,
    )
    print(f"→ {geojson_path} (GeoJSON)", file=sys.stderr)


if __name__ == '__main__':
    main()
