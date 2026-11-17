"""imacore.chains — physical mechanism chain assembly from the ontology.

门B inputs per (lever, kpi):
  * relationships[] edge lever→kpi WITH a usable direction that agrees with
    the data-implied effect sign  → status "known"
  * edge without direction, or dictionary/physical_meaning prior only
    → status "same_domain"
  * nothing  → status "unknown" (grade capped at C, [MECHANISM_UNKNOWN])

No direction declaration → no causal edge is invented (house rule).
"""


def _flatten_signals(ontology):
    if not isinstance(ontology, dict):
        return {}
    signals = ontology.get("signals") if isinstance(ontology.get("signals"), dict) else {}
    out = {}
    for bucket, items in signals.items():
        for sig in items or []:
            if isinstance(sig, dict) and sig.get("column"):
                entry = dict(sig)
                entry["_bucket"] = bucket
                out[str(sig["column"])] = entry
    return out


def _edge_direction(rel):
    """Direction carried by a relationship edge, if any ('+'/'-')."""
    for key in ("expected_sign", "direction", "sign"):
        value = rel.get(key)
        if isinstance(value, str):
            v = value.strip()
            if v in ("+", "-"):
                return v
            lower = v.lower()
            if lower in ("increase", "positive", "up", "increases"):
                return "+"
            if lower in ("decrease", "negative", "down", "decreases"):
                return "-"
    return None


def mechanism_for(ontology, lever, kpi, slope_sign):
    """slope_sign: sign of dKPI/dlever as estimated from THIS data (+1/−1/0).

    Ontology `expected_sign` is declared in the same dKPI/dlever convention
    (DOE semantics), so agreement is `declared == sign(slope)` — NOT the sign
    of the KPI change under the suggested move (a suggested decrease would
    otherwise flip a correct edge into a false contradiction).

    Returns {"status": "known"|"same_domain"|"unknown", "reason": str|None,
             "chain": [{step, ontology_ref}], "edges": [...]}.
    """
    signals = _flatten_signals(ontology)
    lever_sig = signals.get(lever) or {}
    kpi_sig = signals.get(kpi) or {}
    chain = []
    refs = []

    meaning = lever_sig.get("physical_meaning")
    if meaning:
        chain.append({"step": f"杠杆 {lever} 的物理含义：{meaning}",
                      "ontology_ref": f"signals.{lever_sig.get('_bucket')}[column={lever}].physical_meaning"})
        refs.append("lever_meaning")
    law = lever_sig.get("governing_law")
    if law:
        chain.append({"step": f"控制方程/物理律：{law}",
                      "ontology_ref": f"signals.{lever_sig.get('_bucket')}[column={lever}].governing_law"})
        refs.append("lever_law")
    kpi_meaning = kpi_sig.get("physical_meaning")
    if kpi_meaning:
        chain.append({"step": f"目标 KPI {kpi} 的物理含义：{kpi_meaning}",
                      "ontology_ref": f"signals.{kpi_sig.get('_bucket')}[column={kpi}].physical_meaning"})
        refs.append("kpi_meaning")

    rels = ontology.get("relationships") if isinstance(ontology, dict) else []
    edges = []
    for rel in rels or []:
        if not isinstance(rel, dict):
            continue
        frm = str(rel.get("from") or "")
        to = str(rel.get("to") or "")
        if {frm, to} == {lever, kpi}:
            edges.append(rel)
    for rel in edges:
        direction = _edge_direction(rel)
        mechanism = rel.get("mechanism") or ""
        step = (f"机制边 {rel.get('from')}→{rel.get('to')} "
                f"({rel.get('type') or 'causal'})：{mechanism}".strip())
        chain.append({"step": step,
                      "ontology_ref": f"relationships[from={rel.get('from')},to={rel.get('to')}]"})
        refs.append("relationship")
        if direction is None or slope_sign == 0:
            continue
        want = "+" if slope_sign > 0 else "-"
        if direction != want:
            return {"status": "unknown", "reason": "mechanism_contradicted",
                    "chain": chain, "edges": edges}
    if any(_edge_direction(rel) for rel in edges):
        chain.append({"step": "声明机制方向与本次数据建议方向一致",
                      "ontology_ref": "relationships[*].expected_sign"})
        return {"status": "known", "reason": None, "chain": chain, "edges": edges}
    if refs:
        chain.append({"step": "无方向声明：机制为同域先验（不构成因果边）",
                      "ontology_ref": "ontology.limitations"})
        return {"status": "same_domain", "reason": None, "chain": chain, "edges": edges}
    chain.append({"step": "[MECHANISM_UNKNOWN] 本体无该杠杆/KPI 的机理信息，"
                          "建议先建/补本体或用小试验证",
                  "ontology_ref": "ontology.scene"})
    return {"status": "unknown", "reason": "mechanism_absent", "chain": chain,
            "edges": edges}
