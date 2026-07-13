# Key Findings — Sovereign SatCom-IoT Constellation Study

## Summary

The study compares five Walker-Delta constellations for sovereign satellite-IoT connectivity across the Indian theatre — the maritime EEZ and the northern land border. Each was propagated in STK 13 Pro over a 33-day window and cross-checked against first-principles Python. The recommended constellation is 24 satellites in 4 planes at 525 km and 40° inclination (C3): worst-case revisit under 14 minutes at every asset, in four launches instead of six.

But the constellation is not the whole system. The results separate two things that usually get collapsed into one: how often a satellite can pick up data from an asset (revisit), and how long that data then takes to reach an Indian ground station (delivery latency). Revisit is solved. Delivery latency on an India-only ground network has one sharp gap — a western-maritime tail of about ten hours — and surfacing it, and pricing its fix, is the most useful result in the study.

## The five configurations

| Config | Satellites | Planes | Inclination | Role |
|---|---|---|---|---|
| R (SSO) | 18 | 3 | 97.6° | Sun-synchronous reference — the rideshare default |
| C1 | 18 | 3 | 40° | Same fleet as R, tilted to the target latitude |
| C2 | 24 | 6 | 40° | 24 satellites, six planes |
| C3 | 24 | 4 | 40° | Recommended |
| C4 | 32 | 4 | 40° | Denser fleet, resilience check |

## Revisit (collection)

Worst-case revisit, in minutes, at a 10° elevation mask over a 33-day window:

| Config | EEZ East | EEZ West | Ladakh | Siachen | Tawang |
|---|---|---|---|---|---|
| R (SSO) | 153 | 153 | 159 | 158 | 162 |
| C1 | 213 | 213 | 9.5 | 9.8 | 12.8 |
| C2 | 18.2 | 18.2 | 10.1 | 9.8 | 12.2 |
| C3 | 13.4 | 13.6 | 9.5 | 9.1 | 12.8 |
| C4 | 12.4 | 12.4 | 5.3 | 4.9 | 8.5 |

The sun-synchronous reference is the wrong orbit — about 2.5 hours between passes at every asset, because a near-polar track spends little time over the Indian belt. Its one advantage, constant illumination for an optical sensor, does not outweigh a tenfold revisit penalty at these latitudes. Tilting the same 18 satellites to 40° (C1) fixes the border immediately, to under 13 minutes, because a ground track is densest at its turning latitude and 40° puts that dwell over Ladakh, Siachen, and Tawang. But it leaves the maritime EEZ above three hours — 18 satellites cannot cover both the border and the open sea. Twenty-four close the EEZ. C3 holds worst-case revisit under 14 minutes at every asset, in four launches.

### Four planes or six is a trade, not a ranking

C3 (4 planes) and C2 (6 planes) carry the same 24 satellites, and choosing between them is a real trade.

At the specific assets, C3 wins: 13.4 minutes at the EEZ points against 18.2 for C2, and level or slightly better at the border. C3 also costs two fewer launches. That is why it is the recommendation.

But C3's coverage is structured by latitude and C2's is not. Across the whole 8-37°N belt, C2 holds everything under 40 minutes; C3 has spots inside the belt that reach about 110 minutes, and a revisit hole centered on the equator — a band of roughly ±8.6° latitude where worst-case revisit exceeds one orbit and peaks near 183 minutes at 0°. No asset in this study sits in that hole or in the belt spots; the assets fall exactly in C3's good latitudes. So C3 is right for this fixed asset list. C2 is the choice if the list grows toward the equator or if broad-area coverage is needed — it buys uniformity for two more launches.

### 32 satellites buy resilience, not coverage

C4 (32 satellites) sharpens the border hard — Ladakh nearly halves, to 5.3 minutes — but the binding constraint is the maritime EEZ, and there C4 gains about a minute over C3. Eight more satellites and their launches do not pay for a minute at the assets. What they buy is resilience, below. C4 keeps the same equatorial hole as C3.

## Delivery latency, and the cost of a sovereign ground segment

Revisit is when a satellite can pick up data. It is not when that data reaches the ground. With no inter-satellite links, a satellite picks up the asset's data and carries it until it passes a ground station. Delivery latency is collection plus carry, and the carry depends entirely on which ground stations you are allowed to use.

C3 delivery latency, 95th percentile, in minutes:

| Asset | Global network | India-only (sovereign) |
|---|---|---|
| EEZ East (87°E) | 8.7 | 8.7 |
| Ladakh (77°E) | 11.4 | 11.4 |
| Siachen (77°E) | 11.2 | 11.2 |
| Tawang (92°E) | 49.5 | 94.7 |
| EEZ West (62°E) | 23.6 | 619.6 |

With a global network, C3 delivers everywhere within about 24 minutes at the 95th percentile. With an India-only network, the picture splits by geography:

- Assets under or east of the Indian station belt — EEZ East, Ladakh, Siachen — deliver fast, within about 11 minutes at the 95th percentile, worst case one orbit.
- The eastern border, Tawang, carries a moderate tail: about 95 minutes at the 95th percentile.
- The far-western maritime point, EEZ West in the Arabian Sea, carries a heavy tail: about 620 minutes — over ten hours — at the 95th percentile. It sits roughly 15° of longitude west of the westernmost Indian station, and a satellite that picks up data there can take up to about 6.6 orbits before its own ground track returns over the narrow Indian station band.

That is the cost of a sovereign ground segment, and for the western sea it is not measured in minutes. It is the single hardest number in the study.

### The tail is a ground-segment problem, not a fleet problem

The western tail does not shrink with more satellites. C4 (32 satellites) has the same EEZ West sovereign latency — about 622 minutes at the 95th percentile — as C3 (24). Losing up to eight satellites moves it by under ten minutes. Adding satellites shortens revisit; it does nothing for the time one satellite takes to carry data to a distant station.

The constellation is in near-continuous contact with India as a whole: across the fleet, the gap in Indian ground-station contact is never more than about 3.6 minutes. The problem is only that a specific satellite carries specific data, and without inter-satellite links it cannot hand that data to whichever satellite is over India at the time. Two levers close the tail:

- A western ground station. EEZ East delivers in 13 minutes worst-case because it sits under the station belt. A station on the western seaboard — the Gujarat coast, near 69-70°E — would put EEZ West under the belt the same way. This is the cheapest fix and the next run to make.
- Inter-satellite links. With cross-links, any satellite over India downlinks the western satellite's data and the tail collapses to the few-minute aggregate contact gap.

Neither is a constellation change. The recommendation is C3 plus a western station or cross-links — the constellation and its ground segment specified together.

## Orbital lifetime and disposal

Lifetime from STK Lifetime runs on a 3U bus (4 kg, drag area 0.03 m², ballistic coefficient near 61 kg/m²), Jacchia-Roberts atmosphere, CSSI predicted solar flux, epoch 1 July 2026:

| Altitude | Unattended life |
|---|---|
| 525 km | 8.6 years |
| 550 km | 10.3 years |

Both altitudes give the mission a long service life, and both exceed the five-year post-mission disposal rule. A satellite that decays naturally in 8.6 years is not compliant, so every satellite carries an end-of-life burn that drops perigee and clears the orbit inside the rule, priced into the Δv budget. For the lower edge of the design window there is a no-propulsion alternative: adding drag area (a deployable surface, 0.045 m²) shortens decay enough to comply passively. The orbit decays circular — eccentricity stays under 0.003 all the way down — so disposal is an altitude-and-drag decision, not an attitude problem.

## Δv budget and propulsion

Per-satellite budget at the design point (525 km, 5-year life, disposal perigee 350 km):

| Item | Δv (m/s) |
|---|---|
| End-of-life deorbit | 49 |
| Station-keeping (5 yr) | 31 |
| Injection trim | 15 |
| In-plane phasing | 11 |
| Collision avoidance | 5 |
| Margin (25%) | 28 |
| Total | 138 |

A 7-year life raises the total to 156 m/s. Either sits inside a small module: on the 4 kg bus, that is roughly 250-280 g of green monopropellant (6-7% of the bus) or about 930 g of cold gas (23%). Station-keeping was fitted from the first-year slope of the STK decay profiles — 6.15 m/s/yr at 525 km, 4.03 at 550 — and the two-altitude slope pair implies a 60 km density scale height, inside the thermospheric band, which is the check that the fit is physical.

Plane acquisition ties the geometry to the launch plan. A four-plane constellation needs its satellites in four planes, and there are three ways to get them there:

- Rotate a plane with propulsion. That costs 4,884 m/s for 60° or 6,908 m/s for 90° — more than thirty times the entire bus budget. Not feasible.
- Let the planes drift apart with J2. A 50 km altitude offset gives 0.147°/day, about 1.7 years to open 90°, with the satellites off-altitude the whole time. Too slow to deploy with.
- Launch each plane separately. On a PSLV or SSLV the plane is fixed by the launch time, so each plane comes from its own launch.

Plane count is launch count, which is why four planes (C3) beat six (C2): four launches, not six, for the same 24 satellites.

## Resilience

Failures were modeled by Monte Carlo on the four-plane family. Worst-asset P95 revisit as satellites are removed, in minutes:

| Satellites lost | C3 (24) | C4 (32) |
|---|---|---|
| 0 | 12.5 | 8.6 |
| 1 | 12.9 | 9.5 |
| 2 | 25.5 | 17.0 |

The first loss is invisible — C3's worst-asset revisit moves from 12.5 to 12.9 minutes. The second loss roughly doubles it, to 25.5. So the replacement clock does not start at the first failure; it starts at the second. That is the difference between a scheduled maintenance launch and a scramble. C4's extra satellites soften the second loss to 17.0 minutes, which is the real reason to field 32 rather than 24 — resilience, not revisit.

## What the study does not model

The analysis is orbital geometry, dynamics, and deployment. It stops where detailed design begins. Not modeled: sensor and payload performance (radiometry, resolution, SAR or optical specifics), on-board power and thermal, downlink RF budget, ground-processing time, launch-vehicle integration, and maintenance downtime. These need detailed-design inputs and cannot be closed honestly at architecture stage. Saying so is what makes the coverage, lifetime, and Δv numbers worth trusting.

## Bottom line

The constellation is C3: 24 satellites, 4 planes, 525 km, 40°. Worst-case revisit under 14 minutes at every asset, an 8.6-year service life with compliant disposal, 138 m/s of Δv on a 4 kg bus, four launches, and a first-failure margin. The system is C3 plus a western ground station or inter-satellite links — because with an India-only ground segment the western maritime point carries a ten-hour delivery tail that no number of satellites can close. Every figure here was checked in STK and in independent Python.
