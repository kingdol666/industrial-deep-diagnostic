"""Subject & scenario resolution — adaptive narrative without hard-coding 产线.

Answers "what is being analyzed" from, in priority order:
  1. context.scenario  (free text, e.g. "注塑车间能耗监控" / "production_line")
  2. ontology scene    (condition.scene.name / process_type from the asset)
  3. context.line_id / context.product (legacy production-line fields)
  4. default           (generic subject for any numeric time-series)

The resolved subject drives the conclusion sentence and the HTML hero, so a
factory line reads 产线, an energy/lab/building system reads 系统, and an
unclassified dataset reads the neutral 对象 — same numbers, right wording.
"""
from __future__ import annotations

_NOUN_RULES = (
    (("产线", "line", "production", "工厂", "车间", "factory"), "产线"),
    (("系统", "system", "机组", "装置", "设备", "unit", "plant", "能耗", "空调",
      "锅炉", "反应", "实验室", "lab", "建筑", "楼宇", "污水处理", "hvac"), "系统"),
)


def _noun_from_text(text: str) -> str | None:
    low = (text or "").lower()
    for needles, noun in _NOUN_RULES:
        if any(n in low for n in needles):
            return noun
    return None


def resolve_subject(context: dict, condition: dict) -> dict:
    """Return {noun, display, source}.

    noun    — 产线 | 系统 | 对象 (drives sentence templates)
    display — human-readable scenario name for the hero chip (may be None)
    source  — context.scenario | ontology.scene | context.line | default
    """
    scenario = (context.get("scenario") or "").strip()
    if scenario:
        return {"noun": _noun_from_text(scenario) or "系统",
                "display": scenario, "source": "context.scenario"}

    scene = (condition or {}).get("scene") or {}
    scene_name = (scene.get("name") or "").strip()
    scene_text = " ".join(filter(None, [scene_name, scene.get("process_type"),
                                        scene.get("production_goal")]))
    if scene_text.strip():
        noun = _noun_from_text(scene_text)
        if scene_name:
            return {"noun": noun or "系统", "display": scene_name,
                    "source": "ontology.scene"}
        if noun:
            return {"noun": noun, "display": None, "source": "ontology.scene"}

    if context.get("line_id") or context.get("product"):
        display = context.get("line_id") or context.get("product")
        return {"noun": "产线", "display": display, "source": "context.line"}

    return {"noun": "对象", "display": None, "source": "default"}


def sentence_subject(noun: str) -> str:
    """Sentence opener for the conclusion statement."""
    return {"产线": "该产线", "系统": "该系统"}.get(noun, "被评估对象")
