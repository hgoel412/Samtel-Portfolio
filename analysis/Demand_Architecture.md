# Sovereign Demand & The Architecture Call

*Prepared by: Harshit Goel*

## Phase 5: Sovereign Demand Map

This phase defines the strategic business development layer, grounding the engineering capabilities in actual sovereign use cases. It identifies who buys, at what volume, and why satellite-IoT is the superior solution, explicitly navigating around existing state programs like NavIC.

### 1. Deep-Sea / Distant-Water Fishing

- **Customer:** Fleets / Ministry of Fisheries
- **Volume:** Thousands
- **Rationale:** Covers deep-sea vessels beyond NavIC's regional coastal distress footprint. Enables high-data fleet telematics (engine/cold-chain) and catch traceability for export compliance.

### 2. Border-Sensor Telemetry (Strategic)

- **Customer:** Army / BSF / ITBP
- **Volume:** Hundreds to low-thousands
- **Rationale:** Unattended ground sensors (UGS) along the LAC/LoC in terrain with zero cellular coverage and infeasible fibre. The Phase 1 Ladakh revisit/latency numbers act as the exact spec sheet for this use case.

### 3. Critical Infrastructure & Energy Telemetry

- **Customer:** GAIL, PowerGrid, ONGC, NTPC
- **Volume:** Thousands
- **Rationale:** Remote SCADA backhaul for pipelines, offshore wells, and transmission towers. Acts as the commercial ARPU anchor for the constellation.

### 4. Army Logistics & Disaster Fallback

- **Logistics:** Convoy and depot tracking across Ladakh/Northeast terrain where cellular is absent.
- **Disaster Fallback:** NDMA/State authorities needing resilient telemetry when terrestrial networks fail (e.g., Cyclone Dana precedent).

## Phase 6: The Architecture Call

This phase fuses the orbital mechanics, deployment constraints, and demand mapping into a single, buildable architecture recommendation.

### 1. Orbit & Geometry

- **Drop SSO, Go Mid-Inclination (~40°):** Sun-synchronous orbit is an optical requirement, not an L-band IoT requirement. A 40° inclination concentrates the dwell time directly on the Indian border belt (8-37°N) while still covering the south, drastically improving revisit times for the same satellite count.

### 2. Size, Altitude, and Plane Count

- **Altitude (525-550 km):** The sweet spot balancing multi-year service life, a large coverage footprint, and minimum lifecycle delta-v.
- **Fleet Size (~24-32 Sats):** 24 satellites act as the service-grade first block, while 32 satellites provide sovereign-grade margin and graceful degradation.
- **Plane Count (3-4 Planes):** Minimized to match the launch campaign. Because propulsive plane changes are infeasible for CubeSats and J2 drift is too slow, each plane requires a dedicated PSLV/SSLV injection. The geometry is actively shaped around this launch reality.

### 3. Waveform Standard

- **3GPP NB-IoT-NTN:** Betting on a proprietary stack in 2026 strands the network outside the device economy. By adopting 3GPP Release 17/19 standards, the constellation leverages the global chipset ecosystem, enabling dual-mode terrestrial/satellite roaming seamlessly.

### Synthesis Recommendation

**Recommended Sovereign Constellation:** ~24-32 3U CubeSats · ~40° inclination · ~525-550 km · 3-4 planes deployed by dedicated PSLV/SSLV injections · ~150-300 m/s propulsion with EOL deorbit · 3GPP NB-IoT-NTN.
