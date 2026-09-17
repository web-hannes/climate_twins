# Klimazwilling

**Wo liegt heute dein Klima von morgen?**

Klimazwilling macht den Klimawandel greifbar. Statt abstrakter Temperaturgrafiken zeigt es dir, welche europäische Stadt heute schon das Klima hat, das deine Stadt in 20 bis 40 Jahren haben wird — mit Namen, Lage und echten Vergleichswerten.

## Was ist ein Klimazwilling?

"+2°C im Jahresmittel" klingt abstrakt. "Das Klima von München ähnelt 2041–2060 dem heutigen Klima von Toulouse" macht denselben Wandel konkret und erlebbar.

Klimazwilling findet für jede deutsche Postleitzahl die europäische oder nordafrikanische Stadt, deren heutiges Klima dem prognostizierten Zukunftsklima deiner Stadt am ähnlichsten ist. Du siehst sofort: Wie heiß werden die Sommer? Wie mild die Winter? Wie viel Regen fällt?

## So funktioniert es

1. **PLZ eingeben** — Klimazwilling ermittelt die Lage deiner Stadt und lädt die lokalen Klimadaten.
2. **Matching** — Temperatur und Niederschlag in allen vier Jahreszeiten werden mit über 4.000 Städten in Europa und Nordafrika verglichen.
3. **Ergebnis** — Die Stadt mit dem ähnlichsten heutigen Klima ist dein Klimazwilling, inklusive Distanz, Erwärmungswert und saisonalem Vergleichsdiagramm.

Zwei Vergleichsmodi stehen zur Wahl: Zukunftsklima vs. historisches Klima (1970–2000) oder vs. aktuelles Klima (2021–2040).

## Datengrundlage

- **Klimaprojektionen:** WorldClim 2.1, basierend auf fünf CMIP6-Klimamodellen (EC-Earth3-Veg, IPSL-CM6A-LR, MIROC6, MPI-ESM1-2-HR, MRI-ESM2-0), Emissionspfad SSP2-4.5 — ein mittleres Szenario, das weder das Schlimmste noch das Beste annimmt.
- **Historische Klimadaten:** WorldClim 2.1, Referenzperiode 1970–2000.
- **Städte & Koordinaten:** GeoNames, Mindestgröße 25.000 Einwohner.

## Kandidatenpool

Über 4.000 Städte aus 34 Ländern: Süd- und Mitteleuropa (inkl. Deutschland, Frankreich, Polen, Ukraine), der Türkei sowie Nordafrika (Marokko, Algerien, Tunesien, Libyen, Ägypten). Nordeuropäische Länder (Skandinavien, Britische Inseln, Baltikum) sind ausgeschlossen, da ihr heutiges Klima dem zukünftigen deutschen Klima nicht entspricht.

## Projektstruktur

```
scripts/
  extract_candidates.py   Kandidatenstädte aus GeoNames filtern
  build_city_json.py      Klimadaten je PLZ aus WorldClim abtasten
  build_twins.py          Klimazwillinge berechnen und speichern
data/
  candidates_eu.csv       Kandidatenstädte (gefiltert)
  candidates_climate.csv  Klimadaten der Kandidaten
  cities/                 WorldClim-Rohdaten je Zeitraum
docs/
  index.html              Startseite
  result.html             Ergebnisseite
  data/cities/            Fertige JSON-Dateien je PLZ
```

## Lokale Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install numpy pandas rasterio scipy
python3 -m http.server 8000 --directory docs
```

Dann [http://localhost:8000](http://localhost:8000) aufrufen.
