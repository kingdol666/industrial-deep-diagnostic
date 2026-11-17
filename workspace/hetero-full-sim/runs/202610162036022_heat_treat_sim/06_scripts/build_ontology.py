# -*- coding: utf-8 -*-
"""Deterministic ontology builder — Step 2 (context-builder, fast mode).

Semantics sources (no re-inference):
  - scene spec: 00_input/user_context.json (continuous heat-treatment line, simulated)
  - HX columns: 07_hetero/column_contract.json -> heterocore.contracts.to_ontology_signals
    (VERBATIM merge; null-valued optional keys dropped per schema string-typing)
  - analysis designation: 07_hetero/explicit_cols.json (verbatim, recorded in schema.json)
  - operator annotations: 07_hetero/annotations.json (shift buckets / notes, read-only context)
  - base-column stats: recomputed from the anchor table 07_hetero/preprocessed_data_hetero.csv
  - principle knowledge: first-principles heat-treatment physics (RAG engine localhost:8764
    unreachable -> documented degradation path)

Outputs:
  01_ontology/ontology.json, 01_ontology/schema.json,
  01_ontology/rag_deep_understanding.json + 00_input/rag_deep_understanding.json (same content),
  00_input/clarification_needed.json
"""
import csv
import json
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

RUN_DIR = Path(__file__).resolve().parents[1]
ROOT = RUN_DIR
while not (ROOT / ".claude").exists():
    ROOT = ROOT.parent
SKILLS = ROOT / ".claude" / "skills"
sys.path.insert(0, str(SKILLS / "industrial-hetero-preprocessor" / "scripts"))
from heterocore import contracts  # noqa: E402

ANCHOR = RUN_DIR / "07_hetero" / "preprocessed_data_hetero.csv"
CONTRACT = json.loads((RUN_DIR / "07_hetero" / "column_contract.json").read_text(encoding="utf-8"))
EXPLICIT = json.loads((RUN_DIR / "07_hetero" / "explicit_cols.json").read_text(encoding="utf-8"))
ANNOTATIONS = json.loads((RUN_DIR / "07_hetero" / "annotations.json").read_text(encoding="utf-8"))

BASE_COLS = ["FUR-Z1-TEMP", "FUR-Z2-TEMP", "FUR-Z3-TEMP", "FUR-SPEED", "FUR-PRES", "FUR-OUT-TEMP", "FUR-YIELD"]

# ─────────────────────── probe anchor base columns (recomputable) ───────────────────────
with ANCHOR.open("r", encoding="utf-8-sig", newline="") as fh:
    rows = list(csv.DictReader(fh))
N_ROWS = len(rows)
times = [r["时间"] for r in rows]
T_START, T_END = times[0], times[-1]


def pctl(vals_sorted, p):
    if not vals_sorted:
        return None
    k = (len(vals_sorted) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(vals_sorted) - 1)
    return vals_sorted[lo] + (vals_sorted[hi] - vals_sorted[lo]) * (k - lo)


def rnd(x, d=4):
    return None if x is None else round(x, d)


STAT = {}
for col in BASE_COLS:
    vals = []
    for r in rows:
        v = r.get(col)
        if v is None or v == "":
            continue
        try:
            vals.append(float(v))
        except ValueError:
            pass
    sv = sorted(vals)
    STAT[col] = {
        "n": len(vals),
        "min": rnd(sv[0]) if sv else None,
        "max": rnd(sv[-1]) if sv else None,
        "mean": rnd(statistics.fmean(vals)) if vals else None,
        "std": rnd(statistics.stdev(vals)) if len(vals) > 1 else None,
        "p05": rnd(pctl(sv, 0.05)),
        "p95": rnd(pctl(sv, 0.95)),
    }


def obs(col):
    s = STAT[col]
    return (f"锚定表 1440 行实测: min={s['min']}, max={s['max']}, mean={s['mean']}, "
            f"std={s['std']}, p05={s['p05']}, p95={s['p95']} (source: 07_hetero/preprocessed_data_hetero.csv)")


def nrange(col):
    return [STAT[col]["p05"], STAT[col]["p95"]]


# ─────────────────────── HX verbatim merge via deterministic mapper ───────────────────────
mapped = contracts.to_ontology_signals(CONTRACT)


def strip_nulls(obj):
    if isinstance(obj, dict):
        return {k: strip_nulls(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [strip_nulls(v) for v in obj]
    return obj


HX_PP = [strip_nulls(p) for p in mapped["process_parameters"]]
HX_EVT = [strip_nulls(e) for e in mapped["events"]]

conf_tally = {}
for p in HX_PP:
    conf_tally[p.get("physical_meaning_confidence", "MISSING")] = conf_tally.get(p.get("physical_meaning_confidence", "MISSING"), 0) + 1
if conf_tally.get("UNKNOWN") or conf_tally.get("MISSING"):
    raise SystemExit(f"HX merge produced forbidden confidence values: {conf_tally}")

contract_hx = [c["column"] for c in CONTRACT["columns"] if str(c.get("column", "")).startswith("HX-")]
merged_hx = {p["column"] for p in HX_PP} | {e["column"] for e in HX_EVT}
missing = [c for c in contract_hx if c not in merged_hx]
if missing:
    raise SystemExit(f"contract HX columns missing from mapper output: {missing}")

contract_role_hist = {}
for c in CONTRACT["columns"]:
    key = str(c.get("role"))
    contract_role_hist[key] = contract_role_hist.get(key, 0) + 1

# fallback physics table (degradation path evidence)
p2p = SKILLS / "industrial-ontology-builder" / "resources" / "parameter_to_physics.json"
p2p_matches = []
if p2p.exists():
    try:
        p2p_doc = json.loads(p2p.read_text(encoding="utf-8"))
        tokens = ["temp", "heat", "furnace", "anneal", "speed", "pressure", "hardness", "yield"]
        for k in (p2p_doc.get("parameters") or {}):
            if any(t in k.lower() for t in tokens):
                p2p_matches.append(k)
    except Exception as exc:  # pragma: no cover
        p2p_matches = [f"<read_error: {exc}>"]

# ─────────────────────── scene / equipment / stages ───────────────────────
equipment = [
    {"id": "FUR-Z1", "name": "炉膛一区（预热区）", "type": "加热炉区", "function": "带材入炉预热，降低热冲击", "location": "连续热处理线入口段"},
    {"id": "FUR-Z2", "name": "炉膛二区（加热区）", "type": "加热炉区", "function": "主加热段，带材快速升温", "location": "连续热处理线中段"},
    {"id": "FUR-Z3", "name": "炉膛三区（均热区）", "type": "加热炉区", "function": "保温均热，组织均匀化（操作备注记录设定 880℃）", "location": "连续热处理线出口前段"},
    {"id": "FUR-LINE", "name": "炉线辊道/传动系统", "type": "传输设备", "function": "决定带材运行速度与炉内停留时间 L/v", "location": "全线"},
    {"id": "THERMO-MAP-1", "name": "炉膛温度场测量（5x4 网格）", "type": "温度场测量", "function": "2h 粒度炉膛温度场（含左右不对称/热斑指标）", "location": "炉膛"},
    {"id": "PROFILE-SENSOR-1", "name": "带材横向温度剖面测量", "type": "剖面测量", "function": "30min 粒度带材横向温度剖面（边部/中部/斜度）", "location": "炉线"},
    {"id": "CCD-SURF-1", "name": "表面检查相机（CCD 图像索引）", "type": "表面检测", "function": "1h 粒度表面图像帧统计（未标定，相对监测）", "location": "出料侧"},
    {"id": "LAB-HRC", "name": "实验室硬度抽检（洛氏 C）", "type": "实验室检测", "function": "2h 粒度洛氏硬度抽检（未并入锚定主表，仅作外部验证参照）", "location": "实验室"},
]

stages = [
    {"id": "S1", "name": "入炉预热（一区）", "sequence": 1, "typical_duration": "分钟级（按 L/v 估算，未在数据中声明）",
     "key_physics": "对流+辐射换热升温；升温速率受炉温-带材温差驱动", "key_parameters": ["FUR-Z1-TEMP", "FUR-SPEED"]},
    {"id": "S2", "name": "主加热（二区）", "sequence": 2, "typical_duration": "分钟级（按 L/v 估算）",
     "key_physics": "牛顿换热 Q=hA(T_f−T_s) + 辐射四次方项；停留时间 t_res=L/v 决定吸热量", "key_parameters": ["FUR-Z2-TEMP", "FUR-SPEED", "FUR-PRES"]},
    {"id": "S3", "name": "均热保温（三区）", "sequence": 3, "typical_duration": "分钟级至十几分钟（操作备注设定 880℃）",
     "key_physics": "保温段晶粒长大/组织均匀化（Arrhenius 型动力学）；横向温度均匀性决定带材性能一致性",
     "key_parameters": ["FUR-Z3-TEMP", "HX-PROF-L1BANDTEMPPROFILE30M-MEAN", "HX-PROF-L1BANDTEMPPROFILE30M-STD"]},
    {"id": "S4", "name": "出料与冷却", "sequence": 4, "typical_duration": "秒级-分钟级",
     "key_physics": "冷却速率与终冷温度决定最终组织与硬度（相变动力学）", "key_parameters": ["FUR-OUT-TEMP"]},
    {"id": "S5", "name": "在线表面检查", "sequence": 5, "typical_duration": "1h 粒度",
     "key_physics": "表面氧化/划伤在灰度统计上的响应（未标定）", "key_parameters": ["HX-IMG-L1SURFACECCDINDEX-MEAN", "HX-IMG-L1SURFACECCDINDEX-DARKFRAC"]},
    {"id": "S6", "name": "实验室抽检（离线）", "sequence": 6, "typical_duration": "2h 粒度",
     "key_physics": "硬度-温度-时间关系（退火软化曲线）", "key_parameters": ["LAB-HRC"]},
]

scene = {
    "name": "heat_treat_sim · 连续热处理线（模拟场景，10 天）",
    "process_type": "连续热处理（连续退火/保温热处理炉线：三区炉温 + 传输速度 + 炉内压力控制带材出口温度与性能）",
    "production_goal": "连续生产 10 天；通过三区炉温/线速度/炉压控制带材出口温度与横向温度均匀性，保证硬度与收得率达标",
    "equipment": equipment,
    "stages": stages,
    "objectives": [
        "定位产线质量异常根因并给出证据链",
        "维持三区炉温稳定（操作备注：三区设定 880℃）",
        "保证带材横向温度均匀性（边部偏差/斜度在限内）",
        "保证表面质量与收得率",
    ],
}

# ─────────────────────── base-column signal entries ───────────────────────
def base_param(name, col, unit, role, meaning, conf, conf_basis, law, expected, source="user_provided", **extra):
    e = {
        "name": name, "column": col, "role": role,
        "physical_meaning": meaning,
        "physical_meaning_confidence": conf,
        "auto_inferred": source != "user_provided",
        "inference_basis": conf_basis,
        "normal_range": nrange(col),
        "governing_law": law,
        "expected_data_behavior": expected,
        "observed_data_behavior": obs(col),
        "behavior_match": "UNVERIFIED",
        "discrepancy_signal": "Stage-1 预检仅记录观测范围；与物理预期的一致/矛盾判定由 data-processor（Step 3）完成",
        "knowledge_source": source,
    }
    if unit:
        e["unit"] = unit
    e.update(extra)
    return e


process_parameters = [
    base_param(
        "炉内压力", "FUR-PRES", None, "predictor",
        "炉膛/保护气氛压力（相对值；单位未在数据或文档中声明）",
        "INFERRED",
        "列名 FUR-PRES 指向炉膛压力；单位未声明，按相对漂移量使用",
        "炉压影响炉内气氛与氧化/卷气，属间接质量影响通道",
        "有界波动、与炉门/密封状态及事件相关；不随炉温同步大幅变化",
        equipment_ref="FUR-Z3", stage_ref="S2",
    ),
    base_param(
        "带材出口温度", "FUR-OUT-TEMP", "°C", "target",
        "出料侧带材温度（DCS 实测），决定冷却起点与最终硬度",
        "KNOWN",
        "列名 + 场景描述（连续热处理线出口温度）",
        "Q=hA(T_f−T_s) 与停留时间 t_res=L/v 决定出料温度",
        "低于各区炉温；随炉温上升/速度下降而升高；波动应传导至硬度",
        equipment_ref="FUR-LINE", stage_ref="S4",
    ),
]

y_s = STAT["FUR-YIELD"]
if y_s["max"] is not None and y_s["max"] > 1.0:
    y_unit, y_ub = "%", "观测域 0–100，推断为百分数"
else:
    y_unit, y_ub = "fraction(0-1)", "观测域 0–1，推断为分数"
process_parameters.append(
    base_param(
        "收得率/良率", "FUR-YIELD", y_unit, "target",
        "DCS 上报的产线收得率/良率（质量结果代理）",
        "INFERRED",
        f"列名 FUR-YIELD + {y_ub}",
        "由合格率统计生成，非连续物理量；受温度/表面质量影响",
        "缓慢变化、与质量事件同步下探；不易受单点噪声影响",
        equipment_ref="FUR-LINE", stage_ref="S4",
    )
)
process_parameters.extend(HX_PP)

control_variables = [
    {
        "name": "一区炉温（预热区）", "column": "FUR-Z1-TEMP", "unit": "°C", "role": "control",
        "control_type": "measurement",
        "physical_meaning": "炉膛一区温度实测（预热段）",
        "physical_meaning_confidence": "KNOWN",
        "auto_inferred": False,
        "inference_basis": "列名 FUR-Z1-TEMP + 场景（三区炉线）",
        "controlled_by": "一区温控回路（燃气/电加热执行器，回路细节未声明）",
        "normal_range": nrange("FUR-Z1-TEMP"),
        "governing_law": "一阶热惯性 + 炉膛热平衡（热源 = 对流/辐射散热 + 带材吸热）",
        "expected_data_behavior": "围绕设定值波动、与二/三区热耦合；跨区温差决定升温曲线",
        "observed_data_behavior": obs("FUR-Z1-TEMP"),
        "behavior_match": "UNVERIFIED",
        "discrepancy_signal": "整段漂移或异常波动 = 温控/热电偶/燃控候选根因（操作备注曾记录三区波动偏大并通知仪表检查热电偶）",
        "knowledge_source": "user_provided",
        "equipment_ref": "FUR-Z1", "stage_ref": "S1",
    },
    {
        "name": "二区炉温（加热区）", "column": "FUR-Z2-TEMP", "unit": "°C", "role": "control",
        "control_type": "measurement",
        "physical_meaning": "炉膛二区温度实测（主加热段）",
        "physical_meaning_confidence": "KNOWN",
        "auto_inferred": False,
        "inference_basis": "列名 FUR-Z2-TEMP + 场景（三区炉线）",
        "controlled_by": "二区温控回路（细节未声明）",
        "normal_range": nrange("FUR-Z2-TEMP"),
        "governing_law": "热平衡 + 带材吸热（Q=hA(T_f−T_s)）",
        "expected_data_behavior": "围绕设定值波动；与带材速度负相关（提速吸热增多）",
        "observed_data_behavior": obs("FUR-Z2-TEMP"),
        "behavior_match": "UNVERIFIED",
        "discrepancy_signal": "二区掉温/滞后 = 燃控能力不足或仪表故障候选",
        "knowledge_source": "user_provided",
        "equipment_ref": "FUR-Z2", "stage_ref": "S2",
    },
    {
        "name": "三区炉温（均热区）", "column": "FUR-Z3-TEMP", "unit": "°C", "role": "control",
        "control_type": "measurement",
        "physical_meaning": "炉膛三区温度实测（均热/保温段）；操作备注记录设定 880℃",
        "physical_meaning_confidence": "KNOWN",
        "auto_inferred": False,
        "inference_basis": "列名 FUR-Z3-TEMP + 07_hetero/annotations.json（2026-02-02 交接班：三区温度设定 880℃ 稳定）",
        "setpoint": 880.0,
        "controlled_by": "三区温控回路（2026-02-05 备注：温度波动偏大，已通知仪表检查热电偶）",
        "normal_range": nrange("FUR-Z3-TEMP"),
        "governing_law": "热平衡 + 保温段组织均匀化动力学（Arrhenius）",
        "expected_data_behavior": "稳定在 880℃ 附近（±小幅波动）；直接影响出料温度与硬度",
        "observed_data_behavior": obs("FUR-Z3-TEMP"),
        "behavior_match": "UNVERIFIED",
        "discrepancy_signal": "超过设定附近的正常波动带 = 热电偶/燃控/负荷扰动候选；与硬度波动配对出现则为强证据",
        "knowledge_source": "user_provided",
        "equipment_ref": "FUR-Z3", "stage_ref": "S3",
    },
    {
        "name": "产线速度", "column": "FUR-SPEED", "unit": None, "role": "control",
        "control_type": "measurement",
        "physical_meaning": "带材运行线速度（单位未在数据或文档中声明）；决定炉内停留时间 t_res=L/v",
        "physical_meaning_confidence": "INFERRED",
        "auto_inferred": True,
        "inference_basis": "列名 FUR-SPEED + 热平衡物理：停留时间对吸热量的控制作用",
        "controlled_by": "传动主控（设定值未声明）",
        "normal_range": nrange("FUR-SPEED"),
        "governing_law": "t_res = L / v；吸热量 ∝ t_res·(T_f−T_s)",
        "expected_data_behavior": "围绕工艺设定小幅波动；升速时出料温度下降（负相关、有热惯性滞后）",
        "observed_data_behavior": obs("FUR-SPEED"),
        "behavior_match": "UNVERIFIED",
        "discrepancy_signal": "速度阶跃且出料温度同步偏移 = 传输/工艺调整，而非设备故障",
        "knowledge_source": "user_provided",
        "equipment_ref": "FUR-LINE", "stage_ref": "S1",
    },
]

inspection_signals = [
    {
        "name": "实验室洛氏硬度", "column": "LAB-HRC", "unit": "HRC", "role": "target",
        "physical_meaning": "实验室洛氏 C 硬度抽检（2h 粒度）；未并入锚定主表，仅作外部验证参照（raw/L1_lab_hardness_2h.csv）",
        "physical_meaning_confidence": "KNOWN",
        "auto_inferred": False,
        "inference_basis": "场景描述 + raw/README.md（实验室硬度抽检 2h）+ raw/L1_lab_hardness_2h.csv 表头 LAB-HRC",
        "governing_law": "硬度 ∝ f(均热温度, 保温时间, 冷却速率)；退火软化曲线（Arrhenius 型）",
        "expected_data_behavior": "围绕工艺窗口中心小幅波动；与出口温度/均热温度负相关（升温软化）",
        "behavior_match": "UNVERIFIED",
        "discrepancy_signal": "硬度漂移而同炉温稳定 = 冷却段/来料/抽检偏差候选",
        "knowledge_source": "user_provided",
        "equipment_ref": "LAB-HRC", "stage_ref": "S6",
    },
]

events = HX_EVT

metadata_columns = [
    {"name": "时间戳", "column": "时间", "role": "timestamp",
     "description": f"锚定主表时间列；10min 粒度，{T_START} → {T_END}（{N_ROWS} 行）"},
]

# ─────────────────────── relationships (physics priors) ───────────────────────
def rel(f, t, typ, strength, mech, eq, form, lag, inferred=True):
    return {
        "from": f, "to": t, "type": typ, "strength": strength,
        "mechanism": mech, "governing_equation": eq,
        "predicted_functional_form": form, "time_lag": lag,
        "inferred": inferred, "lag_detection_method": "physics_prior_only",
        "rag_validated": False, "data_direction_validated": "untested",
    }


relationships = [
    rel("FUR-Z3-TEMP", "FUR-OUT-TEMP", "causal", "strong",
        "均热区炉温经对流+辐射换热决定带材出口温度（热平衡）",
        "Q = h·A·(T_f − T_s) + εσA(T_f⁴ − T_s⁴)；T_out ≈ f(T_f, t_res)", "linear",
        "分钟级：接近均热段停留时间 L/v（待数据估计）"),
    rel("FUR-Z2-TEMP", "FUR-OUT-TEMP", "causal", "moderate",
        "加热区炉温通过带材蓄热传导至出料温度", "能量守恒沿带材积分", "linear",
        "分钟级（L/v 量级，待数据估计）"),
    rel("FUR-Z1-TEMP", "FUR-OUT-TEMP", "causal", "weak",
        "预热区对出料温度的间接贡献（降低后续加热负荷）", "能量守恒沿带材积分", "linear",
        "分钟级（L/v 量级，待数据估计）"),
    rel("FUR-SPEED", "FUR-OUT-TEMP", "causal", "strong",
        "提速缩短炉内停留时间→吸热不足→出口温度下降（负相关）", "t_res = L / v；吸热量 ∝ t_res·(T_f−T_s)",
        "inverse", "热惯性滞后（分钟级，待数据估计）"),
    rel("FUR-SPEED", "HX-PROF-L1BANDTEMPPROFILE30M-MEAN", "causal", "moderate",
        "停留时间改变带材整体温度水平，剖面均值随之移动", "t_res = L / v", "inverse",
        "滞后 + 30min 采样量化（待数据估计）"),
    rel("FUR-Z3-TEMP", "HX-MAP-L1FURNACETHERMALMAP2-MEAN", "physical", "strong",
        "炉膛温度场均值应跟随三区（及全线）实测炉温", "场统计量 = 炉温的空间平均", "linear",
        "近零（同一炉膛瞬时耦合；2h 采样量化）"),
    rel("FUR-Z3-TEMP", "HX-MAP-L1FURNACETHERMALMAP2-GRAD-P95", "correlative", "weak",
        "单侧/局部加热不均会使炉温场梯度抬高，与区温设定存在弱耦合", "场的空间梯度统计", "monotonic",
        "近零（空间场与区温同炉膛）"),
    rel("HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR", "HX-PROF-L1BANDTEMPPROFILE30M-EDGE-L-DEV", "causal", "moderate",
        "炉膛左右不对称加热→带材左侧边部温度偏差", "横向热流不对称 → 剖面边部偏差", "linear",
        "分钟级（热传导 + 30min 采样量化）"),
    rel("HX-MAP-L1FURNACETHERMALMAP2-ASYM-LR", "HX-PROF-L1BANDTEMPPROFILE30M-EDGE-R-DEV", "causal", "moderate",
        "炉膛左右不对称加热→带材右侧边部温度偏差", "横向热流不对称 → 剖面边部偏差", "linear",
        "分钟级（热传导 + 30min 采样量化）"),
    rel("HX-PROF-L1BANDTEMPPROFILE30M-MEAN", "FUR-OUT-TEMP", "physical", "strong",
        "一致性检查：在线剖面均值应与 DCS 出料测温同量级同趋势", "同被测量（带材温度）的不同测量通道一致性",
        "linear", "近零（测量一致性；采样粒度差异除外）"),
    rel("FUR-OUT-TEMP", "LAB-HRC", "causal", "strong",
        "终冷温度/均热温度决定组织与硬度（退火软化）", "硬度 = f(T, t)（Arrhenius 型软化动力学）", "monotonic",
        "实验室抽检延迟（2h 采样 + 离线时长，待对齐估计）"),
    rel("HX-PROF-L1BANDTEMPPROFILE30M-MEAN", "LAB-HRC", "causal", "moderate",
        "带材实际温度水平直接影响硬度", "硬度 = f(T, t)（Arrhenius 型软化动力学）", "monotonic",
        "抽检延迟 + 30min 采样量化（待数据估计）"),
    rel("FUR-PRES", "HX-IMG-L1SURFACECCDINDEX-DARKFRAC", "causal", "weak",
        "炉内压力/气氛影响氧化与烟灰沉积→表面暗区占比（未标定图像，相对响应）", "氧化动力学 ∝ f(气氛, T)",
        "threshold", "分钟级至小时级（待数据估计）"),
    rel("HX-TXT-L1OPERATORNOTES-EVT-HEATUP", "FUR-Z2-TEMP", "causal", "moderate",
        "升温事件窗内对应炉温爬升", "事件驱动：加热功率上调 → 炉温上行", "delayed_response",
        "事件窗内（前向 1h 窗口，见事件列描述）"),
    rel("HX-TXT-L1OPERATORNOTES-EVT-MAINTENANCE", "FUR-Z3-TEMP", "causal", "weak",
        "检修事件后继发的仪表/温控扰动（操作备注曾记录通知仪表检查热电偶）", "维护活动 → 环路/传感器状态变化",
        "delayed_response", "检修窗后数小时（待数据估计）"),
]

confounders = [
    {"variable": "环境温度/冷却条件（未记录）", "why": "会同时影响出口温度与硬度，且不在数据结构中", "controlled": False},
    {"variable": "实验室抽检延迟与稀疏性（2h、未并入主表）", "why": "硬度与在线量的时间对齐存在不确定性，可能制造伪相关", "controlled": False},
    {"variable": "CCD 图像未标定（灰度相对值）", "why": "照明/相机漂移会同时影响全部 IMG 统计量", "controlled": False},
    {"variable": "人工操作备注稀疏（9 条/10 天）", "why": "事件漏记会造成事件窗覆盖不全，削弱事件回归", "controlled": False},
    {"variable": "炉膛热电偶状态（2026-02-05 备注：波动偏大、已通知仪表检查）", "why": "仪表故障会同时污染温度读数与基于读数的诊断结论", "controlled": False},
]

parameter_groups = {
    "furnace_zone_temperatures": ["FUR-Z1-TEMP", "FUR-Z2-TEMP", "FUR-Z3-TEMP",
                                  "HX-MAP-L1FURNACETHERMALMAP2-MEAN", "HX-MAP-L1FURNACETHERMALMAP2-P95"],
    "transport_parameters": ["FUR-SPEED"],
    "atmosphere_parameters": ["FUR-PRES"],
    "band_temperature": ["FUR-OUT-TEMP", "HX-PROF-L1BANDTEMPPROFILE30M-MEAN",
                          "HX-PROF-L1BANDTEMPPROFILE30M-STD", "HX-PROF-L1BANDTEMPPROFILE30M-EDGE-L-DEV",
                          "HX-PROF-L1BANDTEMPPROFILE30M-EDGE-R-DEV"],
    "quality_outcomes": ["FUR-YIELD", "LAB-HRC"],
    "surface_inspection": [c for c in contract_hx if c.startswith("HX-IMG-")],
    "hetero_explicit_targets": EXPLICIT.get("targets", []),
    "hetero_explicit_predictors": EXPLICIT.get("predictors", []),
    "hetero_excluded_from_screening": EXPLICIT.get("excludes", []),
}

provenance = {
    "ontology_version": "6.4",
    "generated_by": "context-builder (industrial-ontology-builder, Step 2, fast mode)",
    "run_id": RUN_DIR.name,
    "build_mode": "full",
    "hx_merge": {
        "contract": "07_hetero/column_contract.json",
        "contract_version": CONTRACT.get("contract_version"),
        "mapper": "heterocore.contracts.to_ontology_signals",
        "merged_hx_columns": len(contract_hx),
        "verbatim": True,
        "null_policy": "null-valued optional keys dropped (schema string-typed fields reject null)",
    },
    "rag": {"engine": "http://localhost:8764", "reachable": False,
            "degradation_path": "parameter_to_physics.json + first-principles physics + scene meta-knowledge"},
}

ontology = {
    "scene": scene,
    "signals": {
        "inspection_signals": inspection_signals,
        "process_parameters": process_parameters,
        "control_variables": control_variables,
        "events": events,
        "metadata_columns": metadata_columns,
    },
    "parameter_groups": parameter_groups,
    "relationships": relationships,
    "confounders": confounders,
    "metadata": {
        "units": {
            "FUR-Z1-TEMP": "°C", "FUR-Z2-TEMP": "°C", "FUR-Z3-TEMP": "°C", "FUR-OUT-TEMP": "°C",
            "LAB-HRC": "HRC", "FUR-YIELD": y_unit,
            "FUR-SPEED": "未声明", "FUR-PRES": "未声明",
            "HX-IMG-L1SURFACECCDINDEX-MEAN": "graylevel_8bit",
        },
        "sampling_rate": ("10 min (锚定 DCS)；HX 源粒度: 带材剖面 30min / 炉膛温度场 2h / 表面图像 1h / "
                          "操作备注事件 / 实验室硬度 2h（未并入锚定主表）"),
        "batch_id": "heat_treat_sim_20260202_10d_continuous",
        "timezone": "naive_local（未声明时区）",
        "start_time": T_START.replace(" ", "T"),
        "end_time": T_END.replace(" ", "T"),
    },
    "provenance": provenance,
}

# ─────────────────────── schema.json (normalized classification) ───────────────────────
schema_doc = {
    "schema_version": "1.0",
    "generated_by": "context-builder (industrial-ontology-builder, Step 2, fast mode)",
    "reference": "01_ontology/ontology.json",
    "source_table": "07_hetero/preprocessed_data_hetero.csv",
    "rows": N_ROWS,
    "time_column": "时间",
    "time_span": {"start": T_START, "end": T_END, "cadence": "10 min"},
    "classification": {
        "control_variables": [c["column"] for c in control_variables],
        "process_parameters": [p["column"] for p in process_parameters],
        "targets": ["FUR-OUT-TEMP", "FUR-YIELD"] + EXPLICIT.get("targets", []),
        "inspection_signals": [s["column"] for s in inspection_signals],
        "events": [e["column"] for e in events],
        "metadata_columns": [m["column"] for m in metadata_columns] +
                            [p["column"] for p in HX_PP if p.get("role") == "metadata"],
    },
    "units": ontology["metadata"]["units"],
    "base_column_stats_10d": STAT,
    "hetero_merge": {
        "contract": "07_hetero/column_contract.json",
        "contract_version": CONTRACT.get("contract_version"),
        "mapper": "heterocore.contracts.to_ontology_signals",
        "merged_hx_columns": len(contract_hx),
        "process_parameters": len(HX_PP),
        "events": len(HX_EVT),
        "metadata_columns": len(mapped.get("metadata_columns", [])),
        "confidence_tally_process_parameters": conf_tally,
        "contract_role_histogram": contract_role_hist,
        "explicit_cols": EXPLICIT,
    },
    "null_policy": "null-valued optional keys (unit, …) dropped during merge",
}

# ─────────────────────── rag_deep_understanding.json (R1-R4, degradation) ───────────────────────
rag_doc = {
    "rag_engine": {
        "endpoint": "http://localhost:8764",
        "reachable": False,
        "probe": "HTTP 000 (connection refused/timeout, 2026-10-17)",
        "degraded": True,
        "degradation_path_used": "parameter_to_physics.json (skill resource) + first-principles heat-treatment physics + scene meta-knowledge",
        "fallback_table": str(p2p.relative_to(ROOT)).replace("\\", "/"),
        "fallback_table_matched_entries": p2p_matches[:20],
    },
    "r1_semantic_comprehension": {
        "domain": "连续热处理（金属带材连续退火/均热炉线）",
        "principles": [
            "牛顿换热 + 辐射换热：炉温与带材温差驱动升温/降温（Q = h·A·ΔT + εσAΔT⁴）",
            "停留时间控制：t_res = L/v，速度与吸热量反相关",
            "退火软化动力学：硬度随均热温度/时间按 Arrhenius 型曲线下降",
            "横向均匀性：炉膛左右不对称加热会转化为带材边部温度偏差",
            "气氛/压力影响氧化：炉压异常影响表面质量（灰度统计的可观测渠道）",
        ],
        "failure_modes": [
            "热电偶漂移/故障（操作备注 2026-02-05：三区温度波动偏大，已通知仪表检查）",
            "温控回路能力不足（掉温/超调）",
            "速度与炉温失配（提速未同步提温 → 欠热）",
            "炉膛局部热斑/左右不对称",
            "炉压异常导致氧化/表面缺陷",
            "维护/升温事件后的过渡期扰动",
        ],
        "confounders": [c["variable"] for c in confounders],
    },
    "r2_knowledge_data_alignment": {
        "stage": "STAGE_1_PRECHECK",
        "method": "锚定主表（1440×48）基础列统计预检；HX 列沿用 contract 语义；未做完整统计分析（属 data-processor / Stage 3）",
        "claim_validations": [
            {"claim": "三区温度稳定在设定 880℃ 附近（操作备注 2026-02-02）",
             "source": "07_hetero/annotations.json",
             "method": f"锚定表 FUR-Z3-TEMP: mean={STAT['FUR-Z3-TEMP']['mean']}, std={STAT['FUR-Z3-TEMP']['std']}, p05={STAT['FUR-Z3-TEMP']['p05']}, p95={STAT['FUR-Z3-TEMP']['p95']}",
             "result": "QUANTIFIED", "status": "defer_to_stage2"},
            {"claim": "出口温度应低于炉温（升温路径）",
             "source": "physics",
             "method": f"mean(FUR-OUT-TEMP)={STAT['FUR-OUT-TEMP']['mean']} vs mean(FUR-Z3-TEMP)={STAT['FUR-Z3-TEMP']['mean']}",
             "result": "QUANTIFIED", "status": "defer_to_stage2"},
            {"claim": "产线速度应基本恒定（连续生产）",
             "source": "scene",
             "method": f"FUR-SPEED: min={STAT['FUR-SPEED']['min']}, max={STAT['FUR-SPEED']['max']}, std={STAT['FUR-SPEED']['std']}",
             "result": "QUANTIFIED", "status": "defer_to_stage2"},
            {"claim": "硬度应在工艺窗口内小幅波动",
             "source": "scene",
             "method": "LAB-HRC 未并入锚定主表（raw/L1_lab_hardness_2h.csv，2h 粒度）",
             "result": "NOT_TESTED", "status": "untestable_stage1"},
        ],
        "validation_queue": [
            "FUR-Z3-TEMP 与 LAB-HRC 的滞后互相关（含滞后补偿）——Stage 2/3 执行",
            "FUR-SPEED 与 FUR-OUT-TEMP 的负相关方向验证——Stage 2/3 执行",
            "HX-MAP ASYM-LR 与 PROF EDGE-*-DEV 的横向偏差传导——Stage 2/3 执行",
            "EVT-MAINTENANCE/HEATUP 事件窗内炉温偏离显著性——Stage 2/3 执行",
        ],
    },
    "r3_physics_principle_extraction": {
        "conservation_laws": ["能量守恒（炉膛热源 = 带材吸热 + 散热）", "质量守恒（连续流）"],
        "constitutive_relations": ["Newton 对流换热 Q=hAΔT", "Stefan-Boltzmann 辐射 Q=εσA(T_f⁴−T_s⁴)",
                                    "Arrhenius 动力学 k=k0·exp(−Ea/RT)"],
        "scaling_laws": ["t_res = L/v（停留时间反比于速度）", "热扩散时间 ∝ L²/α（横向均匀性尺度）"],
        "threshold_physics": ["氧化速率随温度非线性抬升（表面质量阈值）", "欠热阈值：t_res·ΔT 低于临界值时组织不合格"],
    },
    "r4_gap_aware_integration": {
        "unmatched_parameters": ["FUR-SPEED / FUR-PRES 单位未声明（按相对量使用）",
                                  "冷却段参数未记录（冷却速率是硬度的重要因子）",
                                  "来料状态（成分/厚度）未记录"],
        "unexplained_relationships": ["LAB-HRC 与在线量仅在 2h 抽检粒度上可比，未并入主表 → 需要滞后对齐",
                                       "CCD 图像未标定 → IMG 统计量只能作相对漂移使用"],
        "domain_distance": "LOW（场景与列名自描述性强；物理先验完备）",
        "notes": "RAG 不可用时按文档化降级路径构建；所有 HX 语义来自 contract 确定性映射（未再推断）",
    },
}

clarification_doc = {
    "clarification_status": "AUTO_RESOLVED",
    "interaction_mode": "auto",
    "run_mode": "fast",
    "questions": [],
    "auto_resolutions": [
        {"item": "场景与工艺类型", "method": "scene spec", "resolution": "连续热处理线（模拟场景），10 天连续生产", "basis": "00_input/user_context.json"},
        {"item": "FUR-SPEED / FUR-PRES 单位", "method": "L2 (unit undeclared)", "resolution": "按相对量使用；unit 键省略，不做虚构标定", "basis": "数据与文档均未声明单位"},
        {"item": "FUR-YIELD 量纲", "method": "L4 (value-domain inference)", "resolution": f"按观测域 {STAT['FUR-YIELD']['min']}–{STAT['FUR-YIELD']['max']} 推断为 {y_unit}", "basis": "锚定表实测取值域"},
        {"item": "三区设定温度", "method": "L2 (operator record)", "resolution": "880 ℃（2026-02-02 交接班备注）", "basis": "07_hetero/annotations.json"},
        {"item": "HX 列语义", "method": "contract (authoritative)", "resolution": "40 列全部取自 column_contract.json 确定性映射（37+2EVT+…，零再推断）", "basis": "07_hetero/column_contract.json"},
    ],
    "notes": "场景完整指定（模拟），无待澄清问题；所有 FUR-* 基础列语义与物理角色已由场景/物理先验确定。",
}

# ─────────────────────── write outputs ───────────────────────
out_ont = RUN_DIR / "01_ontology" / "ontology.json"
out_sch = RUN_DIR / "01_ontology" / "schema.json"
out_rag1 = RUN_DIR / "01_ontology" / "rag_deep_understanding.json"
out_rag2 = RUN_DIR / "00_input" / "rag_deep_understanding.json"
out_clar = RUN_DIR / "00_input" / "clarification_needed.json"

for path, doc in [(out_ont, ontology), (out_sch, schema_doc), (out_rag1, rag_doc), (out_rag2, rag_doc), (out_clar, clarification_doc)]:
    # null-policy: drop null-valued optional keys everywhere (schema string fields reject null)
    path.write_text(json.dumps(strip_nulls(doc), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

summary = {
    "ontology_bytes": out_ont.stat().st_size,
    "schema_bytes": out_sch.stat().st_size,
    "rag_bytes": out_rag1.stat().st_size,
    "clarification_bytes": out_clar.stat().st_size,
    "rows": N_ROWS,
    "time_span": [T_START, T_END],
    "base_stats": STAT,
    "furyield_unit_decision": y_unit,
    "hx": {
        "contract_columns": len(contract_hx),
        "merged_process_parameters": len(HX_PP),
        "merged_events": len(HX_EVT),
        "confidence_tally": conf_tally,
        "unknown_count": conf_tally.get("UNKNOWN", 0),
        "contract_role_histogram": contract_role_hist,
    },
    "process_parameters_total": len(process_parameters),
    "control_variables": len(control_variables),
    "inspection_signals": len(inspection_signals),
    "relationships": len(relationships),
    "fallback_table_matches": len(p2p_matches),
}
print(json.dumps(summary, ensure_ascii=False, indent=2))
