# -*- coding: utf-8 -*-
"""企业管理场景夹具 —— 验证 line-stability-report 的非设备数据适配性。

D1 生产班组日报：120 天 × 3 班组（A/B/C），注入 B 班一次合格率逐日劣化 +
   C 班 5S 评分高波动；分析时用 group_col/group_filter 拆组评估。
D2 客服运营周报：52 周，注入客户满意度缓慢下滑与响应时长爬升。

Run:  uv run --project .claude/shared/scripts python make_fixtures.py
"""
from __future__ import annotations

import csv
import io
import os
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def _repo_root() -> Path:
    p = ROOT
    while p != p.parent and not (p / ".git").exists():
        p = p.parent
    return p


def _contained(path: Path) -> Path:
    resolved = Path(os.path.normpath(path)).resolve()
    if _repo_root() not in resolved.parents:
        raise ValueError(f"path outside fixture root: {resolved}")
    return resolved


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path = _contained(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    path.write_text(buf.getvalue(), encoding="utf-8", newline="")


def ar1(rng, n, sigma, rho=0.25):
    e = rng.normal(0, sigma, n)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = rho * x[i - 1] + e[i]
    return x


def d1_banzu():
    rng = np.random.default_rng(801)
    days = 120
    d0 = date(2026, 6, 1)
    dates = [(d0 + timedelta(days=i)).isoformat() for i in range(days)]
    rows = []
    for gi, group in enumerate(["A班", "B班", "C班"]):
        t = np.arange(days)
        attend = 96.5 + ar1(rng, days, 0.5)
        output = 218 + ar1(rng, days, 3.5) + (2 if gi == 0 else 0)
        # B班：一次合格率自第 60 天起逐日劣化（-0.02pp/天，累计 -1.2pp）
        qual = 97.8 + ar1(rng, days, 0.12)
        if gi == 1:
            qual = qual - 0.02 * np.clip(t - 60, 0, None)
        loss = 1.8 + ar1(rng, days, 0.08) + (0.01 * np.clip(t - 60, 0, None) if gi == 1 else 0)
        hazard = np.round(np.clip(2.4 + ar1(rng, days, 0.7), 0, None)).astype(int)
        s5 = 88 + ar1(rng, days, 0.4 if gi != 2 else 2.2)  # C班 5S 高波动
        for i in range(days):
            rows.append([dates[i], group, round(attend[i], 2), round(output[i], 1),
                         round(qual[i], 3), round(loss[i], 3), int(hazard[i]),
                         round(s5[i], 1)])
    write_csv(ROOT / "D1_banzu/00_input/banzu_daily_120d.csv",
              ["日期", "班组", "出勤率", "人均产量", "一次合格率", "物料损耗率",
               "安全隐患数", "班组5S评分"], rows)


def d2_service():
    rng = np.random.default_rng(802)
    weeks = 52
    d0 = date(2026, 1, 5)
    dates = [(d0 + timedelta(weeks=i)).isoformat() for i in range(weeks)]
    t = np.arange(weeks)
    volume = 1420 + 90 * np.sin(2 * np.pi * t / 13) + ar1(rng, weeks, 40)
    fcr = 78.5 + ar1(rng, weeks, 0.5)
    resp = 2.6 + 0.012 * t + ar1(rng, weeks, 0.08)          # 响应时长缓慢变长
    csat = 4.42 - 0.008 * t + ar1(rng, weeks, 0.04)         # 满意度缓降
    rows = [[dates[i], round(volume[i], 0), round(fcr[i], 2),
             round(resp[i], 2), round(csat[i], 3)] for i in range(weeks)]
    write_csv(ROOT / "D2_service/00_input/service_weekly_52w.csv",
              ["周开始日期", "工单量", "一次解决率", "平均响应时长", "客户满意度"],
              rows)


if __name__ == "__main__":
    d1_banzu()
    d2_service()
    print("management fixtures written under", ROOT)
