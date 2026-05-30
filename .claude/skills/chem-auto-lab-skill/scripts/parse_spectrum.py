#!/usr/bin/env python3
"""
Spectroscopy Parser
===================
Parses and analyzes spectroscopy data: FTIR, Raman, UV-Vis, HPLC, NMR.

Usage:
  python parse_spectrum.py --input sample.csv --output result.json
  python parse_spectrum.py --input sample.jdx --output result.json --type ftir
  python parse_spectrum.py --input sample.csv --output result.json --baseline airpls
  cat xy.json | python parse_spectrum.py --stdin --type uvvis --output result.json
"""

import argparse
import json
import sys
import warnings
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
    from scipy import signal as scipy_signal
    from scipy.integrate import trapezoid
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

warnings.filterwarnings("ignore")

SPECTRUM_PROFILES = {
    "ftir": {
        "x_unit": "cm-1", "x_range": (400, 4000),
        "y_label_patterns": ["transmittance", "absorbance", "transmission", "%t", "% transmittance"],
        "height_pct": 5, "prominence_pct": 2, "distance": 20, "width": (5, 50),
    },
    "raman": {
        "x_unit": "cm-1", "x_range": (50, 4000),
        "y_label_patterns": ["intensity", "raman intensity", "counts", "a.u."],
        "height_pct": 3, "prominence_pct": 1, "distance": 10, "width": (3, 30),
    },
    "uvvis": {
        "x_unit": "nm", "x_range": (190, 1100),
        "y_label_patterns": ["absorbance", "abs", "transmittance", "optical density", "od"],
        "height_pct": 1, "prominence_pct": 0.5, "distance": 5, "width": (2, 50),
    },
    "nmr": {
        "x_unit": "ppm", "x_range": (0, 12),
        "y_label_patterns": ["intensity", "signal"],
        "height_pct": None, "prominence_pct": None, "distance": 0.02, "width": (0.01, 0.5),
    },
    "hplc": {
        "x_unit": "min", "x_range": None,
        "y_label_patterns": ["absorbance", "mau", "mv", "response", "intensity"],
        "height_pct": 0.5, "prominence_pct": 0.1, "distance": 0.1, "width": (0.05, 2),
    },
}


def detect_spectrum_type(x_data, y_data, headers):
    x_range = (x_data.min(), x_data.max())
    if 350 <= x_range[0] <= 450 and 3800 <= x_range[1] <= 4200:
        return "ftir"
    if 50 <= x_range[0] <= 200 and 3500 <= x_range[1] <= 4200:
        return "raman"
    if 180 <= x_range[0] <= 220 and 800 <= x_range[1] <= 1150:
        return "uvvis"
    if 0 <= x_range[0] <= 2 and 8 <= x_range[1] <= 15:
        return "nmr"
    if headers:
        header_str = " ".join(headers).lower()
        if "wavenumber" in header_str or "cm-1" in header_str or "cm⁻¹" in header_str:
            return "ftir"
        if "raman shift" in header_str:
            return "raman"
        if "wavelength" in header_str and ("nm" in header_str or "absorb" in header_str):
            return "uvvis"
        if "chemical shift" in header_str or "ppm" in header_str:
            return "nmr"
        if "retention" in header_str and "time" in header_str:
            return "hplc"
    return "ftir"


def parse_jcamp_dx(file_path):
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    x_unit = "a.u."
    y_unit = "a.u."
    for line in content.split("\n"):
        if line.startswith("##XUNITS="):
            x_unit = line.split("=", 1)[1].strip()
        if line.startswith("##YUNITS="):
            y_unit = line.split("=", 1)[1].strip()

    data_start = content.find("##XYDATA=")
    if data_start == -1:
        raise ValueError("No ##XYDATA= found in JCAMP-DX file")

    data_section = content[data_start:]
    lines = data_section.split("\n")[1:]
    x_values, y_values = [], []
    current_x = None

    for line in lines:
        line = line.strip()
        if not line or line.startswith("##") or line.startswith("$$"):
            break
        tokens = line.replace(",", " ").split()
        if not tokens:
            continue
        try:
            first_val = float(tokens[0])
            if len(tokens) == 1:
                current_x = first_val
            else:
                current_x = first_val
                for t in tokens[1:]:
                    x_values.append(current_x)
                    y_values.append(float(t))
        except ValueError:
            continue

    return np.array(x_values), np.array(y_values), x_unit, y_unit


def parse_xy_file(file_path):
    try:
        data = np.loadtxt(file_path, delimiter=None)
    except Exception:
        import csv
        with open(file_path, "r") as f:
            reader = csv.reader(f)
            rows = []
            for row in reader:
                try:
                    rows.append([float(x) for x in row])
                except ValueError:
                    pass
            data = np.array(rows)

    if data.ndim != 2 or data.shape[1] < 2:
        raise ValueError(f"Expected 2D data with at least 2 columns, got shape {data.shape}")

    x_data = data[:, 0]
    y_data = data[:, 1]
    return x_data, y_data, "a.u.", "a.u."


def baseline_correction_airpls(y, lam=1e5, p=0.05, n_iter=20):
    L = len(y)
    D = np.diff(np.eye(L), 2)
    H = lam * D.T @ D
    w = np.ones(L)
    for _ in range(n_iter):
        W = np.diag(w)
        z = np.linalg.solve(W + H, w * y)
        w_new = p * (y > z) + (1 - p) * (y < z)
        if np.allclose(w, w_new):
            break
        w = w_new
    return z


def baseline_correction_polynomial(y, x, degree=3):
    coeffs = np.polyfit(x, y, degree)
    baseline = np.polyval(coeffs, x)
    return baseline


def smooth_savitzky_golay(y, window=11, order=3):
    if not HAS_SCIPY:
        return y
    if window > len(y):
        window = len(y) - (1 if len(y) % 2 == 0 else 0)
    if window % 2 == 0:
        window -= 1
    if window < order + 2:
        return y
    return scipy_signal.savgol_filter(y, window, order)


def detect_peaks(y, height_threshold, prominence_threshold, distance, width_range):
    if not HAS_SCIPY:
        return np.array([]), {}
    height = None
    if height_threshold is not None:
        height = max(y) * height_threshold / 100
    prominence = None
    if prominence_threshold is not None:
        prominence = (max(y) - min(y)) * prominence_threshold / 100

    peaks, properties = scipy_signal.find_peaks(
        y, height=height, prominence=prominence,
        distance=distance, width=width_range,
    )
    return peaks, properties


def find_functional_groups(position, tolerance=10):
    groups_db = [
        {"group": "O-H (alcohol/phenol)", "range": [3200, 3600], "intensity": "strong_broad", "notes": "Broad peak; hydrogen-bonded"},
        {"group": "O-H (carboxylic acid)", "range": [2500, 3300], "intensity": "strong_very_broad", "notes": "Very broad; overlaps C-H"},
        {"group": "N-H (amine/amide)", "range": [3300, 3500], "intensity": "medium", "notes": "Primary amines: two peaks"},
        {"group": "C-H (alkane)", "range": [2850, 2960], "intensity": "medium_strong", "notes": ""},
        {"group": "C-H (alkene/aromatic)", "range": [3000, 3100], "intensity": "weak_medium", "notes": "Above 3000"},
        {"group": "C≡C (alkyne)", "range": [2100, 2260], "intensity": "variable", "notes": "Weak for internal alkynes"},
        {"group": "C≡N (nitrile)", "range": [2210, 2260], "intensity": "medium_strong", "notes": ""},
        {"group": "C=O (carbonyl)", "range": [1680, 1780], "intensity": "strong", "notes": "Exact position depends on type"},
        {"group": "C=C (alkene)", "range": [1620, 1680], "intensity": "variable", "notes": "Weaker than C=O"},
        {"group": "N-H bend (amine)", "range": [1550, 1650], "intensity": "medium_strong", "notes": ""},
        {"group": "C-H bend (alkane)", "range": [1350, 1480], "intensity": "medium", "notes": ""},
        {"group": "C-O (alcohol/ether/ester)", "range": [1000, 1300], "intensity": "strong", "notes": "Ester: two bands (C-O-C)"},
        {"group": "C-X (halide)", "range": [500, 800], "intensity": "strong", "notes": "C-Cl: 550-850; C-Br: 500-690"},
        {"group": "Aromatic C-H (out-of-plane)", "range": [675, 900], "intensity": "strong", "notes": "Substitution pattern determination"},
    ]
    matches = []
    for g in groups_db:
        low, high = g["range"]
        if low - tolerance <= position <= high + tolerance:
            match_quality = "strong" if low <= position <= high else "tentative"
            matches.append({
                "group": g["group"],
                "match_quality": match_quality,
                "reference_range": g["range"],
                "notes": g["notes"],
            })
    return matches


def process_spectrum(file_path, args):
    suffix = Path(file_path).suffix.lower()
    if suffix == ".jdx":
        x_data, y_data, x_unit, y_unit = parse_jcamp_dx(file_path)
    else:
        x_data, y_data, x_unit, y_unit = parse_xy_file(file_path)

    x_data = np.asarray(x_data, dtype=float)
    y_data = np.asarray(y_data, dtype=float)

    if args.type == "auto":
        spectrum_type = detect_spectrum_type(x_data, y_data, [x_unit, y_unit])
    else:
        spectrum_type = args.type

    profile = SPECTRUM_PROFILES.get(spectrum_type, SPECTRUM_PROFILES["ftir"])
    x_unit = profile["x_unit"] if profile["x_unit"] != "a.u." else x_unit

    processing_steps = {}

    y_corrected = y_data.copy()
    if args.baseline != "none" and HAS_SCIPY:
        if args.baseline == "airpls":
            baseline = baseline_correction_airpls(y_data)
        elif args.baseline == "polynomial":
            baseline = baseline_correction_polynomial(y_data, x_data)
        elif args.baseline == "als":
            baseline = baseline_correction_airpls(y_data, lam=1e4, p=0.01)
        else:
            baseline = np.zeros_like(y_data)
        if args.baseline != "none":
            y_corrected = y_data - baseline
            processing_steps["baseline_correction"] = args.baseline

    y_smooth = y_corrected.copy()
    if args.smooth != "none" and HAS_SCIPY:
        if args.smooth == "savitzky_golay":
            y_smooth = smooth_savitzky_golay(y_corrected)
        elif args.smooth == "moving_average":
            window = 11
            kernel = np.ones(window) / window
            y_smooth = np.convolve(y_corrected, kernel, mode="same")
        processing_steps["smoothing"] = args.smooth

    snr = 10 * np.log10(np.var(y_smooth) / max(np.var(y_data - y_smooth), 1e-10)) if len(y_smooth) > 0 else 0

    peaks_list = []
    if HAS_SCIPY:
        height_th = args.height if args.height is not None else profile["height_pct"]
        prom_th = args.prominence if args.prominence is not None else profile["prominence_pct"]
        dist = args.distance if args.distance is not None else profile["distance"]
        width_r = profile["width"]
        if isinstance(width_r, (list, tuple)):
            width_r = tuple(width_r)

        peaks, properties = detect_peaks(y_smooth, height_th, prom_th, dist, width_r)

        for i, p in enumerate(peaks):
            peak_info = {
                "peak_id": i + 1,
                "position": round(float(x_data[p]), 2),
                "position_unit": x_unit,
                "height": round(float(y_smooth[p]), 4),
                "prominence": round(float(properties.get("prominences", [0])[i] if i < len(properties.get("prominences", [])) else 0), 4),
            }

            if "widths" in properties and i < len(properties["widths"]):
                peak_info["fwhm"] = round(float(properties["widths"][i]), 2)

            if "left_ips" in properties and "right_ips" in properties:
                li = int(properties["left_ips"][i])
                ri = int(properties["right_ips"][i])
                if ri > li:
                    area = trapezoid(y_smooth[li:ri], x_data[li:ri])
                    peak_info["area"] = round(float(area), 4)

            if spectrum_type in ("ftir", "raman"):
                peak_info["functional_group_matches"] = find_functional_groups(peak_info["position"])

            peaks_list.append(peak_info)

    overall = ""
    if spectrum_type == "ftir":
        carbonyl_peaks = [p for p in peaks_list if p.get("functional_group_matches") and any("C=O" in m["group"] for m in p["functional_group_matches"])]
        oh_peaks = [p for p in peaks_list if p.get("functional_group_matches") and any("O-H" in m["group"] for m in p["functional_group_matches"])]
        if carbonyl_peaks:
            overall = f"Spectrum shows C=O absorption at {carbonyl_peaks[0]['position']} cm⁻¹ suggesting carbonyl-containing compound."
            if oh_peaks:
                overall += f" O-H absorption at {oh_peaks[0]['position']} cm⁻¹. "
        else:
            overall = "No strong C=O detected. Likely non-carbonyl compound."

    result = {
        "metadata": {
            "script": "parse_spectrum.py",
            "version": "1.0.0",
            "input_file": str(file_path),
            "spectrum_type": spectrum_type,
            "processing_timestamp": datetime.utcnow().isoformat() + "Z",
            "x_unit": x_unit,
            "y_unit": y_unit,
            "n_points": len(x_data),
            "processing": processing_steps,
            "snr_estimated": round(snr, 1),
        },
        "peaks": peaks_list,
        "regions_of_interest": [
            {"region": "functional_group" if spectrum_type == "ftir" else "full_spectrum",
             "range": [float(x_data.min()), float(x_data.max())],
             "description": "Full spectral range",
             "key_peaks": [p["peak_id"] for p in peaks_list[:5]]},
        ],
        "overall_assessment": overall,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Spectroscopy Parser")
    parser.add_argument("--input", help="Input file path (.csv, .txt, .jdx, .spc)")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin (JSON)")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--type", default="auto", choices=["auto", "ftir", "raman", "uvvis", "nmr", "hplc"], help="Spectrum type")
    parser.add_argument("--baseline", default="airpls", choices=["airpls", "polynomial", "als", "none"], help="Baseline correction method")
    parser.add_argument("--smooth", default="savitzky_golay", choices=["savitzky_golay", "moving_average", "none"], help="Smoothing method")
    parser.add_argument("--height", type=float, default=None, help="Peak height threshold (percent of max)")
    parser.add_argument("--prominence", type=float, default=None, help="Peak prominence threshold (percent of range)")
    parser.add_argument("--distance", type=float, default=None, help="Minimum distance between peaks")

    args = parser.parse_args()

    if args.stdin:
        raw = json.load(sys.stdin)
        result = raw
    else:
        if not args.input:
            print("ERROR: --input or --stdin required", file=sys.stderr)
            sys.exit(1)
        if not Path(args.input).exists():
            print(f"ERROR: File not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        result = process_spectrum(args.input, args)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Parsed {result['metadata']['spectrum_type']} spectrum: {result['metadata']['n_points']} points, {len(result['peaks'])} peaks")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()