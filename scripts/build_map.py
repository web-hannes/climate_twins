#!/usr/bin/env python3
"""
Build script: downloads Natural Earth 110m countries GeoJSON, projects to
Albers Equal Area Conic, outputs docs/data/europe-paths.json.
"""
import json, math, urllib.request, os, sys

# ── Equirectangular projection with aspect-ratio correction at 50 °N ──────────
# Meridians are straight vertical lines → map is correctly north-up.
COS50 = math.cos(math.radians(50.0))   # ≈ 0.6428

def project(lon_deg, lat_deg):
    x = (lon_deg - 10.0) * COS50   # 10 °E as central meridian
    y =  lat_deg                    # latitude as y
    return x, y

# ── Bounding box — Central Europe + southern twin range ──────────────────────
LON_MIN, LON_MAX = -8, 30
LAT_MIN, LAT_MAX = 41, 57

# ── Download Natural Earth 110m ───────────────────────────────────────────────
URL   = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
         "master/geojson/ne_110m_admin_0_countries.geojson")
CACHE = "/tmp/ne_110m_countries.geojson"

if os.path.exists(CACHE):
    print(f"Using cached {CACHE}")
    with open(CACHE) as f:
        data = json.load(f)
else:
    print(f"Downloading {URL} …")
    with urllib.request.urlopen(URL, timeout=30) as resp:
        raw = resp.read()
    data = json.loads(raw)
    with open(CACHE, 'w') as f:
        json.dump(data, f)
    print("Done.")

# ── Project a coordinate ring ─────────────────────────────────────────────────
def project_ring(ring):
    return [project(coord[0], coord[1]) for coord in ring]

# ── Collect European features ─────────────────────────────────────────────────
all_pts = []
features = []

for feat in data.get('features', []):
    geom  = feat.get('geometry') or {}
    props = feat.get('properties') or {}
    gtype = geom.get('type')
    if gtype not in ('Polygon', 'MultiPolygon'):
        continue

    raw_rings = []
    if gtype == 'Polygon':
        raw_rings = geom['coordinates']
    else:
        for poly in geom['coordinates']:
            raw_rings.extend(poly)

    flat = [c for ring in raw_rings for c in ring]
    if not flat:
        continue
    lons = [c[0] for c in flat]
    lats = [c[1] for c in flat]
    if max(lons) < LON_MIN or min(lons) > LON_MAX:
        continue
    if max(lats) < LAT_MIN or min(lats) > LAT_MAX:
        continue

    proj_rings = [project_ring(r) for r in raw_rings]
    proj_rings = [r for r in proj_rings if len(r) >= 3]
    if not proj_rings:
        continue

    for r in proj_rings:
        all_pts.extend(r)

    features.append({
        'iso':   props.get('ISO_A2', ''),
        'name':  props.get('NAME', ''),
        'rings': proj_rings,
    })

if not all_pts:
    sys.exit("ERROR: no projected points — check internet connection or bbox")

print(f"Features in bbox: {len(features)}")

# ── Compute scale & translation from bbox corners (not data extents) ──────────
# This ensures the desired area fills the canvas regardless of outlier coords.
VW, VH = 820, 560
MARGIN = 24

corner_pts = [project(lon, lat)
              for lon in (LON_MIN, LON_MAX)
              for lat in (LAT_MIN, LAT_MAX)]
xs = [p[0] for p in corner_pts]
ys = [p[1] for p in corner_pts]
xmin, xmax = min(xs), max(xs)
ymin, ymax = min(ys), max(ys)

scale = min((VW - 2*MARGIN) / (xmax - xmin),
            (VH - 2*MARGIN) / (ymax - ymin))

pw = (xmax - xmin) * scale
ph = (ymax - ymin) * scale
tx = (VW - pw) / 2 - xmin * scale
ty = (VH + ph) / 2 + ymin * scale  # SVG y is flipped

def to_svg(px, py):
    return round(px * scale + tx, 1), round(-py * scale + ty, 1)

# ── Build SVG path strings ────────────────────────────────────────────────────
def ring_path(ring):
    parts = []
    for i, pt in enumerate(ring):
        sx, sy = to_svg(*pt)
        parts.append(f"{'M' if i == 0 else 'L'}{sx},{sy}")
    return ''.join(parts) + 'Z'

out_features = []
for feat in features:
    out_features.append({
        'iso':   feat['iso'],
        'name':  feat['name'],
        'paths': [ring_path(r) for r in feat['rings']],
    })

# ── Cities ────────────────────────────────────────────────────────────────────
CITIES = [
    {'name': 'Berlin',    'lat': 52.52, 'lon': 13.41, 'plz': '10115'},
    {'name': 'Hamburg',   'lat': 53.55, 'lon': 10.00, 'plz': '20095'},
    {'name': 'München',   'lat': 48.14, 'lon': 11.58, 'plz': '80331'},
    {'name': 'Köln',      'lat': 50.94, 'lon':  6.96, 'plz': '50667'},
    {'name': 'Frankfurt', 'lat': 50.11, 'lon':  8.68, 'plz': '60311'},
    {'name': 'Leipzig',   'lat': 51.34, 'lon': 12.37, 'plz': '04109'},
    {'name': 'Stuttgart', 'lat': 48.78, 'lon':  9.18, 'plz': '70173'},
    {'name': 'Dresden',   'lat': 51.05, 'lon': 13.74, 'plz': '01067'},
]

out_cities = []
for c in CITIES:
    p = project(c['lon'], c['lat'])
    if p:
        sx, sy = to_svg(*p)
        out_cities.append({'name': c['name'], 'plz': c['plz'], 'x': sx, 'y': sy})

# ── Write output ──────────────────────────────────────────────────────────────
out_dir  = os.path.join(os.path.dirname(__file__), '..', 'docs', 'data')
out_path = os.path.join(out_dir, 'europe-paths.json')

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump({
        'vw': VW, 'vh': VH,
        'proj': {'cos50': round(COS50, 6), 'scale': round(scale, 4),
                 'tx': round(tx, 4), 'ty': round(ty, 4)},
        'features': out_features,
        'cities': out_cities,
    }, f, separators=(',', ':'), ensure_ascii=False)

size = os.path.getsize(out_path)
print(f"Written {out_path}  ({size/1024:.1f} KB)")
print(f"Features: {len(out_features)}, Cities: {len(out_cities)}")
