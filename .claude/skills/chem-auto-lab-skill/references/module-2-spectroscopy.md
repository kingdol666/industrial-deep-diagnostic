# Module 2: Spectroscopy Parser

You parse and analyze spectroscopy data from common chemistry instrument formats.

## Core Principle

Spectroscopy is physics, not pattern matching. Every peak interpretation must be grounded in: (1) spectral region physics (e.g., IR fingerprint vs. functional group region), (2) reference correlation tables, and (3) signal quality assessment. Never report a functional group match without stating confidence.

## Supported Spectroscopy Types

| Type | X-Axis Unit | Typical Range | Y-Axis | Key Features |
|------|------------|---------------|--------|-------------|
| **FTIR** | Wavenumber (cm⁻¹) | 4000–400 | Transmittance (%) / Absorbance | Functional group region (4000–1500) + Fingerprint (1500–400) |
| **Raman** | Raman shift (cm⁻¹) | 4000–50 | Intensity (a.u.) | Complementary to IR; symmetric vibrations active |
| **UV-Vis** | Wavelength (nm) | 190–1100 | Absorbance (a.u.) | λmax, band gap estimation, concentration (Beer-Lambert) |
| **NMR** | Chemical shift (ppm) | 0–12 (¹H) / 0–220 (¹³C) | Intensity | Peak position, integration, multiplicity (splitting) |
| **HPLC** | Retention time (min) | Variable | Absorbance / mV | Peak area, resolution, theoretical plates |

## Input Format Auto-Detection

1. Check file extension: `.jdx` → JCAMP-DX, `.spc` → SPC (limited)
2. For `.csv`/`.txt`: read first 20 lines, look for:
   - Two numeric columns → XY data
   - Header patterns: `wavenumber`, `wavelength`, `ppm`, `chemical shift`, `absorbance`, `transmittance`, `intensity`
   - Numeric range: 4000–400 → likely FTIR, 200–800 → likely UV-Vis, 0–12 → likely NMR
3. JCAMP-DX: Parse `##TITLE=`, `##XUNITS=`, `##YUNITS=`, `##NPOINTS=`, `##XYDATA=`

## Processing Pipeline

### Step 1: Data Loading & Validation

```
Load raw data → Detect format → Validate axis ranges → Normalize units
```

### Step 2: Baseline Correction

**Methods** (controlled by `--baseline`):
- `airpls` — Asymmetric Reweighted Penalized Least Squares. Best for IR/Raman with broad backgrounds.
- `polynomial` — Polynomial baseline fitting. Good for smooth baselines.
- `als` — Asymmetric Least Squares. λ (smoothness) and p (asymmetry) tunable.
- `none` — Skip baseline correction.

**Default**: `airpls` for IR/Raman, `none` for NMR (phase correction is separate), `polynomial` for UV-Vis.

### Step 3: Smoothing

**Methods** (controlled by `--smooth`):
- `savitzky_golay` — Savitzky-Golay filter. Preserves peak shapes. Window and order tunable.
- `moving_average` — Simple moving average. Fast but broadens peaks.
- `none` — Skip smoothing.

**Default**: `savitzky_golay` with window=11, order=3 for high-SNR data; window=21 for noisy data.

### Step 4: Peak Detection

Uses `scipy.signal.find_peaks` with auto-tuned parameters based on spectrum type:

| Type | Height Threshold | Prominence | Distance | Width |
|------|-----------------|------------|----------|-------|
| FTIR | 5% of max absorbance | 2% of range | 20 cm⁻¹ | [5, 50] cm⁻¹ |
| Raman | 3% of max intensity | 1% of range | 10 cm⁻¹ | [3, 30] cm⁻¹ |
| UV-Vis | 1% of max absorbance | 0.5% of range | 5 nm | [2, 50] nm |
| NMR | Auto (baseline noise × 3) | Noise × 2 | 0.02 ppm | [0.01, 0.5] ppm |
| HPLC | 0.5% of max | 0.1% of max | 0.1 min | [0.05, 2] min |

Override any with `--height`, `--prominence`, `--distance`, `--width`.

### Step 5: Peak Area Integration

For each detected peak:
1. Find peak boundaries (valley-to-valley or at baseline)
2. Trapezoidal integration of the signal between boundaries
3. Report: area, height, FWHM (full width at half maximum), asymmetry factor

### Step 6: Peak Matching (FTIR/Raman only)

Match detected peak positions against `assets/functional_groups.json`:

```json
{
  "functional_group": "C=O (carbonyl)",
  "characteristic_range": [1680, 1780],
  "typical_intensity": "strong",
  "notes": "Amides shift lower (1640–1690), esters higher (1735–1750)"
}
```

**Matching rules**:
- Peak position within ±tolerance of reference range (default ±10 cm⁻¹ for IR)
- Strong matches: peak within range AND intensity matches literature
- Tentative matches: peak within range but intensity differs
- No match: no reference peak within tolerance

**Critical**: FTIR functional group interpretation should ALWAYS cross-validate:
- A single C=O peak at ~1700 could be ketone, aldehyde, carboxylic acid, ester, amide
- Look for corroborating peaks: O–H (~3400 broad) → acid; C–O (~1200) → ester; N–H (~3300) → amide

### Step 7: Output Generation

Validate output against `schemas/spectroscopy_output.schema.json`.

## Script Usage

```bash
# Auto-detect type
python scripts/parse_spectrum.py --input sample.csv --output result.json

# Specify type explicitly
python scripts/parse_spectrum.py --input sample.csv --output result.json --type ftir

# With processing options
python scripts/parse_spectrum.py \
  --input sample.jdx \
  --output result.json \
  --type raman \
  --baseline airpls \
  --smooth savitzky_golay \
  --height 0.05 --prominence 0.02

# Stdin mode
cat xy_data.json | python scripts/parse_spectrum.py --stdin --type uvvis --output result.json
```

## Output Format

```json
{
  "metadata": {
    "script": "parse_spectrum.py",
    "version": "1.0.0",
    "input_file": "sample.csv",
    "spectrum_type": "ftir",
    "processing_timestamp": "2026-05-24T10:00:00Z",
    "x_unit": "cm-1",
    "y_unit": "transmittance_%",
    "n_points": 3600,
    "processing": {
      "baseline_correction": "airpls",
      "smoothing": "savitzky_golay_w11_o3",
      "snr_estimated": 45.2
    }
  },
  "peaks": [
    {
      "peak_id": 1,
      "position": 1723.5,
      "position_unit": "cm-1",
      "height": 0.75,
      "area": 12.34,
      "fwhm": 18.2,
      "asymmetry": 1.05,
      "prominence": 0.42,
      "functional_group_matches": [
        {
          "group": "C=O (carbonyl)",
          "match_quality": "strong",
          "reference_range": [1680, 1780],
          "notes": "Position suggests ester or ketone; check for C-O band"
        }
      ]
    }
  ],
  "regions_of_interest": [
    {
      "region": "functional_group",
      "range": [4000, 1500],
      "description": "Characteristic functional group absorptions",
      "key_peaks": [1, 2, 3]
    },
    {
      "region": "fingerprint",
      "range": [1500, 400],
      "description": "Unique molecular fingerprint region"
    }
  ],
  "overall_assessment": "Spectrum shows strong C=O absorption at 1723 cm⁻¹ suggesting carbonyl-containing compound. Broad O-H absorption at ~3400 cm⁻¹ indicates possible carboxylic acid or alcohol. Recommend confirming with NMR or chemical tests."
}
```

## Edge Cases

1. **Saturated detector** — Signal flat at max (e.g., transmittance = 100% for wide range). Flag as `detector_saturated`, affected range.
2. **Noisy baseline** — SNR < 10. Use aggressive smoothing. Flag `low_snr` in output.
3. **JCAMP-DX with multiple blocks** — Some files have `##XYDATA=(X++(Y..Y))` packed format. Unpack correctly.
4. **NMR phase distortion** — Phase correction is NOT implemented in this module. Flag if baseline is asymmetric.
5. **Very large files** — >100k data points. Downsample for peak detection, keep full resolution for output.