"""
Extrahiert Kandidatenstädte für Klimazwilling aus cities15000.txt (GeoNames).

Ausgabe: data/candidates_eu.csv
Felder:  id, name, ascii_name, country, lat, lon, population

Regionen:
  SOUTH_EU   — südeuropäische EU/Balkan-Länder
  CENTRAL_EU — Deutschland, Frankreich, Benelux, Alpenländer, Mittel-/Osteuropa
  EAST_EU    — Ukraine, Moldawien
  NORTH_AF   — Nordafrika (Marokko, Algerien, Tunesien, Libyen, Ägypten)
               relevant als Klimazwillinge für 2061–2100-Szenarien

Ausgeschlossen: Skandinavien, Britische Inseln, Baltikum

Mindestpopulation: 100.000 (anpassbar via MIN_POP)
"""

import csv
import pathlib
import sys

# ── Konfiguration ──────────────────────────────────────────────────────────────

INPUT   = pathlib.Path(__file__).parent.parent / "cities15000.txt"
OUT_DIR = pathlib.Path(__file__).parent.parent / "data"
OUTPUT  = OUT_DIR / "candidates_eu.csv"

MIN_POP = 25_000  # Mindesteinwohnerzahl

# Länder-Codes nach Region
SOUTH_EU = {
    "ES",  # Spanien
    "IT",  # Italien
    "PT",  # Portugal
    "GR",  # Griechenland
    "HR",  # Kroatien
    "SI",  # Slowenien
    "RS",  # Serbien
    "BA",  # Bosnien-Herzegowina
    "ME",  # Montenegro
    "MK",  # Nordmazedonien
    "AL",  # Albanien
    "MT",  # Malta
    "CY",  # Zypern
    "TR",  # Türkei (klimatisch südeuropäisch/mediterran)
}

CENTRAL_EU = {
    "DE",  # Deutschland
    "FR",  # Frankreich
    "AT",  # Österreich
    "CH",  # Schweiz
    "BE",  # Belgien
    "NL",  # Niederlande
    "LU",  # Luxemburg
    "PL",  # Polen
    "CZ",  # Tschechien
    "SK",  # Slowakei
    "HU",  # Ungarn
    "RO",  # Rumänien
    "BG",  # Bulgarien
}

EAST_EU = {
    "UA",  # Ukraine
    "MD",  # Moldawien
}

NORTH_AF = {
    "MA",  # Marokko
    "DZ",  # Algerien
    "TN",  # Tunesien
    "LY",  # Libyen
    "EG",  # Ägypten (Nil-Delta-Küste klimatisch relevant)
}

# Alle einzuschließenden Länder
INCLUDE = SOUTH_EU | CENTRAL_EU | EAST_EU | NORTH_AF

# GeoNames-Spaltennummern (0-basiert, Tab-getrennt)
COL = {
    "geonameid": 0,
    "name":      1,
    "asciiname": 2,
    "lat":       4,
    "lon":       5,
    "country":   8,
    "population":14,
}

# ── Verarbeitung ───────────────────────────────────────────────────────────────

def extract():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total = kept = 0
    per_country: dict[str, int] = {}

    with open(INPUT, encoding="utf-8") as fin, \
         open(OUTPUT, "w", newline="", encoding="utf-8") as fout:

        writer = csv.writer(fout)
        writer.writerow(["id", "name", "ascii_name", "country", "lat", "lon", "population"])

        for line in fin:
            total += 1
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 15:
                continue

            country = fields[COL["country"]]
            if country not in INCLUDE:
                continue

            try:
                pop = int(fields[COL["population"]])
            except ValueError:
                continue

            if pop < MIN_POP:
                continue

            writer.writerow([
                fields[COL["geonameid"]],
                fields[COL["name"]],
                fields[COL["asciiname"]],
                country,
                fields[COL["lat"]],
                fields[COL["lon"]],
                pop,
            ])
            kept += 1
            per_country[country] = per_country.get(country, 0) + 1

    # ── Zusammenfassung ────────────────────────────────────────────────────────
    print(f"Eingabe:  {total:,} Städte gesamt")
    print(f"Ausgabe:  {kept:,} Kandidaten  →  {OUTPUT}")
    print(f"Filter:   Länder {sorted(INCLUDE)}, Mindestpop. {MIN_POP:,}")
    print()
    print("Städte pro Land:")
    region_label = {c: "S-EU" for c in SOUTH_EU}
    region_label.update({c: "C-EU" for c in CENTRAL_EU})
    region_label.update({c: "E-EU" for c in EAST_EU})
    region_label.update({c: "N-AF" for c in NORTH_AF})
    for country, count in sorted(per_country.items(), key=lambda x: -x[1]):
        print(f"  {country}  ({region_label.get(country,'?'):4})  {count:4} Städte")

if __name__ == "__main__":
    if not INPUT.exists():
        sys.exit(
            f"Fehler: Eingabedatei nicht gefunden: {INPUT}\n"
            "→ cities15000.txt von https://download.geonames.org/export/dump/ herunterladen"
            " und ins Projektverzeichnis legen."
        )
    extract()
