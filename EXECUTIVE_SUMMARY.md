# EXECUTIVE SUMMARY: Sovereign SatCom-IoT Constellation Analysis

**Project:** Samtel-Aligned Sovereign Constellation Study
**Architect:** Harshit Goel  
**Date:** July 2026  
**Tools:** STK 13 Pro, Python 3.11, NumPy, Matplotlib

---

## 🚀 Executive Overview

This independent research project evaluates **Walker-Delta constellations** for persistent, sovereign surveillance of the **Indian Exclusive Economic Zone (EEZ)** and the **northern land border**. Five configurations spanning **18 to 32 satellites** were modelled end to end — coverage, revisit, store-and-forward latency, orbital lifetime, propulsion budget, and failure resilience — across a **33-day simulation window**, with every headline number cross-verified between STK coverage grids and independent first-principles Python.

**Key Conclusion:** A **24-satellite, 4-plane** constellation at **525 km / 40°** delivers the optimal operational balance, holding **worst-case revisit under 14 minutes** at every strategic asset. It beats the denser 6-plane alternative across the maritime EEZ, matches it along the border, and deploys in **4 launches instead of 6** — while a **32-satellite** build adds only **~1.3 minutes** of improvement.

*Mission geometry — the 5 constellation's coverage over the Indian EEZ (Arabian Sea & Bay of Bengal boxes) and the northern border assets, with the sovereign (GSI) latency, orbital decay and required ΔV budget*

---

## 📊 Key Findings

### 1. The 24-Satellite Optimum

Concentrating 24 satellites into **4 planes** captures India's **15–35°N belt**, where every asset sits:

* **Plane Efficiency:** The **6-plane** arrangement of the same 24 satellites spreads coverage over open ocean the mission never claims, reaching **18.2 minutes** worst-case at the EEZ against **13.6 minutes** for the 4-plane build.
* **Diminishing Returns:** Adding eight more satellites — 32 in total — improves worst-case revisit by only **~1.3 minutes**.
* **Launch Reality:** Propulsive plane changes cost **km/s-class Δv** on a 4 kg bus, and J2 nodal drift takes **years** against a 5-year design life. Each plane is therefore a dedicated injection, and **plane count is launch count**.
* **Recommendation:** The 24-satellite, 4-plane design delivers the mission in **4 launches instead of 6** — full operational value at approximately **two-thirds the deployment cost**.


### 2. Inclination Is Matched to Geography, Not Chosen by Default

A **40°** orbit dwells at the turning latitude that coincides with the border belt, delivering its tightest revisit exactly where the assets are:

* **40° Family:** **Single-digit-minute** worst-case revisit at every land-border asset.
* **Polar (SSO): 100%** of the region falls in the **95–190 minute** class — uniform, and uniformly unusable for time-critical ISR.
* **Design Consequence:** The sun-synchronous alternative buys consistent illumination the mission never asked for, and pays for it with a single, uniformly high revisit class across the entire theatre — acceptable nowhere the mission needs it.


### 3. Sovereign-Grade Resilience & Disposal

The architecture was stress-tested against random satellite failures and end-of-life obligations, not just nominal performance:

* **Graceful Degradation:** The **first satellite loss is invisible** to worst-case revisit — the replacement clock starts at the second failure, not the first.
* **Cost of Sovereignty:** Store-and-forward delivery was quantified for an **India-only ground segment** against a global one. Worst-case sovereign latency at the western EEZ asset holds near **620 minutes for every configuration tested** — a **ground-segment** constraint that no satellite count can close.
* **Compliant Disposal:** At 525 km the unattended orbital lifetime is **8.6 years**, so disposal is **propulsive by design**. The full per-satellite budget closes at **138 m/s** (5-year life, 350 km disposal perigee, 25% margin).
* **Propellant Feasibility:** On a 4 kg bus that is **838 g** of cold gas (23.3%), **248 g** of green monopropellant (7.0%), or **56 g** of electric propellant (1.6%).

---

## 🛠️ Technical Methodology

The analysis pipeline was built to ensure reproducibility and high-fidelity simulation:

* **Simulation Engine:** **STK 13 Pro** was used to model orbital mechanics, employing **Walker-Delta** patterns at 40° and 97.6° inclination, with Coverage Figure-of-Merit (Maximum Revisit Time) and Orbit Lifetime evaluated at a **10° elevation mask** over a 33-day window.
* **Data Pipeline:** A custom **Python 3.11** pipeline parsed the STK CSV exports to compute revisit, dual-network store-and-forward latency, orbital decay, and Δv budget across **10,206 coverage grid points** and a 60-second packet-injection grid.
* **Resilience Model:** Monte Carlo satellite kills across the 4-plane family — **exhaustively enumerated** through two simultaneous failures, **200 seeded random draws** beyond, fully reproducible.
* **Validation:** All results were cross-verified between STK coverage grids and independent first-principles code; the fitted drag rate is corroborated by an **implied atmospheric density scale height of ~60 km** — dead-centre of the thermospheric band, and a figure the fit never assumed.
* **Visualization:** **10 professional dashboards** were generated using **Matplotlib** to visualize complex temporal and spatial data.

---

## 🔮 Strategic Recommendations

Based on the quantitative analysis, the following deployment roadmap is recommended:

1.  **Phase 1 (Baseline):** Deploy the **24-satellite, 4-plane Walker-Delta** at **525 km / 40°** across **4 dedicated PSLV/SSLV injections**, carrying green monopropellant at **7% of bus mass** for station-keeping and compliant end-of-life deorbit.
2.  **Phase 2 (Ground Segment):** Close the sovereign latency gap by **siting ground stations, not by buying satellites**. The 620-minute worst case at the western EEZ is invariant to constellation size and is the single highest-leverage fix available to the architecture.
3.  **Phase 3 (Growth):** Hold the **32-satellite** dense build in reserve. The marginal **~1.3-minute** revisit gain does not repay the launch premium unless the requirement tightens below the sub-14-minute floor the 24-satellite build already delivers.

---

*For full technical details, code, and dashboards, please refer to the accompanying GitHub repository.*
