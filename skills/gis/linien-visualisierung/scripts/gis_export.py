#!/usr/bin/env python3
"""
Finaler GIS-Export: zwei GeoJSON-Dateien pro Linie, jeweils mit dem vom
GIS-Konsumenten verlangten Attributschema.

Erzeugt zwei Dateien im Zielverzeichnis:

  HST_Linie<NR>.geojson
      FeatureCollection aus Punkten (eine pro Haltestelle).
      Properties pro Feature:
          Name      — Haltestellenname
          position  — Default 2
          linie     — Liniennummer (entspricht <NR>)
          label     — Default 1
          active    — Default 1

  Linie<NR>.geojson
      FeatureCollection mit genau einem LineString-Feature (Linienverlauf).
      Properties:
          NAME   — Liniennummer (entspricht <NR>)
          HEX    — Default "#000000"
          Farbe  — Default "000000"

Defaults sind so vorgegeben (alle Linien schwarz, position=2, label=1,
active=1). Über CLI-Flags überschreibbar, falls für einen Spezialfall nötig.

Inputs:
  --stops   CSV mit Spalten haltestelle,x,y,linie  (x=lon, y=lat)
  --route   Route-Datei: entweder das interne route_*.json
            ({"coords": [[lat, lon], ...]}) oder ein GeoJSON
            FeatureCollection (LineString daraus wird benutzt)
  --linie   Liniennummer (z.B. 5003) — bestimmt sowohl Dateinamen als
            auch die NAME- und linie-Properties.

Beispiel:
  python3 gis_export.py --stops 5003_haltestellen.csv \\
                         --route 5003_route_google.json \\
                         --linie 5003 \\
                         --out-dir .
"""
import argparse
import csv
import json
import sys
from pathlib import Path


DEFAULT_POSITION = 2
DEFAULT_LABEL = 1
DEFAULT_ACTIVE = 1
DEFAULT_HEX = '#000000'
DEFAULT_FARBE = '000000'


def load_stops(stops_csv):
    """Lies Haltestellen mit Koordinaten aus der CSV. Reihenfolge bleibt erhalten."""
    stops = []
    with open(stops_csv, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not row.get('x') or not row.get('y'):
                print(f"  übersprungen (keine Koords): {row.get('haltestelle','?')}",
                      file=sys.stderr)
                continue
            stops.append({
                'name': row['haltestelle'],
                'lon': float(row['x']),
                'lat': float(row['y']),
            })
    return stops


def load_route_coords_lonlat(route_path):
    """Liefert die LineString-Koordinaten als Liste von [lon, lat] (GeoJSON-Reihenfolge).

    Akzeptiert zwei Eingabeformate:
      - internes Format aus route_google.py / route_osrm.py:
            {"coords": [[lat, lon], ...]}
      - GeoJSON FeatureCollection mit einem LineString-Feature.
    """
    with open(route_path, encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict) and data.get('type') == 'FeatureCollection':
        for feat in data.get('features', []):
            geom = feat.get('geometry') or {}
            if geom.get('type') == 'LineString':
                return list(geom['coordinates'])
        raise SystemExit(f"Kein LineString in {route_path} gefunden.")

    if isinstance(data, dict) and 'coords' in data:
        # internes Format ist [lat, lon] → GeoJSON braucht [lon, lat]
        return [[lon, lat] for lat, lon in data['coords']]

    raise SystemExit(f"Unbekanntes Route-Format: {route_path}")


def write_stops_geojson(path, stops, linie, position, label, active):
    features = []
    for s in stops:
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [s['lon'], s['lat']],
            },
            'properties': {
                'Name': s['name'],
                'position': position,
                'linie': linie,
                'label': label,
                'active': active,
            },
        })
    fc = {'type': 'FeatureCollection', 'features': features}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(fc, f, ensure_ascii=False)


def write_line_geojson(path, line_coords_lonlat, linie, hex_color, farbe):
    feature = {
        'type': 'Feature',
        'geometry': {
            'type': 'LineString',
            'coordinates': line_coords_lonlat,
        },
        'properties': {
            'NAME': linie,
            'HEX': hex_color,
            'Farbe': farbe,
        },
    }
    fc = {'type': 'FeatureCollection', 'features': [feature]}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(fc, f, ensure_ascii=False)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--stops', required=True,
                   help='CSV mit Haltestellen (Spalten: haltestelle,x,y,linie)')
    p.add_argument('--route', required=True,
                   help='Routenfile aus route_google.py oder route_osrm.py '
                        '(.json oder .geojson)')
    p.add_argument('--linie', required=True,
                   help='Liniennummer — fließt in Dateinamen, NAME und linie-Property')
    p.add_argument('--out-dir', default='.',
                   help='Zielverzeichnis für die zwei GeoJSON-Dateien (Default: .)')
    p.add_argument('--prefix-stops', default='HST_Linie',
                   help='Dateiname-Präfix für Haltestellen (Default: HST_Linie)')
    p.add_argument('--prefix-line', default='Linie',
                   help='Dateiname-Präfix für Linienverlauf (Default: Linie)')
    p.add_argument('--position', type=int, default=DEFAULT_POSITION,
                   help=f'Wert für Property "position" (Default: {DEFAULT_POSITION})')
    p.add_argument('--label', type=int, default=DEFAULT_LABEL,
                   help=f'Wert für Property "label" (Default: {DEFAULT_LABEL})')
    p.add_argument('--active', type=int, default=DEFAULT_ACTIVE,
                   help=f'Wert für Property "active" (Default: {DEFAULT_ACTIVE})')
    p.add_argument('--hex', dest='hex_color', default=DEFAULT_HEX,
                   help=f'Wert für Property "HEX" (Default: {DEFAULT_HEX})')
    p.add_argument('--farbe', default=DEFAULT_FARBE,
                   help=f'Wert für Property "Farbe" (Default: {DEFAULT_FARBE})')
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stops = load_stops(args.stops)
    if not stops:
        raise SystemExit("Keine Haltestellen mit Koordinaten in der CSV gefunden.")

    line_coords = load_route_coords_lonlat(args.route)
    if len(line_coords) < 2:
        raise SystemExit("Linienverlauf hat weniger als 2 Punkte.")

    stops_path = out_dir / f"{args.prefix_stops}{args.linie}.geojson"
    line_path = out_dir / f"{args.prefix_line}{args.linie}.geojson"

    write_stops_geojson(stops_path, stops, args.linie,
                        args.position, args.label, args.active)
    write_line_geojson(line_path, line_coords, args.linie,
                       args.hex_color, args.farbe)

    print(f"→ {stops_path}  ({len(stops)} Haltestellen)", file=sys.stderr)
    print(f"→ {line_path}  ({len(line_coords)} Punkte im LineString)", file=sys.stderr)


if __name__ == '__main__':
    main()
