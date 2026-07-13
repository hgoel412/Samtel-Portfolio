# Data — STK Exports and Analysis Results

Two layers. `raw/` holds the STK 13 Pro exports; `processed/` holds the results the Python pipeline computes from them. The scripts in `analysis/` read `raw/` and write `processed/`.

## raw/ — STK exports

### Access/
Satellite-to-asset and satellite-to-ground-station visibility. Two report types (Asset and GS), each in two forms (Access and AER), across the five constellations — 20 files.

`Asset_<cfg>_Access_Data.csv` / `GS_<cfg>_Access_Data.csv` — one row per visibility window.
- Start Time (UTCG), Stop Time (UTCG), Duration (sec)
- To Object (satellite), From Object (asset or ground station)
- Per-pass start/stop latitude, longitude, altitude for both ends

`Asset_<cfg>_Access_AER.csv` / `GS_<cfg>_Access_AER.csv` — pointing series within each access.
- Time (UTCG), Azimuth (deg), Elevation (deg), Range (km)

### Lifetime/
STK Lifetime runs at the design-window altitudes.

`Lifetime.csv` — altitude-versus-lifetime summary grid.
- Altitude_km, Life_Minus2Sigma_yr, Life_Nominal_yr, Life_Plus2Sigma_yr
- Disposal_Call, Area_0.02_yr, Area_0.03_yr, Area_0.045_yr

`Lifetime_Analysis_525km.csv` / `_550km.csv` — decay time-histories to re-entry.
- Time (UTCG), Semi-major Axis (km), Eccentricity, Inclination (deg)
- Height of Apogee (km), Height of Perigee (km), Sidereal Period (sec), Orbit Count

`<cfg>_P<plane>_S<sat>_Lifetime.csv` — per-satellite element histories, same columns.

### Revisit/
STK Coverage figure-of-merit (maximum revisit). Two reports per constellation — 10 files.

`FigureOfMerit<N>_Value_By_Grid_Point.csv` — max revisit at each grid point (0.5° grid, ~10,206 points).
- Latitude (deg), Longitude (deg), FOM Value (min) — after the properties header block

`FigureOfMerit<N>_Grid_Stats.csv` — one-line grid summary.
- Minimum (sec), Maximum (sec), Average (sec)

N maps to the constellation: 1 = C1, 2 = C2, 3 = C3, 4 = C4, 5 = SSO.

## processed/ — Python results

### revisit_latency_results.csv
Revisit and store-and-forward latency per constellation and asset.
- config, asset, metric, network (sovereign / global), P50, P95, max, n_samples
- Followed by a ground-station-contact-gap block and a dropped-packet block

### spatial_fom_summary.csv
Latitude structure of the revisit fields.
- config, grid_min / max / avg, belt_min / max / avg (8-37°N), belt_pct ≤15 / ≤30 / ≤60
- >1-orbit hole extent, peak, and peak latitude
- Followed by a value-at-asset (grid versus point) block

### dv_budget.csv
Per-satellite Δv budget and propulsion sizing.
- alt_km, design_life_yr, disposal_perigee_km
- injection, station_keeping, phasing, COLA, EOL_deorbit, subtotal, margin_25pct, TOTAL
- Followed by propellant-mass, plane-acquisition-trade, and station-keeping-fit blocks

### resilience_degradation.csv
Worst-asset degradation under satellite failures.
- config, k_failed, n_trials
- revisit_med / p10 / p90, latency_med / p10 / p90, dropfrac_mean / max

## Usage

```python
import pandas as pd

df = pd.read_csv('data/processed/revisit_latency_results.csv')
print(df.head())
print(df.describe())
```
