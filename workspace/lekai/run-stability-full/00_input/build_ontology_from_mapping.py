"""Build the line-stability ontology for the lekai FW3 MD-stretching report.

Semantic source: data/lekaiData/parameter_mapping.json
  (_meta.verified_by = "逐行比对XLSX映射表与aligned_multidefect.csv实际数据")

Design rules (user-ruled, enforced by assertions at the bottom):
  * every signal column string is byte-identical to merged_process_data_full.csv header
  * NO normal_range / spec / lsl / usl / target / tolerance in any form
    -> Cpk is not computed (no spec source exists)
  * NO unit (parameter_mapping._meta.unverified_fields declares unit as
    physics-common-sense inference only)
  * typical_from_data is deliberately EXCLUDED (self-referential, not a spec)
  * NO governing_law per signal: parameter_mapping provides no verified control
    equation; the three algebraic identities in derived_parameters are emitted
    as relationships.governing_equation instead
"""
from __future__ import annotations

import csv
import json
import os

REPO = r"D:\codes\industrial-deep-diagnostic"
MAIN_CSV = os.path.join(REPO, "data", "lekaiData", "merged_process_data_full.csv")
MAPPING = os.path.join(REPO, "data", "lekaiData", "parameter_mapping.json")
OUT = os.path.join(REPO, "workspace", "lekai", "run-stability-full", "00_input", "ontology.json")

ZONE_NEAR = "预加热段 (near Tg)"
ZONE_ABOVE = "拉伸段 (above Tg)"
ZONE_QUENCH = "急冷定型段 (<< Tg)"
ZONE_MELT = "熔体挤出段 (upstream)"

# roll-number -> (temperature column, torque column), from parameter_mapping.parameters[].roll
TEMP_BY_ROLL = {r: f"MD_TH{r:03d}@PV" for r in range(1, 19)}
TORQUE_BY_ROLL = {
    1: "W1C7C@PV1", 2: "W1C7D@PV1", 3: "W1C7E@PV1", 4: "W1C7F@PV1", 5: "W1C80@PV1",
    6: "W1C81@PV1", 7: "W1C82@PV1", 8: "W1C83@PV1", 9: "W1C84@PV1", 10: "W1C85@PV1",
    11: "W1C86@PV1", 12: "W1C87@PV1", 13: "W1C88@PV1", 14: "W1C89@PV1", 15: "W1C8A@PV1",
    16: "W1C8B@PV1", 17: "W1C8C@PV1", 18: "W1C8D@PV1",
}


def zone_temp(roll: int) -> str:
    return ZONE_NEAR if roll <= 5 else (ZONE_ABOVE if roll <= 11 else ZONE_QUENCH)


def zone_torque(roll: int) -> str:
    return ZONE_NEAR if roll <= 5 else (ZONE_ABOVE if roll <= 11 else ZONE_QUENCH)


TEMP_GROUPS = [("MD纵拉辊温度·预加热段", range(1, 6)),
               ("MD纵拉辊温度·拉伸段", range(6, 12)),
               ("MD纵拉辊温度·急冷定型段", range(12, 19))]
TORQUE_GROUPS = [("MD纵拉辊扭矩·预加热段", range(1, 6)),
                 ("MD纵拉辊扭矩·拉伸段", range(6, 12)),
                 ("MD纵拉辊扭矩·急冷定型段", range(12, 19))]

# stage_ref / equipment_ref for the non-roll channels (from parameter_mapping
# process_equipment[].measured_parameters + xlsx_label)
SIMPLE = {
    "W1C40@PV1": (ZONE_NEAR, "md_stretcher"),
    "W1C4B@PV1": (ZONE_ABOVE, "md_stretcher"),
    "W1C00@PV1": (ZONE_MELT, "main_extruder"),
    "F_PS002@PV1": (ZONE_MELT, "main_extruder"),
    "F_PS003@PV1": (ZONE_MELT, "main_extruder"),
    "W1C01@PV1": (ZONE_MELT, "secondary_extruder"),
    "F_PS005@PV1": (ZONE_MELT, "secondary_extruder"),
    "F_PS006@PV1": (ZONE_MELT, "secondary_extruder"),
}

TG_NOTE = "跨越 PET Tg（≈75°C）进入拉伸段"
QUENCH_NOTE = "由拉伸段降至远低于 PET Tg 的急冷定型区"

EXTRA_MEANING = {
    "MD_TH006@PV": TG_NOTE,
    "MD_TH012@PV": QUENCH_NOTE,
}


def main() -> None:
    with open(MAPPING, encoding="utf-8") as f:
        mapping = json.load(f)
    params = mapping["parameters"]

    with open(MAIN_CSV, encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f))
    time_col, columns = header[0], header[1:]

    def entry(col: str, group: str, stage: str, equip: str) -> dict:
        p = params[col]
        meaning = p["physical_meaning"]
        if col in EXTRA_MEANING:
            meaning = f"{meaning}（{EXTRA_MEANING[col]}）"
        return {
            "column": col,
            "name": p["physical_meaning"],
            "role": "parameter",
            "stage_ref": stage,
            "equipment_ref": equip,
            "physical_meaning": meaning,
            "source": "parameter_mapping.json (XLSX mapping + data verified)",
        }

    signals: dict[str, list] = {}
    for gname, rolls in TEMP_GROUPS:
        signals[gname] = [entry(TEMP_BY_ROLL[r], gname, zone_temp(r), "md_stretcher") for r in rolls]
    for gname, rolls in TORQUE_GROUPS:
        signals[gname] = [entry(TORQUE_BY_ROLL[r], gname, zone_torque(r), "md_stretcher") for r in rolls]
    signals["MD纵拉辊速与拉伸比"] = [
        entry("W1C40@PV1", "MD纵拉辊速与拉伸比", ZONE_NEAR, "md_stretcher"),
        entry("W1C4B@PV1", "MD纵拉辊速与拉伸比", ZONE_ABOVE, "md_stretcher"),
    ]
    signals["挤出机转速与熔体压力"] = [
        entry(c, "挤出机转速与熔体压力", *SIMPLE[c])
        for c in ["W1C00@PV1", "F_PS002@PV1", "F_PS003@PV1",
                  "W1C01@PV1", "F_PS005@PV1", "F_PS006@PV1"]
    ]

    ontology = {
        "ontology_version": "lekai-fw3-mdo/1.0",
        "scene": {
            "name": "乐凯 FW3 BOPET 产线 · MD 纵拉段",
            "process_type": "BOPET 双向拉伸薄膜 — 熔体挤出 → 纵向拉伸 (MDO 18 辊) 连续生产",
            "production_goal": "在 PET Tg 以上完成纵向拉伸取向，随后急冷定型，"
                               "稳定获得厚度与取向一致的薄膜",
            "equipment": [
                {"id": e["id"], "name": e["name"], "function": e["function"]}
                for e in mapping["process_equipment"]
            ],
            "stages": [
                {"stage": ZONE_MELT, "range": "上游", "columns": [c for c in columns if c.endswith("@PV1") and c not in ("W1C40@PV1", "W1C4B@PV1")],
                 "description": "主/辅挤出机熔融挤出与过滤（主过滤器前/后熔体压力）"},
                {"stage": ZONE_NEAR, "range": "1#–5# 辊", "columns": [TEMP_BY_ROLL[r] for r in range(1, 6)] + [TORQUE_BY_ROLL[r] for r in range(1, 6)] + ["W1C40@PV1"],
                 "description": "辊温贴近 PET Tg（≈75°C），薄膜预热、尚未取向；1# 辊为拉伸入口慢辊"},
                {"stage": ZONE_ABOVE, "range": "6#–11# 辊", "columns": [TEMP_BY_ROLL[r] for r in range(6, 12)] + [TORQUE_BY_ROLL[r] for r in range(6, 12)] + ["W1C4B@PV1"],
                 "description": "辊温升至 Tg 以上，纵向拉伸取向发生区；12# 辊为拉伸出口快辊，与 1# 辊速度之比即拉伸比"},
                {"stage": ZONE_QUENCH, "range": "12#–18# 辊", "columns": [TEMP_BY_ROLL[r] for r in range(12, 19)] + [TORQUE_BY_ROLL[r] for r in range(12, 19)],
                 "description": "温度远低于 Tg，拉伸后的取向结构被急冷冻结定型"},
            ],
        },
        "signals": signals,
        "parameter_groups": {g: [e["column"] for e in entries] for g, entries in signals.items()},
        "relationships": [
            {"from": "W1C4B@PV1", "to": "W1C40@PV1", "type": "derived_parameter",
             "strength": None,
             "mechanism": "MD 纵向拉伸比 = 12#（出口快辊）线速度 ÷ 1#（入口慢辊）线速度；"
                          "来源 parameter_mapping.derived_parameters.MD_DRAW_RATIO",
             "governing_equation": "W1C4B@PV1 / W1C40@PV1"},
            {"from": "F_PS002@PV1", "to": "F_PS003@PV1", "type": "derived_parameter",
             "strength": None,
             "mechanism": "主过滤器压差 = 主过滤器前熔体压力 − 主过滤器后熔体压力；"
                          "来源 parameter_mapping.derived_parameters.MF_FILTER_DELTA_P",
             "governing_equation": "F_PS002@PV1 - F_PS003@PV1"},
            {"from": "F_PS005@PV1", "to": "F_PS006@PV1", "type": "derived_parameter",
             "strength": None,
             "mechanism": "辅过滤器压差 = 辅过滤器前熔体压力 − 辅过滤器后熔体压力；"
                          "来源 parameter_mapping.derived_parameters.SF_FILTER_DELTA_P",
             "governing_equation": "F_PS005@PV1 - F_PS006@PV1"},
        ],
        "confounders": [
            {"variable": "产品型号/规格切换（同期 11 个型号、149 批次）",
             "why": "换规格会改变温度与辊速设定，在时间序列上形成工况台阶；"
                    "不做型号分层的漂移/波动归因会把台阶误读为过程失控",
             "controlled": False},
            {"variable": "人工调参与工艺调整动作（本期无 action_log）",
             "why": "缺少调参动作台账，无法区分“操作引起的台阶”与“过程自发漂移”",
             "controlled": False},
            {"variable": "慢变设备状态（滤网堵塞、模头结垢、辊面状态等）",
             "why": "原始数据无设备状态直接记录，此类状态只能以缓慢累积效应间接体现",
             "controlled": False},
        ],
        "metadata": {
            "units": {},
            "source_document": "data/lekaiData/parameter_mapping.json",
            "source_verified_by": mapping["_meta"]["verified_by"],
            "source_confidence": mapping["_meta"]["confidence"],
            "source_unverified_fields": mapping["_meta"]["unverified_fields"],
            "source_scene": mapping["scene"],
            "main_table": "data/lekaiData/merged_process_data_full.csv",
            "time_col": time_col,
            "column_count": len(columns),
            "deliberately_empty": {
                "unit": "parameter_mapping._meta.unverified_fields 声明单位为物理常识推断，未在数据中确认 → 全部留空",
                "normal_range/target/spec": "用户裁定无规格限；parameter_mapping.typical_from_data 为自参照口径，明令不得当规格 → 全部留空，Cpk 不计算",
                "governing_law": "parameter_mapping 未提供经核验的控制方程 → 逐信号留空；"
                                 "仅 3 个代数恒等式写入 relationships.governing_equation",
            },
            "constructed_by": "workspace/lekai/run-stability-full/00_input/build_ontology_from_mapping.py",
        },
    }

    # ---- contract assertions (fail loudly instead of emitting a bad ontology)
    exported = [e["column"] for entries in signals.values() for e in entries]
    assert len(exported) == len(columns), f"column count {len(exported)} != {len(columns)}"
    assert sorted(exported) == sorted(columns), "ontology columns != CSV header"
    assert len(set(exported)) == len(exported), "duplicate column in ontology"
    for col in columns:
        assert col in params, f"column {col} missing from parameter_mapping.parameters"
    # the machine-read sections must carry no spec/unit material at all
    blob = json.dumps({k: ontology[k] for k in
                       ("signals", "parameter_groups", "relationships", "scene")},
                      ensure_ascii=False)
    for bad in ("normal_range", "spec", "lsl", "usl", "tolerance",
                "typical_from_data", "unit", "target"):
        assert bad not in blob, f"forbidden token present in machine-read sections: {bad}"
    for entries in signals.values():
        for e in entries:
            assert set(e) == {"column", "name", "role", "stage_ref",
                              "equipment_ref", "physical_meaning", "source"}, e

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(ontology, f, ensure_ascii=False, indent=2)
    print(f"OK ontology -> {OUT}")
    print(f"columns={len(exported)} groups={len(signals)} relationships={len(ontology['relationships'])} "
          f"confounders={len(ontology['confounders'])}")


if __name__ == "__main__":
    main()
