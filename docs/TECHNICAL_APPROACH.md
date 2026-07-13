# Technical Approach

## Tools

- STK 13 Pro for orbit propagation, access, coverage, and lifetime.
- Python 3.11 for the analysis pipeline, driving STK headlessly through `ansys-stk-core`.
- NumPy for the vectorized access and latency computation; Matplotlib for the charts.
- tqdm for progress on the heavy access loops.

## Pipeline

The work runs in two stages that share nothing on disk beyond the exported reports.

1. Scenario generation. The scripts in `src/` build each Walker-Delta configuration and the ground segments in STK, validate the orbit parameters, and export access and lifetime reports to `data/raw/`.
2. Verification and analysis. The scripts in `analysis/` read those reports and recompute every headline metric from first principles in Python. STK produces the reference; Python is the independent check. A number is reported only when both agree.

## Coverage and revisit

Access is a satellite seeing an asset above a 10° elevation mask. For each asset, all satellite-over-asset intervals across the fleet are merged into a single coverage timeline, and the gaps between passes are the revisit intervals. Results are reported as the 50th percentile (typical), 95th percentile (realistic worst case), and maximum, over a 33-day propagation window. The spatial layer takes the STK figure-of-merit grids, normalizes them to minutes, and reads worst-case revisit as a function of latitude — which is how the equatorial behavior and the border-belt performance are separated.

## Store-and-forward latency

The constellation has no inter-satellite links, so a satellite collects over a target and carries the data until it passes a ground station. For a collection request at time t, the model finds the first satellite pass over the asset at or after t (the collection), then the first pass of that same satellite over a ground station (the downlink). The delay from request to downlink is the delivery latency. The computation runs twice: once against an India-only sovereign ground segment (Bengaluru, Lucknow, Port Blair, Shadnagar) and once against a global network, so the extra latency of keeping data on Indian soil is measured directly. Requests that cannot be delivered inside the window are counted, not silently dropped. Because the carrier satellite cannot hand its data to another satellite, delivery latency is set by that one satellite's carry time and not by the constellation's aggregate ground contact; the pipeline reports both, and the gap between them is what an inter-satellite link or a better-placed ground station would close.

## Orbital lifetime and disposal

Lifetime comes from STK Lifetime runs on a 3U bus (4 kg, drag area 0.03 m², drag coefficient 2.2, ballistic coefficient near 61 kg/m²) using the Jacchia-Roberts atmosphere and CSSI predicted solar flux from a 1 July 2026 epoch. Each altitude is run across a ±2σ solar-flux band. Disposal is judged on the low-flux, long-life edge of the band — the conservative test — and service worst-case on the high-flux edge. The post-processing checks the σ ordering, the drag-area ordering, and monotonicity with altitude before it trusts the table, and it re-derives the disposal call from the −2σ life to confirm the STK label.

## Δv budget

The budget is closed form, with no STK dependence. Circular-orbit velocity, a Hohmann pair for altitude changes, the J2 nodal-precession rate, and the plane-change geometry are computed directly. Station-keeping is fitted from the first-year slope of the STK decay profiles at elevated 2026-27 flux, which is the high-drag, conservative end. The end-of-life maneuver is the exact perigee-lowering burn from the design altitude to the disposal perigee. Injection trim and collision avoidance are stated allowances, and 25% margin is applied to the total. Propellant mass is sized on the 4 kg bus by the rocket equation for cold-gas, green-monopropellant, and electric options. The two-altitude decay slopes imply a density scale height, which is checked against the range expected for the thermosphere as a physical sanity test on the whole fit.

## Plane acquisition

The plane-acquisition trade compares the three ways to place satellites in separate planes: a direct propulsive plane rotation, differential J2 drift from an altitude offset, and separate launches. Both the direct-rotation Δv and the drift timescale are computed, which is how the study concludes that neither on-orbit method is feasible and that plane count maps one-to-one onto launch count.

## Resilience

Failures are modeled by Monte Carlo on the four-plane family. For each failure count from zero to eight, loss sets are enumerated exhaustively when the number of combinations is small and sampled (200 draws, fixed seed) when it is large. Each loss set has its dead satellites removed and the worst-asset revisit and sovereign latency recomputed under the same store-and-forward model. Results are reported as the median and the 10th-to-90th-percentile spread across loss sets. The zero-failure case reproduces the baseline as a cross-check.

## Verification

Every headline metric is checked two ways. The coverage grids carry acceptance gates: the neighborhood maximum at each asset in the STK grid must bound the per-asset maximum revisit from the access analysis, on the same 10° convention. The lifetime post-processing checks orderings, monotonicity, and disposal-call consistency. The Δv script checks slope ordering, deorbit-burn ordering, and the implied scale height. The resilience script checks that degradation is monotone in the failure count. Where a check fails, the script says so rather than plotting a number that looks fine.

## Assumptions

- 10° minimum elevation for a usable pass.
- 60-second sampling grid for collection requests.
- 3U bus at 4 kg, drag area 0.03 m², drag coefficient 2.2.
- 40° inclination, circular orbits, 525-550 km design window.
- 1 July 2026 epoch, CSSI predicted solar flux.
- 33-day propagation window.

## Not modeled

Sensor and payload performance, on-board power and thermal, downlink RF budget, ground-processing time, launch-vehicle integration, and maintenance downtime. These require detailed-design inputs and are out of scope for an architecture study.
