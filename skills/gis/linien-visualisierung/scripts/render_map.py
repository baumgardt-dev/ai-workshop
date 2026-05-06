#!/usr/bin/env python3
"""
Render an interactive Leaflet HTML map showing bus stops and one or more
driving routes. Uses OpenStreetMap tiles.

Each route JSON should have the shape produced by route_google.py / route_osrm.py:
    { "coords": [[lat, lon], ...], "distance_km": N, "duration_min": N, "engine": "..." }

Multiple routes are drawn as separate, toggleable layers (useful for comparing
Google vs OSRM, or hin- vs Rückrichtung).

Usage:
    python3 render_map.py --stops stops.csv --routes route1.json route2.json \\
                          --output karte.html --title "Linie B 100"
"""
import argparse
import csv
import json
import os


COLORS = ['#c8102e', '#1e88e5', '#43a047', '#fb8c00', '#8e24aa', '#00838f']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stops', required=True)
    p.add_argument('--routes', nargs='*', default=[], help='one or more route JSON files')
    p.add_argument('--output', required=True)
    p.add_argument('--title', default='Linienverlauf')
    p.add_argument('--subtitle', default='')
    args = p.parse_args()

    stops = []
    with open(args.stops, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if not row.get('x') or not row.get('y'):
                continue
            stops.append({
                'name': row['haltestelle'],
                'lon': float(row['x']),
                'lat': float(row['y']),
                'linie': row.get('linie', ''),
            })

    routes = []
    for i, path in enumerate(args.routes):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        label = data.get('engine', os.path.basename(path).replace('.json', ''))
        routes.append({
            'label': label,
            'coords': data['coords'],
            'distance_km': data.get('distance_km'),
            'duration_min': data.get('duration_min'),
            'color': COLORS[i % len(COLORS)],
            'dashed': i > 0,
        })

    stops_json = json.dumps(stops, ensure_ascii=False)
    routes_json = json.dumps(routes, ensure_ascii=False)

    legend_html = ''
    for i, r in enumerate(routes):
        dist = f"{r['distance_km']} km" if r['distance_km'] is not None else ''
        dur = f"{r['duration_min']} min" if r['duration_min'] is not None else ''
        meta = ' · '.join(x for x in [dist, dur] if x)
        legend_html += (
            f'<label><input type="checkbox" id="cb-{i}" checked>'
            f'<span class="swatch" style="background:{r["color"]}"></span>'
            f'<b>{r["label"]}</b>'
            f'{" — " + meta if meta else ""}'
            f'</label>'
        )

    subtitle_block = (
        f'<div class="meta">{args.subtitle}<br>{len(stops)} Haltestellen</div>'
        if args.subtitle else f'<div class="meta">{len(stops)} Haltestellen</div>'
    )

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{args.title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
  html,body{{margin:0;height:100%;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
  #map{{height:100vh;width:100%}}
  .info{{
    position:absolute;top:12px;left:60px;z-index:1000;
    background:white;padding:12px 16px;border-radius:8px;
    box-shadow:0 2px 6px rgba(0,0,0,.25);font-size:14px;line-height:1.5;
    max-width:340px
  }}
  .info b{{color:#333;font-size:15px}}
  .info .meta{{color:#555;font-size:13px;margin-top:6px}}
  .legend{{margin-top:8px;border-top:1px solid #eee;padding-top:8px}}
  .legend label{{display:block;cursor:pointer;padding:3px 0;font-size:13px}}
  .legend .swatch{{display:inline-block;width:20px;height:4px;vertical-align:middle;margin-right:8px;border-radius:2px}}
  .stop-label{{
    background:#333;color:white;border-radius:50%;
    width:24px;height:24px;text-align:center;line-height:24px;
    font-size:11px;font-weight:bold;border:2px solid white;
    box-shadow:0 0 4px rgba(0,0,0,.4)
  }}
</style>
</head>
<body>
<div id="map"></div>
<div class="info">
  <b>{args.title}</b>
  {subtitle_block}
  <div class="legend">{legend_html}</div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const stops = {stops_json};
const routes = {routes_json};

const map = L.map('map');
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  attribution: '© OpenStreetMap contributors',
  maxZoom: 19
}}).addTo(map);

const lines = routes.map((r, i) => {{
  const opts = {{color: r.color, weight: 5, opacity: i === 0 ? 0.85 : 0.65}};
  if (r.dashed) opts.dashArray = '8,6';
  return L.polyline(r.coords, opts).addTo(map);
}});

stops.forEach((s, i) => {{
  const icon = L.divIcon({{
    className: '',
    html: `<div class="stop-label">${{i+1}}</div>`,
    iconSize: [24,24], iconAnchor: [12,12]
  }});
  L.marker([s.lat, s.lon], {{icon}})
    .addTo(map)
    .bindPopup(`<b>${{i+1}}. ${{s.name}}</b>` +
               (s.linie ? `<br>Linie ${{s.linie}}` : '') +
               `<br><small>${{s.lat.toFixed(5)}}, ${{s.lon.toFixed(5)}}</small>`);
}});

if (lines.length) {{
  map.fitBounds(lines[0].getBounds(), {{padding: [40,40]}});
}} else if (stops.length) {{
  map.fitBounds(stops.map(s => [s.lat, s.lon]), {{padding: [40,40]}});
}}

routes.forEach((r, i) => {{
  const cb = document.getElementById('cb-' + i);
  if (cb) cb.addEventListener('change', e => {{
    e.target.checked ? lines[i].addTo(map) : map.removeLayer(lines[i]);
  }});
}});
</script>
</body>
</html>
"""
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"→ {args.output} ({len(html)} bytes, {len(stops)} stops, {len(routes)} routes)")


if __name__ == '__main__':
    main()
