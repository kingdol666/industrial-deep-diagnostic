#!/usr/bin/env python3
"""
Chem-Auto-Lab Full Pipeline Orchestrator
=========================================
Scans input directory and executes the complete processing pipeline.

Usage:
  python run_pipeline.py --input-dir ./raw_data/ --output-dir ./results/ --mode full
  python run_pipeline.py --input-dir ./data/ --output-dir ./out/ --mode clean-and-report
  python run_pipeline.py --input-dir ./data/ --output-dir ./out/ --mode analyze
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.resolve()

SUPPORTED_EXTENSIONS = {
    "spreadsheet": {".xlsx", ".xls", ".csv", ".tsv"},
    "lab_notes": {".txt", ".md", ".log"},
    "spectrum": {".jdx", ".spc"},
}

SPECTRAL_X_PATTERNS = [
    "wavenumber", "wavelength", "chemical shift", "retention time",
    "cm-1", "cm⁻¹", "ppm", "absorbance", "transmittance", "intensity",
]


def scan_directory(input_dir):
    files = {
        "spreadsheets": [],
        "lab_notes": [],
        "spectra": [],
        "unrecognized": [],
    }

    for file_path in Path(input_dir).iterdir():
        if not file_path.is_file() or file_path.name.startswith("."):
            continue
        suffix = file_path.suffix.lower()
        if suffix in SUPPORTED_EXTENSIONS["spreadsheet"]:
            files["spreadsheets"].append(str(file_path))
        elif suffix in SUPPORTED_EXTENSIONS["lab_notes"]:
            files["lab_notes"].append(str(file_path))
        elif suffix in SUPPORTED_EXTENSIONS["spectrum"]:
            files["spectra"].append(str(file_path))
        elif suffix == ".csv" or suffix == ".txt":
            try:
                with open(file_path, "r") as f:
                    first_line = f.readline().lower()
                if any(p in first_line for p in SPECTRAL_X_PATTERNS):
                    files["spectra"].append(str(file_path))
                else:
                    files["spreadsheets"].append(str(file_path))
            except Exception:
                files["unrecognized"].append(str(file_path))
        else:
            files["unrecognized"].append(str(file_path))

    return files


def run_module(script_name, args_list, step_name):
    script_path = SCRIPT_DIR / script_name
    cmd = [sys.executable, str(script_path)] + args_list
    print(f"  [{step_name}] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [{step_name}] ERROR: {result.stderr.strip()}")
        return False, result.stderr.strip()
    print(f"  [{step_name}] OK: {result.stdout.strip()}")
    return True, result.stdout.strip()


def run_pipeline(input_dir, output_dir, mode, skill_path=None):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    events_log = output_dir / ".pipeline_events.jsonl"

    def log_event(event_type, **kwargs):
        entry = {"event": event_type, "timestamp": datetime.utcnow().isoformat() + "Z", **kwargs}
        with open(events_log, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    log_event("pipeline_start", mode=mode)

    classified = scan_directory(input_dir)

    manifest = {
        "pipeline_id": f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        "mode": mode,
        "classified_files": {k: [Path(f).name for f in v] for k, v in classified.items()},
        "status": "initialized",
    }

    total = sum(len(v) for k, v in classified.items() if k != "unrecognized")
    if total == 0:
        print("ERROR: No supported files found in input directory.")
        print(f"Supported: {SUPPORTED_EXTENSIONS}")
        sys.exit(1)

    print(f"Found: {len(classified['spreadsheets'])} spreadsheets, "
          f"{len(classified['spectra'])} spectra, {len(classified['lab_notes'])} notes "
          f"({len(classified['unrecognized'])} unrecognized)")

    errors = []
    modules_run = []

    cleaned_dir = output_dir / "01_cleaned"
    spectra_dir = output_dir / "02_spectra"
    notes_dir = output_dir / "03_structured"
    figures_dir = output_dir / "figures"

    # Step 1: Data Cleaning
    if mode in ("full", "clean-and-report", "analyze"):
        if classified["spreadsheets"]:
            print("\n=== Step 1: Data Cleaning ===")
            cleaned_dir.mkdir(parents=True, exist_ok=True)
            cleaned_files = []
            for sp in classified["spreadsheets"]:
                name = Path(sp).stem
                out_file = cleaned_dir / f"{name}.json"
                ok, msg = run_module("clean_data.py", ["--input", sp, "--output", str(out_file)], "M1-Clean")
                log_event("step_complete" if ok else "step_error", module=1, file=Path(sp).name, error=msg if not ok else None)
                if ok:
                    cleaned_files.append(str(out_file))
                    modules_run.append(1)
                else:
                    errors.append(f"Module 1: {Path(sp).name}: {msg}")
            # Merge
            if cleaned_files:
                merged = []
                for cf in cleaned_files:
                    with open(cf) as f:
                        d = json.load(f)
                        merged.extend(d.get("experiments", []))
                merged_path = cleaned_dir / "merged_experiments.json"
                with open(merged_path, "w") as f:
                    json.dump({"metadata": {"merged_from": [Path(c).name for c in cleaned_files]}, "experiments": merged}, f, ensure_ascii=False, indent=2)
                print(f"  Merged {len(merged)} experiments → {merged_path}")
        else:
            print("\n=== Step 1: Data Cleaning (SKIPPED — no spreadsheets) ===")

    # Step 2: Spectroscopy Parsing
    if mode in ("full", "analyze"):
        if classified["spectra"]:
            print("\n=== Step 2: Spectroscopy Parsing ===")
            spectra_dir.mkdir(parents=True, exist_ok=True)
            for sp in classified["spectra"]:
                name = Path(sp).stem
                out_file = spectra_dir / f"{name}.json"
                ok, msg = run_module("parse_spectrum.py", ["--input", sp, "--output", str(out_file)], "M2-Spectroscopy")
                log_event("step_complete" if ok else "step_error", module=2, file=Path(sp).name, error=msg if not ok else None)
                if ok:
                    modules_run.append(2)
                else:
                    errors.append(f"Module 2: {Path(sp).name}: {msg}")
        else:
            print("\n=== Step 2: Spectroscopy (SKIPPED — no spectra) ===")

    # Step 3: Lab Notes Structuring
    if mode == "full":
        if classified["lab_notes"]:
            print("\n=== Step 3: Lab Notes Structuring ===")
            notes_dir.mkdir(parents=True, exist_ok=True)
            for nt in classified["lab_notes"]:
                name = Path(nt).stem
                out_file = notes_dir / f"{name}.json"
                ok, msg = run_module("structure_notes.py", ["--input", nt, "--output", str(out_file)], "M3-Notes")
                log_event("step_complete" if ok else "step_error", module=3, file=Path(nt).name, error=msg if not ok else None)
                if ok:
                    modules_run.append(3)
                else:
                    errors.append(f"Module 3: {Path(nt).name}: {msg}")
        else:
            print("\n=== Step 3: Lab Notes (SKIPPED — no notes) ===")

    # Step 4: Report Generation
    if mode in ("full", "clean-and-report", "analyze"):
        print("\n=== Step 4: Report Generation ===")
        merged_path = cleaned_dir / "merged_experiments.json"
        if merged_path.exists():
            figures_dir.mkdir(parents=True, exist_ok=True)
            ok_v, _ = run_module("visualize.py", ["--data", str(merged_path), "--output-dir", str(figures_dir)], "M4-Visualize")
            log_event("step_complete" if ok_v else "step_error", module="4a", error=None if ok_v else "visualization failed")

            report_path = output_dir / "report.md"
            extra_args = []
            if spectra_dir.exists():
                extra_args.extend(["--spectra", str(spectra_dir)])
            notes_merged = notes_dir / "merged_notes.json"
            if notes_merged.exists():
                extra_args.extend(["--notes", str(notes_merged)])
            if figures_dir.exists():
                extra_args.extend(["--figures-dir", str(figures_dir)])

            ok_r, msg = run_module("generate_report.py",
                ["--data", str(merged_path), "--output", str(report_path)] + extra_args, "M4-Report")
            log_event("step_complete" if ok_r else "step_error", module=4, error=msg if not ok_r else None)
            if ok_r:
                modules_run.append(4)
            else:
                errors.append(f"Module 4: {msg}")
        else:
            print("  WARNING: No merged_experiments.json found. Skipping report generation.")

    # Step 5: Recommendations
    if mode == "full":
        print("\n=== Step 5: Experiment Recommendations ===")
        merged_path = cleaned_dir / "merged_experiments.json"
        if merged_path.exists():
            rec_path = output_dir / "recommendations.json"
            ok_r, msg = run_module("recommend.py",
                ["--experiments", str(merged_path), "--output", str(rec_path), "--n-recommendations", "3"], "M5-Recommend")
            log_event("step_complete" if ok_r else "step_error", module=5, error=msg if not ok_r else None)
            if ok_r:
                modules_run.append(5)
            else:
                errors.append(f"Module 5: {msg}")
        else:
            print("  WARNING: No data for recommendations.")

    # Finalize
    manifest["status"] = "completed" if not errors else "partial_success"
    manifest["modules_executed"] = sorted(set(modules_run))
    manifest["errors"] = errors
    manifest_path = output_dir / "pipeline_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    log_event("pipeline_complete", status=manifest["status"], errors=len(errors))

    print(f"\n{'='*50}")
    print(f"Pipeline complete: {manifest['status']}")
    print(f"Modules executed: {manifest['modules_executed']}")
    if errors:
        print(f"Errors ({len(errors)}):")
        for e in errors:
            print(f"  - {e}")
    print(f"Output: {output_dir}")
    print(f"Manifest: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="Chem-Auto-Lab Full Pipeline Orchestrator")
    parser.add_argument("--input-dir", required=True, help="Input directory with raw lab data files")
    parser.add_argument("--output-dir", required=True, help="Output directory for results")
    parser.add_argument("--mode", default="full", choices=["full", "clean-and-report", "analyze", "recommend-only"], help="Pipeline mode")
    parser.add_argument("--skill-path", default=None, help="Path to skill directory (for reference files)")

    args = parser.parse_args()

    if not Path(args.input_dir).is_dir():
        print(f"ERROR: Input directory not found: {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    run_pipeline(args.input_dir, args.output_dir, args.mode, args.skill_path)


if __name__ == "__main__":
    main()