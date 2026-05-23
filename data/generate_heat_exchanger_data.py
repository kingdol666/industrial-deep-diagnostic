#!/usr/bin/env python3
"""
Generate synthetic heat exchanger fouling dataset for industrial-deep-diagnostic demo.

Scenario: Shell-and-tube heat exchanger in a chemical plant.
- Hot side: process fluid (180°C) cooled from 180→140°C
- Cold side: cooling water (30°C) heated from 30→70°C
- 30 days operation, 5-minute sampling
- Gradual fouling develops on hot side starting day 12
- Two "spike events" at days 18 and 23 (cooling water pump trips)
- Cleaning cycle at day 25 partially restores performance
- Known root cause: CaCO3 scale deposition due to water chemistry excursion on day 9

Output: CSV with 8640 rows × 14 columns
"""
import csv
import math
import random
from datetime import datetime, timedelta

random.seed(42)

# --- Configuration ---
DAYS = 30
INTERVAL_MIN = 5
TOTAL_ROWS = (DAYS * 24 * 60) // INTERVAL_MIN  # 8640

HOT_INLET_NOMINAL = 180.0   # °C — tightly controlled
COLD_INLET_NOMINAL = 30.0   # °C — seasonal variation
HOT_FLOW_NOMINAL = 200.0    # L/min
COLD_FLOW_NOMINAL = 200.0   # L/min (balanced flow for equal Cp)
INITIAL_HTC = 1850.0        # W/m²K — clean condition
INITIAL_DP_HOT = 12.3       # kPa
INITIAL_DP_COLD = 8.1       # kPa
CLEAN_HOT_OUT = 143.0       # °C — hot outlet under clean conditions
CLEAN_COLD_OUT = 67.0       # °C — cold outlet under clean conditions

# Fouling parameters
FOULING_START_DAY = 12      # Day when fouling becomes measurable
FOULING_RATE = 5.0          # HTC decline per day (W/m²K)
FOULING_DP_RATE = 0.30      # Pressure drop increase per day (kPa)

# Water chemistry excursion (day 9) — triggers CaCO3 scaling
CHEM_EXCURSION_DAY = 9.0

# Cooling water pump trips
PUMP_TRIP_1_DAY = 18.3      # Day 18, ~07:12 — 15 min duration
PUMP_TRIP_2_DAY = 23.1      # Day 23, ~02:24 — 8 min duration

# Cleaning cycle
CLEANING_DAY = 25.0
CLEANING_RECOVERY = 0.72    # Restores 72% of lost performance (incomplete due to hardened scale)

# Noise levels (std dev)
NOISE_TEMP = 0.25    # °C
NOISE_FLOW = 0.8     # L/min
NOISE_HTC = 3.0      # W/m²K
NOISE_DP = 0.15      # kPa


def add_noise(value, std):
    return value + random.gauss(0, std)


def compute_cold_outlet(hot_in, hot_out, cold_in, hot_flow, cold_flow):
    """Energy balance: Q_hot = Q_cold → cold_out ≈ cold_in + (hot_in-hot_out)*(hot_flow/cold_flow)*Cp_ratio"""
    cp_ratio = 1.0  # Simplified — assume equal specific heat
    delta_T = (hot_in - hot_out) * (hot_flow / cold_flow) * cp_ratio
    return cold_in + delta_T


def compute_approach_temp(hot_out, cold_out):
    return hot_out - cold_out


def compute_effectiveness(hot_in, hot_out, cold_in):
    """Effectiveness = (hot_in - hot_out) / (hot_in - cold_in)"""
    return (hot_in - hot_out) / (hot_in - cold_in)


def compute_htc(hot_in, hot_out, cold_in, cold_out, hot_flow, cold_flow):
    """Simplified U*A based on LMTD method. Returns approximate HTC."""
    dt1 = hot_in - cold_out
    dt2 = hot_out - cold_in
    if dt1 <= 0 or dt2 <= 0 or abs(dt1 - dt2) < 0.01:
        return INITIAL_HTC
    lmtd = (dt1 - dt2) / math.log(dt1 / dt2)
    Q = hot_flow * 4.18 * (hot_in - hot_out) / 60  # kW
    UA = Q / lmtd * 1000  # W/K
    area = 15.0  # m² (fixed)
    return UA / area  # W/m²K


def generate():
    rows = []
    start_dt = datetime(2025, 3, 1, 0, 0, 0)

    # Track fouling loss for cleaning recovery calculation
    htc_loss_at_cleaning = 0

    for i in range(TOTAL_ROWS):
        t = start_dt + timedelta(minutes=i * INTERVAL_MIN)
        day = i * INTERVAL_MIN / (24 * 60)

        # --- Hot inlet temperature (tightly controlled, small random walk) ---
        hot_in = add_noise(HOT_INLET_NOMINAL, NOISE_TEMP)

        # --- Cold inlet temperature (slow diurnal + seasonal pattern) ---
        diurnal = 1.5 * math.sin(2 * math.pi * day + 1.2)  # ±1.5°C daily cycle
        seasonal = 0.8 * math.sin(2 * math.pi * day / 30)   # ±0.8°C over month
        cold_in = add_noise(COLD_INLET_NOMINAL + diurnal + seasonal, NOISE_TEMP)

        # --- Flow rates ---
        hot_flow = add_noise(HOT_FLOW_NOMINAL, NOISE_FLOW)
        cold_flow = add_noise(COLD_FLOW_NOMINAL, NOISE_FLOW)

        # --- Fouling progression ---
        if day < FOULING_START_DAY:
            htc_decline = 0
            dp_hot_increase = 0
        else:
            days_fouling = day - FOULING_START_DAY
            htc_decline = FOULING_RATE * days_fouling
            dp_hot_increase = FOULING_DP_RATE * days_fouling

        # Water chemistry excursion accelerates fouling after day 9
        if day > CHEM_EXCURSION_DAY:
            # Latent period: deposits take ~3 days to form measurable layer
            htc_decline *= 1.0 + 0.03 * max(0, day - CHEM_EXCURSION_DAY - 3)

        # Cleaning event
        if day >= CLEANING_DAY and htc_loss_at_cleaning == 0:
            htc_loss_at_cleaning = htc_decline

        if htc_loss_at_cleaning > 0:
            residual_loss = htc_loss_at_cleaning * (1 - CLEANING_RECOVERY)
            days_after_cleaning = day - CLEANING_DAY
            # Some re-fouling after cleaning (slower rate)
            refouling = FOULING_RATE * 0.4 * days_after_cleaning
            htc_decline = residual_loss + refouling
            dp_hot_increase = htc_loss_at_cleaning * (FOULING_DP_RATE / FOULING_RATE) * (1 - CLEANING_RECOVERY)
            dp_hot_increase += FOULING_DP_RATE * 0.4 * days_after_cleaning

        # --- Cold water pump trip events (transient spikes) ---
        pump_event = 0
        if abs(day - PUMP_TRIP_1_DAY) < (15 / 1440):  # 15 minutes
            cold_flow *= 0.35  # Loss of cooling water flow
            pump_event = 1
        elif abs(day - PUMP_TRIP_2_DAY) < (8 / 1440):  # 8 minutes
            cold_flow *= 0.42
            pump_event = 1

        # --- Compute derived variables ---
        # Hot outlet: rises as fouling reduces heat transfer
        # Each 100 W/m²K HTC decline → hot_out rises by ~2.8°C
        hot_out = CLEAN_HOT_OUT + htc_decline * 0.028
        hot_out = add_noise(hot_out, NOISE_TEMP)

        cold_out = compute_cold_outlet(hot_in, hot_out, cold_in, hot_flow, cold_flow)
        cold_out = add_noise(cold_out, NOISE_TEMP)

        approach_temp = compute_approach_temp(hot_out, cold_out)
        effectiveness = compute_effectiveness(hot_in, hot_out, cold_in)

        htc = INITIAL_HTC - htc_decline + random.gauss(0, NOISE_HTC)
        dp_hot = INITIAL_DP_HOT + dp_hot_increase + random.gauss(0, NOISE_DP)
        dp_cold = INITIAL_DP_COLD + random.gauss(0, NOISE_DP)

        # Cleaning cycle marker
        is_cleaning = 1 if abs(day - CLEANING_DAY) < (2 / 24) else 0  # 2-hour window

        rows.append({
            'timestamp': t.strftime('%Y-%m-%d %H:%M:%S'),
            'hot_inlet_temp_c': round(hot_in, 2),
            'hot_outlet_temp_c': round(hot_out, 2),
            'cold_inlet_temp_c': round(cold_in, 2),
            'cold_outlet_temp_c': round(cold_out, 2),
            'hot_flow_rate_lpm': round(hot_flow, 2),
            'cold_flow_rate_lpm': round(cold_flow, 2),
            'heat_transfer_coeff_wm2k': round(htc, 1),
            'pressure_drop_hot_kpa': round(dp_hot, 2),
            'pressure_drop_cold_kpa': round(dp_cold, 2),
            'approach_temp_c': round(approach_temp, 2),
            'effectiveness': round(effectiveness, 4),
            'pump_trip_event': pump_event,
            'cleaning_cycle': is_cleaning,
        })

    return rows


def write_csv(rows, filepath):
    fieldnames = list(rows[0].keys())
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == '__main__':
    import os
    rows = generate()
    outpath = os.path.join(os.path.dirname(__file__) or '.', 'heat_exchanger_fouling.csv')
    write_csv(rows, outpath)

    # Print summary
    print(f"Generated {len(rows)} rows × {len(rows[0])} columns")
    print(f"Time range: {rows[0]['timestamp']} → {rows[-1]['timestamp']}")
    print(f"Hot outlet range: {min(r['hot_outlet_temp_c'] for r in rows):.1f} → {max(r['hot_outlet_temp_c'] for r in rows):.1f} °C")
    print(f"HTC range: {min(r['heat_transfer_coeff_wm2k'] for r in rows):.0f} → {max(r['heat_transfer_coeff_wm2k'] for r in rows):.0f} W/m²K")
    print(f"Pump trip events: {sum(1 for r in rows if r['pump_trip_event'])} rows")
    print(f"Saved: {outpath}")
