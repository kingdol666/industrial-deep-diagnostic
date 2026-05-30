#!/usr/bin/env python3
"""
Main pipeline execution runner.
Invoke: python run_pipeline.py --manifest config/manifest.json
Or call individual modules via --module N
"""

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def emit_event(event: str, **kwargs):
    record = {"event": event, "timestamp": datetime.now(timezone.utc).isoformat(), **kwargs}
    print(json.dumps(record), file=sys.stderr)


def run_module_1_literature_acquisition(manifest: dict, output_dir: Path) -> dict:
    emit_event("module_start", module=1, module_name="literature_acquisition")

    search_config = manifest.get("search_config", {})
    keywords = search_config.get("keywords", manifest.get("search_terms", []))
    sources = search_config.get("sources", ["semantic_scholar", "pubmed", "google_scholar"])
    year_from = search_config.get("year_from", 2015)
    year_to = search_config.get("year_to", 2025)
    max_results = search_config.get("max_results", 50)

    emit_event("module_log", module=1,
               message=f"Searching {len(sources)} sources for keywords: {keywords}")

    papers = []

    if "local_files" in sources or manifest.get("classified_inputs", {}).get("papers"):
        local_papers = manifest.get("classified_inputs", {}).get("papers", [])
        emit_event("module_log", module=1,
                   message=f"Loading {len(local_papers)} local papers")
        for i, paper_path in enumerate(local_papers):
            papers.append({
                "source_id": f"LOCAL_{i + 1:04d}",
                "title": Path(paper_path).stem,
                "file_path": paper_path,
                "document_type": "pdf",
                "source": "local",
                "confidence": 1.0
            })

    for source in [s for s in sources if s != "local_files"]:
        emit_event("module_log", module=1,
                   message=f"Searching source: {source} (placeholder; implement API call)")

    seen_ids = set()
    deduped = []
    for p in papers:
        dedup_key = (p.get("title", "").lower().strip(), p.get("doi", ""))
        if dedup_key not in seen_ids:
            seen_ids.add(dedup_key)
            deduped.append(p)

    results = {
        "papers": deduped,
        "meta": {
            "total_found": len(papers),
            "after_dedup": len(deduped),
            "sources_searched": sources,
            "search_time": time.time()
        }
    }

    output_path = output_dir / "literature_results.json"
    save_json(results, output_path)

    emit_event("module_complete", module=1,
               papers_found=len(papers), papers_after_dedup=len(deduped))

    return results


def run_module_2_experiment_extraction(manifest: dict, output_dir: Path,
                                        prev_results: dict) -> dict:
    emit_event("module_start", module=2, module_name="experiment_extraction")

    papers = prev_results.get("papers", [])
    extraction_config_path = manifest.get("extraction_config_path")
    if extraction_config_path:
        config = load_json(Path(extraction_config_path))
    else:
        config = load_json(SKILL_DIR / "templates" / "extraction_config_template.json")

    fields = config.get("fields", [])

    emit_event("module_log", module=2,
               message=f"Extracting {len(fields)} fields from {len(papers)} papers")

    experiments = []

    for paper in papers:
        source_id = paper.get("source_id", "UNKNOWN")

        emit_event("module_log", module=2,
                   message=f"Extracting from: {paper.get('title', source_id)}")

        pass

    results = {
        "experiments": experiments,
        "meta": {
            "papers_processed": len(papers),
            "total_experiments_extracted": len(experiments),
            "extraction_config_version": config.get("version", "1.0.0")
        }
    }

    output_path = output_dir / "extraction_results.json"
    save_json(results, output_path)

    emit_event("module_complete", module=2,
               experiments_extracted=len(experiments))

    return results


def run_module_3_data_normalization(manifest: dict, output_dir: dict,
                                     prev_results: dict) -> dict:
    emit_event("module_start", module=3, module_name="data_normalization")

    experiments = prev_results.get("experiments", [])

    synonym_map = load_json(SKILL_DIR / "assets" / "synonym_map.json")
    unit_conversions = load_json(SKILL_DIR / "assets" / "unit_conversions.json")

    emit_event("module_log", module=3,
               message=f"Normalizing {len(experiments)} experiment records")

    normalized = []
    stats = {
        "synonyms_normalized": 0,
        "units_converted": 0,
        "missing_values_flagged": 0,
        "ambiguous_values_flagged": 0
    }

    for exp in experiments:
        norm_exp = dict(exp)
        for field, mappings in synonym_map.get("mappings", {}).get("materials", {}).items():
            pass

        for key, value in exp.items():
            if value is None or value == "" or value == "N/A":
                stats["missing_values_flagged"] += 1

        normalized.append(norm_exp)

    results = {
        "experiments": normalized,
        "meta": stats
    }

    output_path = Path(output_dir) / "normalized_results.json"
    save_json(results, output_path)

    emit_event("module_complete", module=3, **stats)

    return results


def run_module_4_provenance(manifest: dict, output_dir: Path,
                             prev_results: dict) -> dict:
    emit_event("module_start", module=4, module_name="provenance_traceability")

    experiments = prev_results.get("experiments", [])
    provenance_records = []

    for exp in experiments:
        prov = {
            "experiment_id": exp.get("experiment_id", ""),
            "source_id": exp.get("source_id", ""),
            "paper_title": exp.get("paper_title", ""),
            "doi": exp.get("doi", ""),
            "fields": {}
        }

        for field, value in exp.items():
            prov["fields"][field] = {
                "value": value,
                "source_page": exp.get("source_page", ""),
                "source_snippet": exp.get("source_snippet", ""),
                "confidence": exp.get("confidence", 0.5),
                "extraction_method": exp.get("extraction_method", "unknown"),
                "assumptions": exp.get("notes", "")
            }

        provenance_records.append(prov)

    results = {"provenance": provenance_records}
    output_path = output_dir / "provenance_results.json"
    save_json(results, output_path)

    emit_event("module_complete", module=4,
               provenance_records=len(provenance_records))

    return results


def run_module_5_explanation(manifest: dict, output_dir: Path,
                              prev_results: dict) -> dict:
    emit_event("module_start", module=5, module_name="explanation_generation")

    experiments = prev_results.get("experiments", [])

    emit_event("module_log", module=5,
               message=f"Generating explanations for {len(experiments)} experiments")

    explanations = []

    for exp in experiments:
        explanation = {
            "experiment_id": exp.get("experiment_id", ""),
            "what_was_tested": "",
            "parameter_meaning": "",
            "result_interpretation": "",
            "trend_or_pattern": "",
            "hypothesis_support": "",
            "caveats": ""
        }
        explanations.append(explanation)

    report_lines = [
        "# Experiment Data Explanation Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Domain: {manifest.get('domain', 'pva_bopet')}",
        f"Total experiments analyzed: {len(experiments)}",
        "",
        "## Explanations",
        ""
    ]
    for exp in explanations:
        report_lines.append(f"### Experiment: {exp['experiment_id']}")
        report_lines.append(f"- **What was tested**: {exp['what_was_tested']}")
        report_lines.append(f"- **Interpretation**: {exp['result_interpretation']}")
        report_lines.append("")

    results = {"explanations": explanations, "report": "\n".join(report_lines)}
    output_path = output_dir / "explanation_results.json"
    save_json(results, output_path)

    emit_event("module_complete", module=5,
               explanations_generated=len(explanations))

    return results


def run_module_6_ontology(manifest: dict, output_dir: Path,
                           prev_results: dict) -> dict:
    emit_event("module_start", module=6, module_name="ontology_construction")

    experiments = prev_results.get("experiments", [])

    emit_event("module_log", module=6,
               message=f"Building ontology from {len(experiments)} experiments")

    template = load_json(SKILL_DIR / "templates" / "ontology_template.json")

    classes = list(template.get("@graph", []))

    material_set = set()
    additive_set = set()
    property_set = set()

    for exp in experiments:
        mat = exp.get("material_system", "")
        if mat:
            material_set.add(mat)
        add = exp.get("additive", "")
        if add:
            additive_set.add(add)
        prop = exp.get("measured_property", "")
        if prop:
            property_set.add(prop)

    for mat_name in sorted(material_set):
        classes.append({
            "@id": f"pva:Material_{mat_name.replace(' ', '_')}",
            "@type": "pva:Polymer",
            "rdfs:label": mat_name
        })

    for add_name in sorted(additive_set):
        classes.append({
            "@id": f"pva:Additive_{add_name.replace(' ', '_')}",
            "@type": "pva:Additive",
            "rdfs:label": add_name
        })

    for prop_name in sorted(property_set):
        classes.append({
            "@id": f"pva:Property_{prop_name.replace(' ', '_')}",
            "@type": "owl:Class",
            "rdfs:label": prop_name
        })

    results = {
        "ontology": {
            "@context": template.get("@context", {}),
            "@graph": classes
        },
        "meta": {
            "total_classes": len(classes),
            "materials": sorted(material_set),
            "additives": sorted(additive_set),
            "properties": sorted(property_set)
        }
    }

    output_path = output_dir / "ontology_results.json"
    save_json(results, output_path)

    emit_event("module_complete", module=6, **results["meta"])

    return results


def run_module_7_literature_summary(manifest: dict, output_dir: Path,
                                     prev_results: dict) -> dict:
    emit_event("module_start", module=7, module_name="literature_summary")

    papers = prev_results.get("papers", [])
    experiments = prev_results.get("experiments", [])

    years = [p.get("year", 0) for p in papers if p.get("year")]
    year_range = f"{min(years)}-{max(years)}" if years else "unknown"

    report_lines = [
        "# Literature Summary",
        "",
        f"Domain: {manifest.get('domain', 'pva_bopet')}",
        f"Papers analyzed: {len(papers)}",
        f"Experiments extracted: {len(experiments)}",
        f"Year range: {year_range}",
        "",
        "## Main Themes",
        "",
        "## Common Experimental Patterns",
        "",
        "## Performance Trends",
        "",
        "## Frequently Used Materials",
        "",
        "## Unresolved Gaps",
        "",
        "## Promising Directions",
        ""
    ]

    results = {
        "summary": "\n".join(report_lines),
        "meta": {
            "papers_count": len(papers),
            "experiments_count": len(experiments),
            "year_range": year_range
        }
    }

    output_path = output_dir / "literature_summary_results.json"
    save_json(results, output_path)

    with open(output_dir / "literature_summary.md", "w", encoding="utf-8") as f:
        f.write(report_lines)

    emit_event("module_complete", module=7, **results["meta"])

    return results


MODULE_RUNNERS = {
    1: run_module_1_literature_acquisition,
    2: run_module_2_experiment_extraction,
    3: run_module_3_data_normalization,
    4: run_module_4_provenance,
    5: run_module_5_explanation,
    6: run_module_6_ontology,
    7: run_module_7_literature_summary,
}

MODULE_OUTPUT_KEYS = {
    1: "literature",
    2: "extraction",
    3: "normalized",
    4: "provenance",
    5: "explanation",
    6: "ontology",
    7: "summary",
}


def run_full_pipeline(manifest: dict, output_dir: Path):
    emit_event("pipeline_start", mode="full",
               domain=manifest.get("domain", "pva_bopet"))

    all_results = {}
    error_count = 0
    errors = []

    for module_num in range(1, 8):
        try:
            prev_key = MODULE_OUTPUT_KEYS.get(module_num - 1)
            prev = all_results.get(prev_key, {}) if prev_key else {}
            runner = MODULE_RUNNERS[module_num]
            result = runner(manifest, output_dir, prev)
            key = MODULE_OUTPUT_KEYS[module_num]
            all_results[key] = result
        except Exception as e:
            error_count += 1
            errors.append({
                "module": module_num,
                "error_type": type(e).__name__,
                "message": str(e)
            })
            emit_event("module_error", module=module_num,
                       error=str(e), traceback=traceback.format_exc())
            if error_count > 3:
                emit_event("pipeline_abort",
                           reason="Too many module errors; aborting pipeline")
                break

    manifest["statistics"] = {
        "papers_processed": len(all_results.get("literature", {}).get("papers", [])),
        "experiments_extracted": len(all_results.get("extraction", {}).get("experiments", [])),
        "errors": errors
    }

    manifest["output_artifacts"] = [
        str(output_dir / "literature_results.json"),
        str(output_dir / "extraction_results.json"),
        str(output_dir / "normalized_results.json"),
        str(output_dir / "provenance_results.json"),
        str(output_dir / "explanation_results.json"),
        str(output_dir / "ontology_results.json"),
        str(output_dir / "literature_summary_results.json"),
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest["status"] = "completed" if error_count == 0 else "partial_success"
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    save_json(manifest, output_dir / "pipeline_manifest.json")

    emit_event("pipeline_complete", status=manifest["status"],
               errors=error_count)


def main():
    parser = argparse.ArgumentParser(
        description="Domain Literature Experiment Extraction Ontology Pipeline"
    )
    parser.add_argument("--manifest", required=True,
                        help="Path to pipeline manifest JSON")
    parser.add_argument("--output-dir", default="./output",
                        help="Output directory for results")
    parser.add_argument("--module", type=int, choices=range(1, 8),
                        help="Run a single module (1-7) instead of full pipeline")

    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        emit_event("error", message=f"Manifest not found: {args.manifest}")
        sys.exit(1)

    manifest = load_json(manifest_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest["started_at"] = datetime.now(timezone.utc).isoformat()
    manifest["status"] = "running"

    if args.module:
        runner = MODULE_RUNNERS.get(args.module)
        if runner:
            result = runner(manifest, output_dir, {})
            key = MODULE_OUTPUT_KEYS[args.module]
            save_json(result, output_dir / f"module_{args.module}_results.json")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            emit_event("error", message=f"No runner for module {args.module}")
            sys.exit(1)
    else:
        run_full_pipeline(manifest, output_dir)

    emit_event("done")


if __name__ == "__main__":
    main()