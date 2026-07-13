# 🛰️ Samtel SatCom-IoT Constellation

Mission architecture and analysis for an IoT satellite constellation providing persistent surveillance over Indian theatre

## Overview

This project demonstrates:
- **Satellite Constellation Design** 5 Walker-Delta configurations 18 to 32 satellites
- **Coverage Analysis** Max revisit over Indian theatre.
- **Independent Revisit Analysis** cross-checked between STK coverage grids and independent Python.
- **End-to-end latency** Sovereign ground segment versus a Global network.
- **Lifetime and Disposal** five-year disposal compliance versus altitude.
- **Δv budget** the plane-acquisition trade.
- **Monte Carlo Analysis** Single node failure edge cases

## Quick Start

The full reasoning is in `docs/PROJECT_OVERVIEW.md` 

### View Daashboards

All visualizations are in `dashboards/`:
1. [Samtel Constellation Revisit] (01_revisit.png)
2. [Constellation Soveriegn Latency] (02_latency_sovereign)
3. [Constellation Global Latency] (03_latency_global.png)
...(see dashboards/README.md)

## Running it

Python 3.11, STK 13 Pro (driven through `ansys-stk-core`), NumPy, Matplotlib,tqdm.
