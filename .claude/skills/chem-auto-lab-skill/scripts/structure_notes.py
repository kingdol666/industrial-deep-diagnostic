#!/usr/bin/env python3
"""
Experiment Log Structuring Scaffold
====================================
Preprocesses lab notes and provides the structured framework for LLM extraction.

Usage:
  python structure_notes.py --input lab_notes.txt --output structured.json
  python structure_notes.py --input notes.txt --output result.json --context "nanocellulose film"
  echo "Dissolved 5g PVA in water at 90C." | python structure_notes.py --stdin --output result.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ABBREVIATIONS = {
    "DI water": "deionized water",
    "DI H2O": "deionized water",
    "RT": "room temperature (~25°C)",
    "r.t.": "room temperature (~25°C)",
    "o/n": "overnight (~12-16h)",
    "eq.": "equivalent",
    "equiv.": "equivalent",
    "cat.": "catalytic amount",
    "quant.": "quantitative yield",
    "calc.": "calculated",
    "obs.": "observed",
    "NMR": "Nuclear Magnetic Resonance",
    "FTIR": "Fourier Transform Infrared",
    "DSC": "Differential Scanning Calorimetry",
    "TGA": "Thermogravimetric Analysis",
    "XRD": "X-ray Diffraction",
    "SEM": "Scanning Electron Microscopy",
    "TEM": "Transmission Electron Microscopy",
    "UV-Vis": "Ultraviolet-Visible spectroscopy",
    "HPLC": "High Performance Liquid Chromatography",
    "GC": "Gas Chromatography",
    "MS": "Mass Spectrometry",
    "PVA": "Poly(vinyl alcohol)",
    "CNC": "Cellulose Nanocrystals",
    "CNF": "Cellulose Nanofibrils",
    "PEO": "Poly(ethylene oxide)",
    "PEG": "Poly(ethylene glycol)",
    "PLA": "Poly(lactic acid)",
}

UNIT_PATTERNS = [
    (r"(\d+\.?\d*)\s*(°?C|℃)", "temperature"),
    (r"(\d+\.?\d*)\s*(°?F)", "temperature"),
    (r"(\d+\.?\d*)\s*(wt%|wt\.?%|weight%)", "concentration"),
    (r"(\d+\.?\d*)\s*(vol%|vol\.?%|volume%)", "concentration"),
    (r"(\d+\.?\d*)\s*(mol/L|M|mM|μM|µM)", "concentration"),
    (r"(\d+\.?\d*)\s*(ppm|ppb)", "concentration"),
    (r"(\d+\.?\d*)\s*(g|mg|μg|µg|kg)", "mass"),
    (r"(\d+\.?\d*)\s*(mL|ml|L|μL|µL)", "volume"),
    (r"(\d+\.?\d*)\s*(h|hr|hour|hours|min|minute|minutes|s|sec|seconds)", "time"),
    (r"(\d+\.?\d*)\s*(mm|cm|m|μm|µm|nm)", "length"),
    (r"(\d+\.?\d*)\s*(MPa|GPa|bar|psi|kPa|atm)", "pressure"),
    (r"(\d+\.?\d*)\s*(rpm|Hz|kHz)", "frequency"),
    (r"(\d+\.?\d*)\s*(%)", "percentage"),
]

CHEMICAL_PATTERN = re.compile(
    r'\b([A-Z][a-z]?(?:\d+)?(?:[A-Z][a-z]?(?:\d+)?)*)\b'
)


def expand_abbreviations(text):
    result = text
    for abbr, full in sorted(ABBREVIATIONS.items(), key=lambda x: -len(x[0])):
        result = re.sub(r'\b' + re.escape(abbr) + r'\b', full, result, flags=re.IGNORECASE)
    return result


def normalize_units(text):
    text = re.sub(r'(\d+)(°?C|℃)', r'\1 °C', text)
    text = re.sub(r'(\d+)(°?F)', r'\1 °F', text)
    text = re.sub(r'(\d+)(wt%|wt\.?%|weight%)', r'\1 wt%', text)
    text = re.sub(r'(\d+)(mL|ml)', r'\1 mL', text)
    text = re.sub(r'(\d+)([μµ]L)', r'\1 μL', text)
    text = re.sub(r'(\d+)(h|hr)', r'\1 h', text)
    text = re.sub(r'(\d+)(min)(?!\w)', r'\1 min', text)
    return text


def normalize_numbers(text):
    text = re.sub(r'(\d+\.?\d*)\s*±\s*(\d+\.?\d*)', r'\1 ± \2', text)
    text = re.sub(r'(\d+)-(\d+)\s*(°C|℃|°F|wt%|%)', r'\1-\2 \3', text)
    return text


def split_sentences(text):
    sentences = re.split(r'(?<=[.!?。！？])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 3]
    return sentences


def extract_entities(text):
    materials = []
    measurements = []
    for match in re.finditer(CHEMICAL_PATTERN, text):
        token = match.group(1)
        if len(token) > 1 and token not in ("The", "In", "At", "An", "Is", "It", "We", "No", "To", "On", "Of"):
            materials.append(token)

    for pattern, category in UNIT_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            measurements.append({
                "value": float(match.group(1)),
                "unit": match.group(2),
                "category": category,
                "text": match.group(0),
            })

    return list(set(materials)), measurements


def process_notes(file_path, context):
    if file_path:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    else:
        text = ""

    original_text = text

    text = expand_abbreviations(text)
    text = normalize_units(text)
    text = normalize_numbers(text)

    sentences = split_sentences(text)
    materials, measurements = extract_entities(text)

    experiments = []
    for i, sentence in enumerate(sentences):
        _, sent_measurements = extract_entities(sentence)
        experiments.append({
            "experiment_id": f"NOTE-{i + 1:03d}",
            "source_text": sentence,
            "structured": {
                "action": "extraction_pending",
                "materials": [],
                "conditions": [],
                "observations": [],
                "measurements": sent_measurements if sent_measurements else [],
            },
            "confidence_overall": "pending",
            "ambiguities": [],
            "warnings": [],
            "_needs_llm_extraction": True,
        })

    result = {
        "metadata": {
            "script": "structure_notes.py",
            "version": "1.0.0",
            "input_file": str(file_path) if file_path else "stdin",
            "context": context,
            "processing_timestamp": datetime.utcnow().isoformat() + "Z",
            "sentences_processed": len(sentences),
            "abbreviations_expanded": len(ABBREVIATIONS),
            "materials_detected": len(materials),
            "measurements_detected": len(measurements),
            "preprocessing": {
                "abbreviation_expansion": True,
                "unit_normalization": True,
                "number_normalization": True,
            },
        },
        "preprocessing_summary": {
            "original_text_length": len(original_text),
            "sentences_found": len(sentences),
            "materials_detected": materials,
            "measurements_summary": [
                {"category": m["category"], "value": m["value"], "unit": m["unit"]}
                for m in measurements
            ],
        },
        "experiments": experiments,
        "_instructions": "The '_needs_llm_extraction' flag indicates sentences that require LLM processing to extract structured fields. Use the few-shot examples in references/module-3-log-structuring.md to guide extraction.",
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Experiment Log Structuring Scaffold")
    parser.add_argument("--input", help="Input file path (.txt, .md, .log)")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--context", default=None, help="Additional experiment context")

    args = parser.parse_args()

    if args.stdin:
        text = sys.stdin.read()
        import tempfile
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tmp.write(text)
        tmp.close()
        result = process_notes(tmp.name, args.context)
        Path(tmp.name).unlink()
    elif args.input:
        if not Path(args.input).exists():
            print(f"ERROR: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        result = process_notes(args.input, args.context)
    else:
        print("ERROR: --input or --stdin required", file=sys.stderr)
        sys.exit(1)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Preprocessed: {result['metadata']['sentences_processed']} sentences")
    print(f"Materials: {result['preprocessing_summary']['materials_detected']}")
    print(f"Measurements: {len(result['preprocessing_summary']['measurements_summary'])}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()