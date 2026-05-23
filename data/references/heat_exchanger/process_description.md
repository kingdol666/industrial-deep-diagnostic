# Heat Exchanger E-201 — Process Description

## System Overview

E-201 is a shell-and-tube heat exchanger in the intermediate product cooling section of a phenol recovery unit. It cools hot process fluid (a phenol-acetone mixture at ~180°C) using cooling tower water (~30°C) on the shell side. The exchanger operates continuously as part of the 24/7 distillation process.

## Equipment Configuration

| Parameter | Value |
|-----------|-------|
| Exchanger Type | TEMA BEM (fixed tubesheet, single-pass shell) |
| Tube Side | Process fluid (hot) |
| Shell Side | Cooling water (cold) |
| Heat Transfer Area | 15 m² |
| Tube Material | 316L Stainless Steel |
| Tube Count | 124 tubes, 19mm OD, 2.5m length |
| Design Pressure | 1.6 MPa |
| Design Temperature | 200°C |
| In Service Since | 2018 (7 years) |

## Normal Operating Conditions

### Hot Side (Process Fluid — Tube Side)
| Parameter | Nominal | Setpoint | Alarm Low | Alarm High |
|-----------|---------|----------|-----------|------------|
| Inlet Temperature | 180.0 ± 1°C | 180°C (distillation control) | — | 190°C |
| Outlet Temperature | 143.0 ± 1°C | — (dependent variable) | — | 150°C |
| Flow Rate | 200 ± 5 L/min | 200 L/min (P-104) | 160 L/min | 240 L/min |
| Pressure Drop (ΔP) | 12.3 ± 0.5 kPa | — | — | 18.0 kPa |

### Cold Side (Cooling Water — Shell Side)
| Parameter | Nominal | Alarm Low | Alarm High |
|-----------|---------|-----------|------------|
| Inlet Temperature | 30.0 ± 3°C (seasonal + diurnal) | — | 35°C |
| Outlet Temperature | 67.0 ± 2°C | — | 75°C |
| Flow Rate | 200 ± 5 L/min | 150 L/min | 250 L/min |
| Pressure Drop (ΔP) | 8.1 ± 0.5 kPa | — | 12.0 kPa |

### Key Performance Indicators (KPIs)
| KPI | Clean Condition | Warning | Action Required |
|-----|----------------|---------|-----------------|
| Heat Transfer Coefficient (U) | 1840-1860 W/m²K | < 1800 | < 1750 |
| Approach Temperature | 75-77°C | > 80°C | > 82°C |
| Effectiveness (ε) | 0.245-0.250 | < 0.235 | < 0.225 |
| Hot Side ΔP | 12.3 kPa | > 14.0 | > 18.0 |

## Process Context

E-201 is the second-stage cooler for the phenol recovery distillation bottoms. The process fluid exits the distillation column reboiler at ~180°C and **must** be cooled to below 150°C before entering the extraction vessel V-205. High outlet temperature (>150°C) risks solvent flashing in V-205 and product loss through the vent system.

## Cooling Water Chemistry

The cooling tower water is treated with:
- **Corrosion inhibitor**: Phosphonate-based (PBTC), target 15-20 ppm
- **Biocide**: Isothiazolinone, weekly slug dose (50 ppm for 4 hours)
- **pH**: Maintained at 7.5-8.5 with sulfuric acid

**Critical vulnerability**: Cooling tower makeup water comes from Well #3 with total hardness 280-320 mg/L as CaCO3. When phosphonate residual drops below 10 ppm, **CaCO3 scaling initiates on hot tube surfaces within 3-5 days**. The scale layer acts as an insulator, reducing heat transfer and increasing tube-side pressure drop.

## Control Logic

- Hot outlet temperature is **not directly controlled** — it is a dependent variable responding to fouling, flow, and temperatures
- Cooling water flow is manually set by operators (nominal 200 L/min, rarely adjusted)
- Hot side flow is controlled by the upstream distillation bottoms pump P-104
- **No automatic fouling compensation exists** — the plant relies on scheduled cleaning
- Cooling water supply temperature varies diurnally (±1.5°C) and seasonally (±0.8°C over a month)

## Maintenance History

| Date | Action | Result |
|------|--------|--------|
| 2024-12-01 | Chemical cleaning (sulfamic acid 5%) | Full performance restored |
| 2025-02-01 | Chemical cleaning (sulfamic acid 5%) | Full performance restored |
| 2025-03-25 | Chemical cleaning (sulfamic acid 5%) | Partial recovery only (~72%) — hardened scale suspected |

Typical cleaning interval: 60-90 days depending on cooling water quality.
