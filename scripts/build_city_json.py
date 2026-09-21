"""
Liest PLZ → lat/lon aus DE.txt, tastet WorldClim 2.1 GeoTIFFs ab,
schreibt docs/data/cities/{plz}.json.

Aufruf:
  python scripts/build_city_json.py 93047
  python scripts/build_city_json.py 93047 80331 10115   # mehrere
  python scripts/build_city_json.py --all               # alle PLZ in DE.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import pathlib
import sys
from typing import Optional

import numpy as np
import rasterio

# ── Pfade ──────────────────────────────────────────────────────────────────────
ROOT      = pathlib.Path(__file__).parent.parent
DE_TXT    = ROOT / "data" / "DE.txt"
WC_DIR    = ROOT / "data" / "worldclim_2.1"
OUT_DIR   = ROOT / "docs" / "data" / "cities"

MODELS  = ["EC-Earth3-Veg", "IPSL-CM6A-LR", "MIROC6", "MPI-ESM1-2-HR", "MRI-ESM2-0"]
PERIODS = ["2021-2040", "2041-2060", "2061-2080", "2081-2100"]
VARS    = ["tmin", "tmax", "prec"]


# ── PLZ-Lookup ─────────────────────────────────────────────────────────────────

def load_plz_db() -> dict:
    """Liest DE.txt und gibt {plz: {name, state, lat, lon}} zurück.
    Bei mehreren Einträgen pro PLZ wird gemittelt (Zentroid der PLZ-Fläche)."""
    db: dict[str, dict] = {}
    with open(DE_TXT, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 11:
                continue
            plz, name, state = parts[1], parts[2], parts[3]
            try:
                lat, lon = float(parts[9]), float(parts[10])
            except ValueError:
                continue
            if plz not in db:
                db[plz] = {"name": name, "state": state, "lats": [lat], "lons": [lon]}
            else:
                db[plz]["lats"].append(lat)
                db[plz]["lons"].append(lon)

    # Mittelwert pro PLZ
    result = {}
    for plz, v in db.items():
        result[plz] = {
            "name":  v["name"],
            "state": v["state"],
            "lat":   round(float(np.mean(v["lats"])), 6),
            "lon":   round(float(np.mean(v["lons"])), 6),
        }
    return result


# ── WorldClim-Abtastung ────────────────────────────────────────────────────────

def _nodata_guard(val: float, nodata) -> Optional[float]:
    if math.isnan(val):
        return None
    if nodata is not None and not math.isnan(nodata) and abs(val - nodata) < 1:
        return None
    return round(float(val), 3)


def sample_monthly_files(var: str, lon: float, lat: float) -> list:
    """12 Einzel-TIFFs (historisch) → Liste mit 12 Werten."""
    folder = WC_DIR / "1970-2000" / f"wc2.1_10m_{var}"
    vals = []
    for m in range(1, 13):
        path = folder / f"wc2.1_10m_{var}_{m:02d}.tif"
        if not path.exists():
            raise FileNotFoundError(f"WorldClim-Datei fehlt: {path}")
        with rasterio.open(path) as src:
            v = list(src.sample([(lon, lat)]))[0][0]
            vals.append(_nodata_guard(float(v), src.nodata))
    return vals


def sample_multiband(path: pathlib.Path, lon: float, lat: float) -> list:
    """12-Band-GeoTIFF (Zukunft) → Liste mit 12 Werten."""
    if not path.exists():
        raise FileNotFoundError(f"WorldClim-Datei fehlt: {path}")
    with rasterio.open(path) as src:
        row = list(src.sample([(lon, lat)]))[0]
        return [_nodata_guard(float(v), src.nodata) for v in row]


def build_climate(lon: float, lat: float) -> dict:
    historical = {}
    for var in VARS:
        historical[var] = sample_monthly_files(var, lon, lat)

    future = {}
    for period in PERIODS:
        future[period] = {}
        for model in MODELS:
            future[period][model] = {}
            for var in VARS:
                fname = f"wc2.1_10m_{var}_{model}_ssp245_{period}.tif"
                path = WC_DIR / period / fname
                future[period][model][var] = sample_multiband(path, lon, lat)

    return {"historical": historical, "future": future}


# ── Hauptfunktion ──────────────────────────────────────────────────────────────

def build(plz: str, db: dict) -> None:
    if plz not in db:
        print(f"  {plz}: nicht in DE.txt gefunden – übersprungen")
        return

    info = db[plz]
    print(f"  {plz} {info['name']} ({info['state']})  "
          f"{info['lat']:.4f}N {info['lon']:.4f}E", end=" ... ", flush=True)

    climate = build_climate(info["lon"], info["lat"])

    payload = {
        "plz":   plz,
        "name":  info["name"],
        "state": info["state"],
        "lat":   info["lat"],
        "lon":   info["lon"],
        **climate,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{plz}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    print(f"→ {out_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plz", nargs="*", help="PLZ(s) zum Verarbeiten")
    parser.add_argument("--all", action="store_true", help="Alle PLZ in DE.txt")
    args = parser.parse_args()

    if not args.plz and not args.all:
        parser.print_help()
        sys.exit(1)

    print("Lade PLZ-Datenbank …")
    db = load_plz_db()
    print(f"  {len(db):,} eindeutige PLZ geladen\n")

    targets = list(db.keys()) if args.all else args.plz

    for plz in targets:
        build(plz.strip(), db)


if __name__ == "__main__":
    main()
