# Heat Exchanger E-201 — Troubleshooting SOP

## Scope
This SOP covers diagnosis of degraded heat transfer performance in shell-and-tube exchanger E-201. Symptoms include rising hot outlet temperature, declining heat transfer coefficient, and increasing tube-side pressure drop.

## 1. Classify Degradation Pattern

### 1.1 Gradual Drift (Days to Weeks)
| Symptom | Likely Cause | Diagnostic Step |
|---------|-------------|-----------------|
| HTC declines 3-8 W/m²K per day | Fouling (scale, sediment, biofouling) | Check cooling water chemistry logs |
| Hot outlet slowly rises | Reduced heat transfer due to fouling layer | Compare ΔP trend vs HTC trend |
| ΔP rises proportionally with HTC decline | Tube-side deposit buildup | Inspect approach temperature trend |
| Approach temperature increases | Insulating layer on tube wall | Cross-reference with water treatment logs |

**Confirmed gradual fouling when**: HTC decline rate is steady (±20%), ΔP rise correlates with HTC decline (r < -0.7), and hot/cold inlet conditions are stable.

### 1.2 Sudden Step Change (Minutes)
| Symptom | Likely Cause | Diagnostic Step |
|---------|-------------|-----------------|
| HTC drops >30 W/m²K in < 1 hour | Cooling water pump failure or flow blockage | Check cold_flow_rate trend |
| ΔP spikes suddenly | Tube blockage or debris | Check for upstream strainer failure |
| Hot outlet spikes >5°C | Loss of cooling water flow | Verify pump amps and valve positions |

**Confirmed sudden event when**: The step change coincides with a measurable change in flow rates or pump status.

### 1.3 Oscillation / Cycling
| Symptom | Likely Cause | Diagnostic Step |
|---------|-------------|-----------------|
| HTC cycles with ~24h period | Diurnal cooling water temperature variation | Check correlation with cold_inlet_temp |
| ΔP cycles irregularly | Flow instability from upstream process | Check hot_flow_rate stability |

## 2. Diagnostic Decision Tree

```
Hot Outlet Temperature Rising?
├── YES → Is the rise gradual (> 1 day)?
│   ├── YES → Check HTC trend
│   │   ├── HTC declining steadily → FOULING (go to Section 3)
│   │   └── HTC stable → Check hot_inlet_temp or cold_inlet_temp trends
│   └── NO (sudden) → Check cold_flow_rate
│       ├── Flow dropped → PUMP/FLOW ISSUE (go to Section 4)
│       └── Flow normal → Check cold_inlet_temp
│           └── Cold inlet high (>33°C) → COOLING TOWER PROBLEM
└── NO → Normal operation, continue monitoring
```

## 3. Fouling Diagnosis Protocol

### Step 3.1: Confirm Fouling Pattern
1. Plot HTC vs time — should show **linear decline** if fouling
2. Plot ΔP hot vs time — should show **linear increase**
3. Plot approach_temp vs time — should show **linear increase**
4. Verify hot_inlet_temp and hot_flow are stable (rules out upstream disturbance)

### Step 3.2: Identify Fouling Type
| Evidence | Fouling Type |
|----------|-------------|
| HTC ↓ + ΔP ↑ at similar rates | Particulate/sediment fouling (both sides affected) |
| HTC ↓ fast, ΔP ↑ slowly | Scale fouling (thin insulating layer, minimal flow restriction) |
| HTC ↓ + ΔP ↑ + approach_temp ↑ | CaCO3 scale (classic "insulating blanket" pattern) |
| Pump trip events → accelerated fouling after | Biofouling triggered by stagnant warm water |

### Step 3.3: Check Root Cause — Water Chemistry
1. Review cooling water treatment logs for the period **3-5 days before fouling onset**
2. Check phosphonate inhibitor concentration — below 10 ppm triggers scaling
3. Check pH excursions above 8.5 (increases CaCO3 precipitation rate)
4. Check for biocide schedule compliance (missed doses can cause biofouling)

### Step 3.4: Check Root Cause — Operational
1. Verify cooling water flow has not been reduced below 150 L/min
2. Check if hot side flow exceeds 220 L/min (higher velocity increases shear but also heat flux)
3. Review any upstream process changes that could alter fluid composition

## 4. Pump/Flow Issue Diagnosis Protocol

### Step 4.1: Confirm Flow Anomaly
1. Plot cold_flow_rate — look for step drops
2. Cross-reference with pump_trip_event signals
3. Check if cold_flow recovers spontaneously (partial trip) or stays low (hard failure)

### Step 4.2: Distinguish Transient vs Persistent
- **Transient**: Flow recovers within < 30 minutes, HTC bounces back → pump trip/restart
- **Persistent**: Flow stays low, HTC stays degraded → pump failure, valve stuck, or line blockage

## 5. Cleaning Effectiveness Assessment

After chemical cleaning:
| Observation | Interpretation |
|-------------|---------------|
| HTC recovers to > 95% of clean value | Normal — soft scale fully removed |
| HTC recovers to 70-85% of clean value | Partial — some hardened scale remains |
| HTC recovers to < 70% of clean value | Incomplete — consider mechanical cleaning or tube replacement |
| ΔP does NOT return to baseline | Possible permanent deposit or tube damage |

## 6. Recommended Actions

| Priority | Condition | Action |
|----------|-----------|--------|
| HIGH | HTC < 1750 W/m²K | Schedule cleaning within 7 days |
| HIGH | Hot outlet > 148°C (approaching 150°C alarm) | Reduce hot side flow to 160 L/min as interim measure |
| MEDIUM | Approach temp > 82°C | Initiate water chemistry investigation |
| MEDIUM | ΔP > 16 kPa | Inspect tube sheet for debris accumulation |
| LOW | Fouling rate exceeds 5 W/m²K per day | Review chemical treatment program with water treatment vendor |

## 7. Verification After Diagnosis

- [ ] Fouling onset date identified (±1 day)
- [ ] Pre-fouling trigger event identified (water chemistry excursion, pump trip, etc.)
- [ ] Fouling type matches observed pattern (scale vs particulate vs biofouling)
- [ ] Cleaning effectiveness explained (why partial vs full recovery)
- [ ] Recommendation includes both short-term (cleaning) and long-term (inhibitor management) actions
