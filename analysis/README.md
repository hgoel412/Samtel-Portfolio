# 🛰️ Sovereign Space-Based IoT Constellation

Mission architecture and trade study for a sovereign narrowband IoT constellation serving the Indian EEZ and the northern land border — unattended sensor backhaul, vessel telematics, and remote SCADA over territory with no cellular or fibre reach.

Five Walker-Delta configurations, 18 to 32 satellites, modelled end to end: coverage, revisit, store-and-forward latency, orbital lifetime, Δv budget, and failure resilience. Every headline number is cross-verified between STK coverage grids and independent first-principles Python.

---

## The call

**24 satellites · 4 planes · 525 km · 40° inclination**

| | |
|---|---|
| Worst-case revisit, every strategic asset | **≤ 13.6 min** |
| Cost of going to 32 satellites | ~1.1 min better revisit, +8 satellites |
| Cost of the 6-plane alternative | 18.2 min at the EEZ, and 6 launches instead of 4 |
| Per-satellite Δv (5 yr, 350 km disposal) | **138 m/s** incl. 25% margin |
| Propellant on a 4 kg bus | 933 g cold gas · 279 g green monoprop · 63 g electric |
| Unattended orbital lifetime at 525 km | 8.6 yr — EOL deorbit burn required, already in the budget |

**The uncomfortable finding:** worst-case *sovereign* latency at the western EEZ asset sits near **620 minutes** — for every single configuration. No amount of satellites fixes it. The constraint is the ground segment, not the constellation: a sovereign India-only ground network cannot see a satellite over the Arabian Sea for hours. Against a global ground network the same packet lands in minutes. That gap is the measurable price of data sovereignty, and it is a ground-station siting problem, not an orbit problem.

---

## What the analysis covers

| Phase | Script | Output |
|---|---|---|
| 0 | `00_build_constellations.py` | 5 Walker-Delta constellations in STK |
| 0 | `03_build_groundstation_setup.py` | 4 Indian GS, 7 global GS, 5 strategic assets |
| 1 | `01_revisit_latency.py` | Revisit + dual-network store-and-forward latency |
| 2 | `02_spatial_fom.py` | Coverage figure-of-merit over 10,206 grid points |
| 3 | `03_lifetime_vs_altitude.py` | Orbital lifetime vs altitude, 5-yr disposal compliance |
| 4 | `04_dv_budget.py` | Δv budget, plane-acquisition trade, propellant sizing |
| 5 | `05_resilience_degradation.py` | Monte Carlo degradation under 0–8 satellite failures |
| 6 | `06_decay_profile.py` | Unattended decay profiles at the design-window edges |

---

## Key findings

**1. Inclination is matched to geography, not chosen by default.**
A 40° orbit turns over at the latitude where the assets sit, giving its tightest revisit exactly where the mission needs it. Sun-synchronous is an optical requirement, not an L-band IoT one — and it puts **100% of the region in the 95–190 minute class**, uniformly, which is uniformly unusable.

**2. Four planes beat six, at the same satellite count.**
24 satellites in 6 planes spread coverage over ocean the mission never claims (18.2 min worst-case at the EEZ). The same 24 in 4 planes beat it across the maritime EEZ and match it along the border — and deploy in **4 launches instead of 6**. Propulsive plane changes are infeasible on a 4 kg bus (km/s-class Δv) and J2 drift takes years, so plane count *is* launch count.

**3. Scaling past 24 satellites does not pay.**
32 satellites improve worst-case revisit by roughly 1.1 minutes. The geography does not repay the launch premium.

**4. The first satellite loss is invisible.**
Monte Carlo kills across the 4-plane family show worst-case revisit unchanged after a single failure. The replacement clock starts at the second loss, not the first.

**5. The drag model is corroborated, not assumed.**
The station-keeping rate is fitted from the decay profiles, and the two-altitude slope pair implies an atmospheric density scale height of ~60 km — dead centre of the thermospheric band. The fit agrees with an atmosphere it never modelled.

---

## Dashboards

All figures in [`dashboards/`](dashboards/):

| | |
|---|---|
| [01_revisit.png](dashboards/01_revisit.png) | Revisit per asset, all 5 constellations |
| [02_latency_sovereign.png](dashboards/02_latency_sovereign.png) | End-to-end latency, Indian ground segment only |
| [03_latency_global.png](dashboards/03_latency_global.png) | End-to-end latency, global ground segment |
| [04_max_latency_sovereign.png](dashboards/04_max_latency_sovereign.png) | Worst-case sovereign latency — the sovereignty cost |
| [05_lifetime_vs_altitude.png](dashboards/05_lifetime_vs_altitude.png) | Lifetime vs altitude, ±2σ flux band, 5-yr rule |
| [06_decay_profile_design_window.png](dashboards/06_decay_profile_design_window.png) | Unattended decay at 525 / 550 km |
| [07_dv_budget.png](dashboards/07_dv_budget.png) | Per-satellite Δv budget + propellant sizing |
| [08_degradation_resilience.png](dashboards/08_degradation_resilience.png) | Degradation under 0–8 satellite failures |
| [09_fom_heatmaps.png](dashboards/09_fom_heatmaps.png) | Worst-case revisit fields, all 5 configs |
| [10_fom_latitude_profile.png](dashboards/10_fom_latitude_profile.png) | Zonal worst-case revisit vs latitude |

---

## Running it

**Requirements:** Python 3.11 · STK 13 Pro (driven via the `ansys-stk` package, import namespace `ansys.stk.core`) · NumPy · Matplotlib · tqdm

```bash
pip install -r requirements.txt
```

Phases 1–6 read the STK exports committed under `data/raw/` and need **no STK licence** — clone the repo and they run. Only phase 0 (constellation and ground-segment construction) requires STK 13 Pro.

> **Note:** the analysis scripts currently carry absolute Windows paths (`D:/Samtel-Portfolio/...`) at the top of each file. Point them at your own clone before running.

---

## Documents

- [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) — the one-page version
- [docs/Architectural_Call.md](docs/Architectural_Call.md) — demand map and the architecture decision
- [docs/PROJECT_OVERVIEW.md](docs/PROJECT_OVERVIEW.md) — full reasoning chain

---

## License

MIT — see [LICENSE.md](LICENSE.md).
