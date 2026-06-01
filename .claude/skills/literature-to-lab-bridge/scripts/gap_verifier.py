#!/usr/bin/env python3
"""
Gap Verifier — Phase 1.5 of Literature-to-Lab Bridge

Takes identified research gaps from Phase 1 and verifies them through
targeted literature searches. Each gap gets scored on:
  - novelty: 0 (already well-studied) → 1 (truly novel)
  - research_value: composite of impact × feasibility
  - verification_evidence: specific papers found or absence thereof

Output: verified_gaps.json with evidence-based scoring.
"""

import json
import sys
from datetime import datetime, timezone
from typing import Any

GAP_VERIFICATION_PROMPT = """
You are verifying a research gap for the domain: {domain}

The proposed gap is: "{gap_description}"

Your task:
1. Determine if this gap is genuinely under-studied or already addressed in literature
2. Assess the research value (scientific/industrial impact × feasibility)
3. Assign a novelty score (0-10):
   0-3: Well-studied, many papers exist
   4-6: Partially addressed, significant work remains
   7-9: Genuinely novel, very few papers address it
   10: Completely unexplored

Evidence quality scale:
  A = Direct experimental papers exist confirming this is a gap
  B = Indirect evidence (papers on related topics suggest this is open)
  C = Theoretical reasoning only, no confirming/disconfirming papers found
  D = Papers exist that partially or fully address this gap
  E = Multiple papers fully address this gap (gap is closed)

Return JSON:
{{
  "gap_id": "...",
  "novelty_score": 0-10,
  "evidence_grade": "A/B/C/D/E",
  "verified_as_gap": true/false,
  "research_value": {{
    "scientific_impact": 0-10,
    "industrial_impact": 0-10,
    "feasibility": 0-10,
    "composite": 0-10
  }},
  "evidence_summary": "...",
  "papers_found_addressing_gap": [],
  "papers_confirming_gap_exists": [],
  "recommended_priority": "high/medium/low/rejected"
}}
"""


def build_gap_search_queries(gap: dict) -> list[str]:
    desc = gap.get("description", "")
    suggested = gap.get("suggested_experiment", "")

    queries = []

    # Primary: gap description as search query
    if desc:
        # Extract key phrases
        queries.append(desc.strip()[:200])

    # Secondary: suggested experiment keywords
    if suggested:
        words = suggested.split()
        key_terms = [w for w in words if len(w) > 4 and w.lower() not in
                     ('system', 'study', 'should', 'would', 'could', 'using')]
        if key_terms:
            queries.append(" ".join(key_terms[:8]))

    # Tertiary: reverse query (what would disprove the gap)
    queries.append(f"review {desc[:80]}")

    return queries[:3]


def verify_gap(gap: dict, domain: str, all_literature: list[dict]) -> dict:
    gap_id = gap.get("gap_id", "GAP-UNKNOWN")
    desc = gap.get("description", "")

    # Check if any existing paper already addresses this gap
    addressing_papers = []
    confirming_papers = []
    gap_keywords = set(desc.lower().split())

    for paper in all_literature:
        paper_text = json.dumps(paper).lower()
        keyword_hits = sum(1 for kw in gap_keywords if kw in paper_text)
        if keyword_hits >= 3:
            # Check if paper explicitly addresses the gap
            key_finding = paper.get("key_finding", "").lower()
            if any(term in key_finding for term in ["study", "investigate", "measure", "report", "found"]):
                addressing_papers.append(paper.get("source_id", paper.get("title", "")))
            else:
                confirming_papers.append(paper.get("source_id", paper.get("title", "")))

    # Scoring logic
    n_addressing = len(addressing_papers)
    n_confirming = len(confirming_papers)

    if n_addressing == 0 and n_confirming == 0:
        novelty_score = 9
        evidence_grade = "C"
        verified = True
        evidence_summary = "No papers found in current literature dataset addressing this gap. Theoretical reasoning suggests it is open."
    elif n_addressing == 0 and n_confirming <= 2:
        novelty_score = 7
        evidence_grade = "B"
        verified = True
        evidence_summary = f"{n_confirming} papers provide indirect evidence this gap exists, but none directly address it."
    elif n_addressing <= 1:
        novelty_score = 5
        evidence_grade = "B"
        verified = True
        evidence_summary = f"Only {n_addressing} paper partially addresses this gap. Significant room for novel contribution."
    elif n_addressing <= 3:
        novelty_score = 3
        evidence_grade = "D"
        verified = False
        evidence_summary = f"{n_addressing} papers partially address this gap. The gap is narrowing but may still have open questions."
    else:
        novelty_score = 1
        evidence_grade = "E"
        verified = False
        evidence_summary = f"{n_addressing} papers fully address this gap. The gap is effectively closed."

    # Research value scoring
    importance = gap.get("significance", "medium")
    impact_base = {"high": 8, "medium": 6, "low": 4}.get(importance, 5)

    research_value = {
        "scientific_impact": min(10, impact_base + 1),
        "industrial_impact": min(10, impact_base),
        "feasibility": 7 if verified else 3,
        "composite": 0
    }
    research_value["composite"] = round(
        (research_value["scientific_impact"] * 0.4 +
         research_value["industrial_impact"] * 0.3 +
         research_value["feasibility"] * 0.3),
        1
    )

    # Priority
    if not verified:
        priority = "rejected"
    elif novelty_score >= 7 and research_value["composite"] >= 7:
        priority = "high"
    elif novelty_score >= 5:
        priority = "medium"
    else:
        priority = "low"

    return {
        "gap_id": gap_id,
        "description": desc,
        "original_significance": importance,
        "novelty_score": novelty_score,
        "evidence_grade": evidence_grade,
        "verified_as_gap": verified,
        "research_value": research_value,
        "evidence_summary": evidence_summary,
        "papers_addressing_gap": addressing_papers[:5],
        "papers_confirming_gap": confirming_papers[:5],
        "search_queries_for_verification": build_gap_search_queries(gap),
        "recommended_priority": priority,
        "verified_at": datetime.now(timezone.utc).isoformat()
    }


def verify_all_gaps(gaps: list[dict], domain: str, papers: list[dict],
                    experiments: list[dict]) -> dict:
    verified = []
    for gap in gaps:
        result = verify_gap(gap, domain, papers)
        verified.append(result)

    # Sort by research value
    verified.sort(key=lambda g: g["research_value"]["composite"], reverse=True)

    high_count = sum(1 for g in verified if g["recommended_priority"] == "high")
    medium_count = sum(1 for g in verified if g["recommended_priority"] == "medium")
    rejected_count = sum(1 for g in verified if g["recommended_priority"] == "rejected")

    return {
        "total_gaps_input": len(gaps),
        "verified_gaps": sum(1 for g in verified if g["verified_as_gap"]),
        "rejected_gaps": sum(1 for g in verified if not g["verified_as_gap"]),
        "priority_distribution": {
            "high": high_count,
            "medium": medium_count,
            "low": sum(1 for g in verified if g["recommended_priority"] == "low"),
            "rejected": rejected_count
        },
        "gaps": verified,
        "verification_method": "literature_evidence_cross_reference",
        "verification_confidence": "medium",
        "note": "Verification is based on current literature dataset. External searches recommended for gaps graded C (theoretical only)."
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Verify research gaps against literature evidence")
    parser.add_argument("--gaps", required=True, help="Path to literature_summary.json or gaps JSON")
    parser.add_argument("--experiments", required=True, help="Path to experiments_normalized.json")
    parser.add_argument("--papers", required=True, help="Path to source_manifest.json")
    parser.add_argument("--domain", required=True, help="Domain name")
    parser.add_argument("--output", required=True, help="Output path for verified_gaps.json")

    args = parser.parse_args()

    with open(args.gaps) as f:
        gaps_data = json.load(f)
    gaps = gaps_data if isinstance(gaps_data, list) else gaps_data.get("research_gaps", [])

    with open(args.experiments) as f:
        experiments = json.load(f)

    with open(args.papers) as f:
        papers_data = json.load(f)
    papers = papers_data if isinstance(papers_data, list) else papers_data.get("papers", [])

    result = verify_all_gaps(gaps, args.domain, papers, experiments)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(json.dumps({
        "status": "success",
        "total_gaps": result["total_gaps_input"],
        "verified": result["verified_gaps"],
        "rejected": result["rejected_gaps"],
        "high_priority": result["priority_distribution"]["high"]
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()