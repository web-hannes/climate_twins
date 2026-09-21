"""
Klimazwilling – Matching-Skript

Zwei Modi:
  A  „historisch"  : Zielort 2041-2060  ↔  Kandidaten 1970-2000
  B  „aktuell"     : Zielort 2041-2060  ↔  Kandidaten 2021-2040 (Ens.-Mittel)

Ablauf:
  1. Kandidaten abtasten  (einmalig, → data/candidates_climate.csv)
  2. Zielorte laden       (data/cities/{plz}.json, bereits vorhanden)
  3. Matching berechnen   (saisonale Variablen, z-standardisiert, eukl. Distanz)
  4. Twins speichern      (data/cities/{plz}.json  ergänzt um "twins"-Schlüssel)

Aufruf:
  python scripts/build_twins.py --sample-candidates          # Schritt 1 einmalig
  python scripts/build_twins.py 93047 80331                  # Schritt 2-4 für PLZ
  python scripts/build_twins.py --all                        # alle vorhandenen JSONs
  python scripts/build_twins.py --all --skip-sampling        # ohne Schritt 1
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
from typing import Optional

import numpy as np
import pandas as pd
import rasterio
from scipy.spatial import cKDTree

# ── Pfade ──────────────────────────────────────────────────────────────────────
ROOT         = pathlib.Path(__file__).parent.parent
WC_DIR       = ROOT / "data" / "worldclim_2.1"
CANDIDATES   = ROOT / "data" / "candidates_eu.csv"
CAND_CLIMATE = ROOT / "data" / "candidates_climate.csv"
CITIES_DIR   = ROOT / "docs" / "data" / "cities"

MODELS         = ["EC-Earth3-Veg", "IPSL-CM6A-LR", "MIROC6", "MPI-ESM1-2-HR", "MRI-ESM2-0"]
VARS           = ["tmin", "tmax", "prec"]
# Monate 0-basiert
SEASONS        = {"DJF": [11, 0, 1], "MAM": [2, 3, 4], "JJA": [5, 6, 7], "SON": [8, 9, 10]}
FEAT_COLS      = [f"{v}_{s}" for v in ["tasmin", "tasmax", "pr"] for s in SEASONS]
TOP_K          = 5   # Anzahl Zwillinge je Modus
TARGET_PERIODS = ["2041-2060", "2061-2080"]


# ── Saisonale Aggregation ──────────────────────────────────────────────────────

def to_seasonal(monthly: dict) -> dict:
    """
    monthly: {"tmin": [12 Werte], "tmax": [...], "prec": [...]}
    → {"tasmin_DJF": ..., "tasmax_DJF": ..., "pr_DJF": ..., ...}
    """
    feat: dict = {}
    for s, months in SEASONS.items():
        feat[f"tasmin_{s}"] = float(np.mean([monthly["tmin"][m] for m in months]))
        feat[f"tasmax_{s}"] = float(np.mean([monthly["tmax"][m] for m in months]))
        feat[f"pr_{s}"]     = float(np.sum( [monthly["prec"][m] for m in months]))
    return feat


# ── Raster-Abtastung ───────────────────────────────────────────────────────────

def _nodata_guard(val: float, nodata) -> Optional[float]:
    if math.isnan(val):
        return None
    if nodata is not None and not math.isnan(nodata) and abs(val - nodata) < 1:
        return None
    return round(float(val), 3)


def sample_hist(lon: float, lat: float) -> Optional[dict]:
    """12 Einzel-TIFFs 1970-2000 → {tmin:[12], tmax:[12], prec:[12]}"""
    result: dict = {v: [] for v in VARS}
    for var in VARS:
        folder = WC_DIR / "1970-2000" / f"wc2.1_10m_{var}"
        for m in range(1, 13):
            path = folder / f"wc2.1_10m_{var}_{m:02d}.tif"
            if not path.exists():
                raise FileNotFoundError(f"WorldClim-Datei fehlt: {path}")
            with rasterio.open(path) as src:
                v = list(src.sample([(lon, lat)]))[0][0]
                val = _nodata_guard(float(v), src.nodata)
                if val is None:
                    return None  # NoData → Stadt überspringen
                result[var].append(val)
    return result


def sample_period_ensemble(lon: float, lat: float, period: str) -> Optional[dict]:
    """12-Band-GeoTIFFs → Ensemble-Mittel {tmin:[12], tmax:[12], prec:[12]}"""
    result: dict = {v: [] for v in VARS}
    for var in VARS:
        monthly_models = []
        for model in MODELS:
            fname = f"wc2.1_10m_{var}_{model}_ssp245_{period}.tif"
            path  = WC_DIR / period / fname
            if not path.exists():
                raise FileNotFoundError(f"WorldClim-Datei fehlt: {path}")
            with rasterio.open(path) as src:
                row = list(src.sample([(lon, lat)]))[0]
                bands = []
                for v in row:
                    val = _nodata_guard(float(v), src.nodata)
                    if val is None:
                        return None
                    bands.append(val)
                monthly_models.append(bands)
        # Ensemble-Mittel über Modelle, pro Monat
        ensemble = [float(np.mean([model[i] for model in monthly_models])) for i in range(12)]
        result[var] = [round(e, 3) for e in ensemble]
    return result


# ── Schritt 1: Kandidaten abtasten ────────────────────────────────────────────

def sample_candidates() -> None:
    df = pd.read_csv(CANDIDATES)
    print(f"Taste {len(df)} Kandidaten ab … (kann einige Minuten dauern)")

    rows = []
    skipped = 0
    for pos, (_, row) in enumerate(df.iterrows()):
        lon, lat = float(row.lon), float(row.lat)

        hist = sample_hist(lon, lat)
        p21  = sample_period_ensemble(lon, lat, "2021-2040")

        if hist is None or p21 is None:
            skipped += 1
            continue

        r = {
            "id":         row.id,
            "name":       row["name"],
            "ascii_name": row.ascii_name,
            "country":    row.country,
            "lat":        lat,
            "lon":        lon,
            "population": row.population,
        }
        r.update({f"hist_{k}": v  for k, v in to_seasonal(hist).items()})
        r.update({f"p21_{k}":  v  for k, v in to_seasonal(p21).items()})
        rows.append(r)

        if (pos + 1) % 100 == 0:
            print(f"  {pos+1}/{len(df)} …")

    result = pd.DataFrame(rows)
    result.to_csv(CAND_CLIMATE, index=False)
    print(f"\nFertig: {len(result)} Kandidaten gespeichert, {skipped} übersprungen (NoData)")
    print(f"→ {CAND_CLIMATE}")


# ── Schritt 2-4: Matching ─────────────────────────────────────────────────────

def build_twins(plz_list: list[str]) -> None:
    if not CAND_CLIMATE.exists():
        print("FEHLER: candidates_climate.csv nicht gefunden.")
        print("Bitte zuerst ausführen: python scripts/build_twins.py --sample-candidates")
        sys.exit(1)

    cands = pd.read_csv(CAND_CLIMATE)
    print(f"Kandidaten geladen: {len(cands)}")

    # Feature-Matrizen für beide Modi — NaN-Zeilen pro Modus separat filtern
    hist_cols = [f"hist_{c}" for c in FEAT_COLS]
    p21_cols  = [f"p21_{c}"  for c in FEAT_COLS]

    mask_hist = cands[hist_cols].notna().all(axis=1)
    mask_p21  = cands[p21_cols].notna().all(axis=1)
    cands_hist = cands[mask_hist].reset_index(drop=True)
    cands_p21  = cands[mask_p21].reset_index(drop=True)
    print(f"  Kandidaten nach NaN-Filter: Modus A {len(cands_hist)}, Modus B {len(cands_p21)}")

    P_hist = cands_hist[hist_cols].values.astype(float)
    P_p21  = cands_p21[p21_cols].values.astype(float)

    # Skalierungsparameter aus Kandidaten-Historik ableiten (Modus A)
    mu_hist = P_hist.mean(axis=0)
    sd_hist = P_hist.std(axis=0, ddof=0)
    sd_hist[sd_hist == 0] = 1  # Division durch 0 verhindern

    # Modus B: eigene Skalierung aus 2021-2040
    mu_p21 = P_p21.mean(axis=0)
    sd_p21 = P_p21.std(axis=0, ddof=0)
    sd_p21[sd_p21 == 0] = 1

    P_hist_z = (P_hist - mu_hist) / sd_hist
    P_p21_z  = (P_p21  - mu_p21)  / sd_p21

    tree_hist = cKDTree(P_hist_z)
    tree_p21  = cKDTree(P_p21_z)

    def make_twin(idx: int, dist: float, mode: str) -> dict:
        df = cands_hist if mode == "A" else cands_p21
        c  = df.iloc[idx]
        fk = "hist" if mode == "A" else "p21"
        return {
            "name":       c["name"],
            "ascii_name": c.ascii_name,
            "country":    c.country,
            "lat":        float(c.lat),
            "lon":        float(c.lon),
            "population": int(c.population),
            "distance":   round(float(dist), 4),
            "features": {
                k: round(float(c[f"{fk}_{k}"]), 2)
                for k in FEAT_COLS
            },
        }

    for plz in plz_list:
        json_path = CITIES_DIR / f"{plz}.json"
        if not json_path.exists():
            print(f"  {plz}: kein city JSON gefunden – übersprungen")
            continue

        city = json.loads(json_path.read_text())

        city["twins"] = {}
        for target_period in TARGET_PERIODS:
            fut_monthly = {
                var: [
                    round(float(np.mean(
                        [v for model in MODELS
                         if (v := city["future"][target_period][model][var][i]) is not None]
                        or [float("nan")]
                    )), 3)
                    for i in range(12)
                ]
                for var in VARS
            }
            fut_feat = to_seasonal(fut_monthly)
            F = np.array([fut_feat[c] for c in FEAT_COLS], dtype=float)
            if not np.isfinite(F).all():
                continue  # NoData in future raster for this period → skip

            F_hist_z = (F - mu_hist) / sd_hist
            dists_a, idxs_a = tree_hist.query(F_hist_z.reshape(1, -1), k=TOP_K)

            F_p21_z = (F - mu_p21) / sd_p21
            dists_b, idxs_b = tree_p21.query(F_p21_z.reshape(1, -1), k=TOP_K)

            city["twins"][target_period] = {
                "target_features": {k: round(v, 2) for k, v in fut_feat.items()},
                "mode_A": {
                    "label":      f"Zielort {target_period} ↔ Kandidaten 1970–2000",
                    "ref_period": "1970-2000",
                    "results":    [make_twin(idxs_a[0][i], dists_a[0][i], "A") for i in range(TOP_K)],
                },
                "mode_B": {
                    "label":      f"Zielort {target_period} ↔ Kandidaten 2021–2040",
                    "ref_period": "2021-2040",
                    "results":    [make_twin(idxs_b[0][i], dists_b[0][i], "B") for i in range(TOP_K)],
                },
            }

        if not city["twins"]:
            print(f"  {plz} {city['name']:20} übersprungen (NoData)")
            continue
        json_path.write_text(json.dumps(city, ensure_ascii=False, separators=(",", ":")))
        for tp in [p for p in TARGET_PERIODS if p in city["twins"]]:
            ta = city["twins"][tp]["mode_A"]["results"][0]
            tb = city["twins"][tp]["mode_B"]["results"][0]
            print(f"  {plz} {city['name']:20} [{tp}]  "
                  f"A→ {ta['name']} ({ta['country']}) d={ta['distance']:.2f}  "
                  f"B→ {tb['name']} ({tb['country']}) d={tb['distance']:.2f}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plz", nargs="*")
    parser.add_argument("--sample-candidates", action="store_true",
                        help="Kandidaten abtasten (einmalig, langsam)")
    parser.add_argument("--all", action="store_true",
                        help="Alle vorhandenen city JSONs verarbeiten")
    parser.add_argument("--skip-sampling", action="store_true",
                        help="Kandidaten-Sampling überspringen auch wenn --all")
    args = parser.parse_args()

    if args.sample_candidates:
        sample_candidates()

    plz_list = []
    if args.all:
        plz_list = [p.stem for p in sorted(CITIES_DIR.glob("?????.json"))]
        print(f"\nMatching für {len(plz_list)} PLZ …\n")
    elif args.plz:
        plz_list = args.plz

    if plz_list:
        build_twins(plz_list)


if __name__ == "__main__":
    main()
