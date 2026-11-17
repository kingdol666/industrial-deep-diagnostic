"""test_p6.py — WS5 anchor_join acceptance cases (frozen interface I10).

Seven scenarios over directly-constructed DataFrames (no shape modules, no
fixtures on disk, no subprocess, no RNG — every fixture is a closed-form
deterministic formula, so there is nothing to seed):

 1. mixed cadence     — 2-min profile vs 30-min camera onto a 10-min anchor;
                        row count/order frozen; dense source eligible, coarse
                        time-limited source coverage ≈ 1/3 → sparse (R2)
 2. staleness         — source that stops early: beyond max_age the cells are
                        NaN, proving no forward-fill / ZOH smuggling
 3. late source       — all stamps after the anchor end → all NaN, effective_n 0
 4. EVT window        — forward-only [event, event+window) with exact boundary
                        behaviour (default 3600 s and contract-supplied window)
 5. duplicate stamps  — aggregate policy: numeric mean, n_inputs sum
 6. transport lag     — declared lag 600 s ⇒ a source-side step appears exactly
                        600 s later on the anchor axis
 7. anchor discipline — unsorted anchor and duplicate anchor stamps raise
                        row-numbered ValueErrors
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

HERE = __import__("pathlib").Path(__file__).resolve().parent
SCRIPTS = HERE.parent.parent / "scripts"
import sys  # noqa: E402

sys.path.insert(0, str(SCRIPTS))

from heterocore import align  # noqa: E402

T0 = datetime(2026, 9, 20, 0, 0, 0)
ISO = "%Y-%m-%d %H:%M:%S"
ANCHOR_N = 3024  # 10-min cadence ⇒ span 30230 min ≈ 21 days
TIME_COL = "时间"


def _stamp(minutes: float) -> str:
    return (T0 + timedelta(minutes=minutes)).strftime(ISO)


def _anchor_df(n: int = ANCHOR_N) -> pd.DataFrame:
    return pd.DataFrame({
        TIME_COL: [_stamp(10 * k) for k in range(n)],
        "温度": [25.0 + 0.001 * k for k in range(n)],
        "压力": [101.0 - 0.0005 * k for k in range(n)],
    })


def _src(sid: str, stamps_min: list[float], cols: dict[str, list], n_inputs=None) -> tuple[str, pd.DataFrame]:
    rows = len(stamps_min)
    if n_inputs is None:
        n_inputs = [1] * rows
    data = {
        "ts": [_stamp(m) for m in stamps_min],
        "_src_ts": [_stamp(m) for m in stamps_min],
        "n_inputs": list(n_inputs),
    }
    data.update({c: list(v) for c, v in cols.items()})
    return sid, pd.DataFrame(data)


def _policy(factor=3.0, ts_source=None, contract_rows=None, lag=None) -> dict:
    p = {"max_age_factor": factor, "duplicate_key_policy": "aggregate",
         "transport_lag_s": lag or {}, "anchor_time_col": TIME_COL}
    if ts_source:
        p["ts_source"] = ts_source
    if contract_rows is not None:
        p["contract_rows"] = contract_rows
    return p


def _updates_by_col(updates: list[dict]) -> dict[str, dict]:
    return {u["column"]: u for u in updates}


# --------------------------------------------------------------- case 1


def case_p6_mixed_cadence():
    out = []
    anchor = _anchor_df()
    # source A: 2-min profile grid ON the anchor stamps, full span (15116 rows)
    a_stamps = [2.0 * j for j in range(15116)]
    a_vals = [100.0 + 0.01 * (j % 97) + 5.0 * np.sin(j / 50.0) for j in range(15116)]
    _, src_a = _src("src_a", a_stamps, {"HX-PROF-A-MEAN": a_vals})
    # source B: 30-min image snapshots, first 336 snapshots (= 7 days) only,
    # camera timing ⇒ staleness factor doubles to 6×30 min = 180 min
    b_stamps = [30.0 * j for j in range(336)]
    _, src_b = _src("src_b", b_stamps, {"HX-IMG-B-MEAN": [50.0 + j for j in range(336)]})

    joined, updates = align.anchor_join(
        anchor, {"src_a": src_a, "src_b": src_b},
        _policy(ts_source={"src_b": "camera"}))
    by = _updates_by_col(updates)

    out.append(("joined row count == anchor", len(joined) == ANCHOR_N, f"{len(joined)}"))
    out.append(("row order unchanged (time column verbatim)",
                joined[TIME_COL].tolist() == anchor[TIME_COL].tolist(), ""))
    out.append(("anchor columns untouched",
                joined[list(anchor.columns)].equals(anchor), ""))
    tail = [c for c in joined.columns if c not in anchor.columns]
    out.append(("feature columns appended at tail, sources sorted",
                tail == ["HX-PROF-A-MEAN", "HX-IMG-B-MEAN"], str(tail)))

    ua = by["HX-PROF-A-MEAN"]
    out.append(("source A coverage == 1.0", ua["coverage"] == 1.0, str(ua["coverage"])))
    out.append(("source A effective_n == 3024", ua["effective_n"] == ANCHOR_N, str(ua["effective_n"])))
    out.append(("source A stats_eligible", ua["stats_eligible"] is True, str(ua)))
    out.append(("source A not sparse", ua["sparse"] is False, str(ua)))
    got = joined["HX-PROF-A-MEAN"].to_numpy()
    exp = np.asarray(a_vals)[::5]  # anchor stamps are every 5th 2-min snapshot
    out.append(("source A exact-time join values",
                np.array_equal(got, exp), f"max|Δ|={np.nanmax(np.abs(got - exp)) if len(got) else 'n/a'}"))

    # B: carried within the 180-min camera cap ⇒ 1024 of 3024 anchor rows non-null
    ub = by["HX-IMG-B-MEAN"]
    cov = ub["coverage"]
    out.append(("source B coverage ≈ 1/3 (measured 1024/3024, band 0.30–0.37)",
                0.30 <= cov <= 0.37 and ub["effective_n"] == 1024, f"coverage={cov:.4f}"))
    out.append(("source B not stats_eligible (< 0.5 — core_stats would drop it, R2)",
                ub["stats_eligible"] is False, str(ub)))
    out.append(("source B sparse (I8: not eligible ⇒ sparse)",
                ub["sparse"] is True, str(ub)))
    out.append(("source B first NaN right after the staleness cap",
                bool(np.isnan(joined["HX-IMG-B-MEAN"].iloc[1024]))
                and not np.isnan(joined["HX-IMG-B-MEAN"].iloc[1023]), ""))
    out.append(("source B spot values (age-0 at k=0, 180-min carry at k=1023)",
                joined["HX-IMG-B-MEAN"].iloc[0] == 50.0
                and joined["HX-IMG-B-MEAN"].iloc[1023] == 385.0, ""))

    frozen = {"column", "coverage", "effective_n", "sparse", "stats_eligible"}
    out.append(("contract_updates keys frozen per column (I10)",
                len(updates) == 2 and all(set(u) == frozen for u in updates),
                str([sorted(u) for u in updates])))
    out.append(("updates values JSON-native types",
                all(isinstance(u["coverage"], float) and isinstance(u["effective_n"], int)
                    and isinstance(u["sparse"], bool) and isinstance(u["stats_eligible"], bool)
                    for u in updates), ""))
    return out


# --------------------------------------------------------------- case 2


def case_p6_staleness_no_zoh():
    out = []
    anchor = _anchor_df()
    # source C: 10-min snapshots on the anchor grid, first 302 rows only;
    # dcs timing ⇒ max_age = 3 × 10 min = 30 min ⇒ carry stops at row 304
    _, src_c = _src("src_c", [10.0 * k for k in range(302)],
                    {"HX-PROF-C-MEAN": [10.0 + k for k in range(302)]})
    joined, updates = align.anchor_join(anchor, {"src_c": src_c}, _policy())
    u = _updates_by_col(updates)["HX-PROF-C-MEAN"]
    col = joined["HX-PROF-C-MEAN"]

    out.append(("row count preserved", len(joined) == ANCHOR_N, str(len(joined))))
    out.append(("effective_n == 302 snapshots + 3 within-cap carries",
                u["effective_n"] == 305, str(u["effective_n"])))
    out.append(("coverage matches measurement exactly",
                abs(u["coverage"] - 305 / ANCHOR_N) < 1e-12, f"{u['coverage']:.6f}"))
    out.append(("within-cap carry still works (k=301..304 non-null)",
                all(not np.isnan(col.iloc[k]) for k in (301, 302, 303, 304)), ""))
    out.append(("carry value at k=304 is the k=301 snapshot (30 min old)",
                col.iloc[304] == 311.0, str(col.iloc[304])))
    out.append(("NO forward fill: k=305 (40 min past last snapshot) is NaN",
                bool(np.isnan(col.iloc[305])), str(col.iloc[305])))
    out.append(("tail rows all NaN (90% of the table)",
                bool(col.iloc[305:].isna().all()), f"NaN rows={int(col.isna().sum())}/{ANCHOR_N}"))
    out.append(("mid-tail spot check is NaN, not a carried value",
                bool(np.isnan(col.iloc[1500])) and bool(np.isnan(col.iloc[3023])), ""))
    out.append(("sparse + not stats_eligible (coverage 0.10)",
                u["sparse"] is True and u["stats_eligible"] is False, str(u)))
    return out


# --------------------------------------------------------------- case 3


def case_p6_late_source():
    out = []
    anchor = _anchor_df(n=60)
    end_min = 10 * 59  # anchor ends at t0+590min
    _, src_d = _src("src_d", [end_min + 10.0 + 30.0 * j for j in range(100)],
                    {"HX-IMG-D-FOCUS": [0.9 + 0.001 * j for j in range(100)]})
    joined, updates = align.anchor_join(anchor, {"src_d": src_d}, _policy())
    u = _updates_by_col(updates)["HX-IMG-D-FOCUS"]
    col = joined["HX-IMG-D-FOCUS"]

    out.append(("late source: every joined cell is NaN",
                bool(col.isna().all()), f"non-null={int(col.notna().sum())}"))
    out.append(("effective_n == 0", u["effective_n"] == 0, str(u["effective_n"])))
    out.append(("coverage == 0.0", u["coverage"] == 0.0, str(u["coverage"])))
    out.append(("sparse and not stats_eligible",
                u["sparse"] is True and u["stats_eligible"] is False, str(u)))
    out.append(("row count preserved", len(joined) == 60, str(len(joined))))
    return out


# --------------------------------------------------------------- case 4


def case_p6_evt_window():
    out = []
    anchor = _anchor_df()
    # one TXT source, two event columns; events at t0+100min (REPAIR, contract
    # window 3600 s) and t0+200min (SCRAP, no contract row ⇒ default 3600 s)
    _, src_e = _src("src_e", [100.0, 200.0, 5000.0],
                    {"HX-TXT-E-EVT-REPAIR": [1, 0, 0],
                     "HX-TXT-E-EVT-SCRAP": [0, 1, 0]})
    contract = [{"column": "HX-TXT-E-EVT-REPAIR", "source_id": "src_e",
                 "ts_source": "manual", "role": "metadata", "evt_window_s": 3600.0}]
    joined, updates = align.anchor_join(anchor, {"src_e": src_e}, _policy(contract_rows=contract))
    by = _updates_by_col(updates)
    rep = joined["HX-TXT-E-EVT-REPAIR"].to_numpy()
    scr = joined["HX-TXT-E-EVT-SCRAP"].to_numpy()

    exp_rep = np.zeros(ANCHOR_N, dtype=int)
    exp_rep[10:16] = 1  # t0+100min … t0+150min: event_ts <= t < event_ts+60min
    out.append(("REPAIR window forward-only, exact 1s at k=10..15",
                np.array_equal(rep, exp_rep), f"ones={np.where(rep == 1)[0].tolist()}"))
    out.append(("boundary t == event+window is 0 (strict <)",
                rep[16] == 0, f"k=16 (t0+160min)={rep[16]}"))
    out.append(("before the event all 0 (no backward window)",
                int(rep[:10].sum()) == 0 and rep[9] == 0, f"pre-sum={int(rep[:10].sum())}"))

    exp_scr = np.zeros(ANCHOR_N, dtype=int)
    exp_scr[20:26] = 1
    out.append(("SCRAP default window 3600 s behaves identically",
                np.array_equal(scr, exp_scr), f"ones={np.where(scr == 1)[0].tolist()}"))
    out.append(("EVT columns are complete 0/1 (never NaN, no asof carry)",
                not np.isnan(rep.astype(float)).any() and set(np.unique(rep)) <= {0, 1}, ""))
    urep = by["HX-TXT-E-EVT-REPAIR"]
    out.append(("EVT coverage 1.0 / effective_n 3024",
                urep["coverage"] == 1.0 and urep["effective_n"] == ANCHOR_N, str(urep)))
    out.append(("contract evt_window_s consumed without error",
                set(by) == {"HX-TXT-E-EVT-REPAIR", "HX-TXT-E-EVT-SCRAP"}, str(sorted(by))))
    return out


# --------------------------------------------------------------- case 5


def case_p6_duplicate_aggregate():
    out = []
    # direct helper check: two rows on the same stamp
    _, dup = _src("src_h", [10.0, 10.0, 20.0],
                  {"HX-PROF-H-MEAN": [5.0, 3.0, 7.0]})
    agg, stamps = align.aggregate_duplicate_stamps(dup, list(pd.to_datetime(dup["ts"])))
    out.append(("stamps deduplicated to 2 rows", len(agg) == 2 and len(stamps) == 2,
                f"rows={len(agg)}"))
    out.append(("aggregated n_inputs = 1+1 = 2",
                float(agg["n_inputs"].iloc[0]) == 2.0, str(agg["n_inputs"].tolist())))
    out.append(("aggregated numeric column = mean(5,3) = 4",
                float(agg["HX-PROF-H-MEAN"].iloc[0]) == 4.0, str(agg["HX-PROF-H-MEAN"].tolist())))
    out.append(("distinct stamp untouched (n_inputs 1, value 7)",
                float(agg["n_inputs"].iloc[1]) == 1.0 and float(agg["HX-PROF-H-MEAN"].iloc[1]) == 7.0, ""))

    # end-to-end: naive backward-asof would carry 3 (the later duplicate row);
    # aggregation must surface the mean 4 instead
    anchor = _anchor_df(n=6)
    joined, updates = align.anchor_join(anchor, {"src_h": dup}, _policy())
    col = joined["HX-PROF-H-MEAN"]
    out.append(("joined at the duplicated stamp carries the mean 4, not 3 or 5",
                col.iloc[1] == 4.0, str(col.iloc[1])))
    out.append(("later stamp joins 7; first anchor row (before any data) NaN",
                col.iloc[2] == 7.0 and bool(np.isnan(col.iloc[0])), str(col.tolist())))
    u = _updates_by_col(updates)["HX-PROF-H-MEAN"]
    out.append(("duplicate rows counted once (effective_n == 5 non-null rows)",
                u["effective_n"] == 5, str(u["effective_n"])))
    return out


# --------------------------------------------------------------- case 6


def case_p6_transport_lag():
    out = []
    anchor = _anchor_df()
    # source G on the anchor grid with a step at k=100 (t0+1000min): 0 → 1
    g_vals = [0.0 if k < 100 else 1.0 for k in range(ANCHOR_N)]
    _, src_g = _src("src_g", [10.0 * k for k in range(ANCHOR_N)], {"HX-PROF-G-STEP": g_vals})
    joined, updates = align.anchor_join(
        anchor, {"src_g": src_g}, _policy(lag={"src_g": 600}))
    col = joined["HX-PROF-G-STEP"]

    out.append(("first anchor rows before the first usable (t-lag) snapshot are NaN",
                bool(np.isnan(col.iloc[0])), str(col.iloc[0])))
    out.append(("source-side pre-step rows join 0 once lag has elapsed",
                float(col.iloc[1]) == 0.0 and float(col.iloc[99]) == 0.0, ""))
    out.append(("at the source step time (k=100) the anchor still shows 0 — held back by lag",
                float(col.iloc[100]) == 0.0, str(col.iloc[100])))
    out.append(("step appears exactly 600 s later: k=101 (t0+1010min) is 1",
                float(col.iloc[101]) == 1.0, str(col.iloc[101])))
    out.append(("lag-shifted pattern exact: rows 1..100 all 0, rows 101.. all 1",
                bool((col.iloc[1:101] == 0.0).all()) and bool((col.iloc[101:] == 1.0).all()), ""))
    u = _updates_by_col(updates)["HX-PROF-G-STEP"]
    out.append(("only the very first row is withheld (effective_n == 3023)",
                u["effective_n"] == ANCHOR_N - 1, str(u["effective_n"])))
    return out


# --------------------------------------------------------------- case 7


def case_p6_anchor_discipline():
    out = []
    good = _anchor_df(n=5)

    shuffled = good.iloc[[0, 2, 1, 3, 4]].reset_index(drop=True)  # rows 1↔2 swapped
    try:
        align.anchor_join(shuffled, {}, _policy())
        out.append(("unsorted anchor raises ValueError", False, "no exception"))
    except ValueError as e:
        msg = str(e)
        import re
        out.append(("unsorted anchor raises ValueError", True, msg[:120]))
        out.append(("message names the violation ('anchor must be time-sorted')",
                    "anchor must be time-sorted" in msg, msg[:160]))
        out.append(("message contains the offending row number",
                    bool(re.search(r"row \d+", msg)), msg[:160]))

    dup = pd.concat([good.iloc[:2], good.iloc[[2]], good.iloc[[2]], good.iloc[[3, 4]]],
                    ignore_index=True)  # rows 2 and 3 share a stamp
    try:
        align.anchor_join(dup, {}, _policy())
        out.append(("duplicate anchor stamps raise ValueError", False, "no exception"))
    except ValueError as e:
        msg = str(e)
        import re
        out.append(("duplicate anchor stamps raise ValueError", True, msg[:120]))
        out.append(("duplicate message names 'duplicate' with a row number",
                    "duplicate" in msg and bool(re.search(r"rows? \d+", msg)), msg[:160]))

    try:
        align.anchor_join(good, {}, {"anchor_time_col": "不存在的列"})
        out.append(("missing anchor_time_col raises", False, "no exception"))
    except ValueError:
        out.append(("missing anchor_time_col raises", True, ""))
    try:
        _, src_x = _src("src_x", [0.0], {"HX-PROF-X-MEAN": [1.0]})
        align.anchor_join(good, {"src_x": src_x}, _policy(lag={"src_x": -5}))
        out.append(("negative transport lag refused (causality)", False, "no exception"))
    except ValueError:
        out.append(("negative transport lag refused (causality)", True, ""))
    try:
        align.anchor_join(good, {}, _policy())
        align.anchor_join(good, {}, dict(_policy(), duplicate_key_policy="subsecond_offset_ms"))
        out.append(("non-aggregate duplicate policy refused, not guessed", False, "no exception"))
    except ValueError:
        out.append(("non-aggregate duplicate policy refused, not guessed", True, ""))
    return out


CASES = [
    ("p6-mixed-cadence", case_p6_mixed_cadence),
    ("p6-staleness-no-zoh", case_p6_staleness_no_zoh),
    ("p6-late-source", case_p6_late_source),
    ("p6-evt-window", case_p6_evt_window),
    ("p6-duplicate-aggregate", case_p6_duplicate_aggregate),
    ("p6-transport-lag", case_p6_transport_lag),
    ("p6-anchor-discipline", case_p6_anchor_discipline),
]
