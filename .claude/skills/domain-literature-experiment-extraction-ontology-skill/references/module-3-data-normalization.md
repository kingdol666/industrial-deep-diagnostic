# Module 3: Data Normalization

> **Load this file when Module 3 is invoked.**
> Purpose: Normalize extracted data to canonical units, names, and formats. Every transformation is logged and reversible.

## Normalization Pipeline

```
Raw extracted data
    │
    ├──► Unit normalization (temperature, concentration, thickness, pressure, mechanical, barrier)
    ├──► Name normalization (materials, additives, solvents, instruments)
    ├──► Value normalization (ranges → midpoint, approximate → exact)
    └──► Format normalization (ISO dates, consistent numeric precision)
            │
            ▼
    Normalized data (experiments_normalized.json)
```

## Unit Normalization

### Temperature

| Input Unit | Canonical Unit | Conversion |
|------------|---------------|------------|
| °C | °C | Keep as-is (domain standard) |
| K | °C | T(°C) = T(K) - 273.15 |
| °F | °C | T(°C) = (T(°F) - 32) × 5/9 |

### Concentration

| Input Format | Canonical Format | Conversion |
|-------------|-----------------|------------|
| wt%, wt.%, w/w%, % (m/m) | wt% | Keep value, standardize label |
| vol%, v/v% | vol% | Keep value, standardize label |
| mol%, mole% | mol% | Keep value, standardize label |
| phr (parts per hundred resin) | phr | Keep as phr (domain convention); also compute wt% equivalent if possible |
| mg/mL, g/L, g/dL | g/mL | Convert: 1 mg/mL = 0.001 g/mL |
| mol/L, M | mol/L | Keep as-is |

### Film Thickness

| Input Unit | Canonical Unit | Conversion |
|------------|---------------|------------|
| μm, um, micron, µm | μm | Keep as-is (domain standard) |
| mm | μm | × 1000 |
| nm | μm | ÷ 1000 |
| mil | μm | × 25.4 |
| Å, Angstrom | μm | ÷ 10000 |

### Pressure

| Input Unit | Canonical Unit | Conversion |
|------------|---------------|------------|
| Pa, kPa, MPa | kPa | Convert to kPa |
| bar, mbar | kPa | 1 bar = 100 kPa |
| atm | kPa | 1 atm = 101.325 kPa |
| psi | kPa | 1 psi = 6.89476 kPa |
| mmHg, Torr | kPa | 1 mmHg = 0.133322 kPa |

### Mechanical Properties

| Input Unit | Canonical Unit | Conversion |
|------------|---------------|------------|
| MPa (strength, modulus) | MPa | Keep as-is |
| GPa (modulus) | GPa | Keep as-is |
| kgf/cm², kgf/mm² | MPa | 1 kgf/cm² = 0.0980665 MPa |
| psi | MPa | 1 psi = 0.00689476 MPa |
| N/mm² | MPa | Keep (1 N/mm² = 1 MPa) |

### Barrier Properties

| Input Unit | Canonical Unit | Conversion |
|------------|---------------|------------|
| WVTR: g/(m²·day), g/m²/day, g/m²·d | g/(m²·day) | Standardize notation |
| WVTR: g/(m²·24h) | g/(m²·day) | Equivalent |
| WVTR: g/(100in²·day) | g/(m²·day) | × 0.155 |
| OTR: cc/(m²·day·atm), cm³/(m²·day·atm) | cc/(m²·day·atm) | Standardize notation |
| OTR: cc/(m²·day·bar) | cc/(m²·day·atm) | × 1.01325 |
| OTR: mL/(m²·day) | cc/(m²·day·atm) | Flag: pressure condition may differ |

### Optical Properties

| Input Format | Canonical Format | Handling |
|-------------|-----------------|----------|
| Transmittance: %, percent | % | Keep as-is |
| Haze: %, percent | % | Keep as-is |
| Absorbance: a.u., AU, abs | a.u. | Keep as-is; do not convert to transmittance |
| Wavelength: nm | nm | Keep as-is |

### Handling Unconvertible Units

When a unit cannot be converted:

```json
{
  "field": "pressure",
  "value_original": 3,
  "unit_original": "bar_g",
  "value_normalized": 3,
  "unit_normalized": "bar_g",
  "conversion_status": "unconvertible",
  "reason": "Gauge pressure (bar_g) cannot be automatically converted to absolute pressure (kPa) without knowing atmospheric pressure offset"
}
```

Never fabricate a conversion. Log all unconvertible units in `normalization_log.json`.

## Name Normalization

### Material Name Canonicalization

Load `assets/pva_bopet_vocabulary.json` for the complete synonym map. Key examples:

| Original | Canonical |
|----------|-----------|
| PVA, PVA-1799, PVA1799, poly(vinyl alcohol) 1799 | PVA 1799 |
| PVA-1788, PVA1788 | PVA 1788 |
| PVA-0588, PVA0588 | PVA 0588 |
| PET, poly(ethylene terephthalate) | PET |
| TAC, triacetyl cellulose, cellulose triacetate | TAC |
| PMMA, poly(methyl methacrylate), acrylic | PMMA |
| COP, cyclo-olefin polymer | COP |
| PC, polycarbonate | PC |

### Additive Name Canonicalization

| Original | Canonical |
|----------|-----------|
| CNC, cellulose nanocrystal, nanocrystalline cellulose, NCC | CNC |
| CNF, cellulose nanofiber, nanofibrillated cellulose, NFC, MFC | CNF |
| GO, graphene oxide | GO |
| rGO, reduced graphene oxide | rGO |
| MMT, montmorillonite, nanoclay | MMT |
| CNT, carbon nanotube, MWCNT (multi-wall), SWCNT (single-wall) | CNT (preserve subtype in `additive_subtype`) |
| SiO₂, silica, silicon dioxide, nanosilica | SiO₂ |
| TiO₂, titania, titanium dioxide | TiO₂ |
| ZnO, zinc oxide | ZnO |
| AgNP, silver nanoparticle, Ag nanoparticle, nano-silver | AgNP |
| glycerol, glycerin, glycerine, 丙三醇 | glycerol |
| EG, ethylene glycol, 乙二醇 | EG |
| PEG, polyethylene glycol | PEG (preserve MW in `additive_subtype`) |
| sorbitol, 山梨醇 | sorbitol |
| boric acid, borax, 硼酸 | boric acid |
| glutaraldehyde, GA, 戊二醛 | glutaraldehyde |
| citric acid, CA, 柠檬酸 | citric acid |

### Solvent Name Canonicalization

| Original | Canonical |
|----------|-----------|
| water, H₂O, distilled water, deionized water, DI water, 水 | water |
| DMSO, dimethyl sulfoxide | DMSO |
| DMF, dimethylformamide | DMF |
| ethanol, EtOH, ethyl alcohol, 乙醇 | ethanol |
| methanol, MeOH, 甲醇 | methanol |
| acetone, 丙酮 | acetone |
| THF, tetrahydrofuran | THF |
| chloroform, CHCl₃, 三氯甲烷 | chloroform |

### Instrument Name Canonicalization

| Original | Canonical |
|----------|-----------|
| UV-Vis, UV-Vis spectrophotometer, UV-vis spectrometer, 紫外可见分光光度计 | UV-Vis spectrophotometer |
| Haze meter, hazemeter, 雾度计 | Haze meter |
| UTM, universal testing machine, universal tensile tester, tensile tester, 万能试验机 | Universal Testing Machine (UTM) |
| DSC, differential scanning calorimeter, 差示扫描量热仪 | DSC |
| TGA, thermogravimetric analyzer, 热重分析仪 | TGA |
| SEM, scanning electron microscope, 扫描电子显微镜 | SEM |
| AFM, atomic force microscope, 原子力显微镜 | AFM |
| XRD, X-ray diffractometer, X射线衍射仪 | XRD |
| FTIR, FT-IR, Fourier transform infrared spectrometer, 傅里叶红外光谱仪 | FTIR |

### Normalization Rules

1. **Case-insensitive matching**: "pva", "PVA", "Pva" all map to "PVA"
2. **Whitespace normalization**: "PVA-1799" and "PVA - 1799" are equivalent
3. **Punctuation normalization**: "poly(vinyl alcohol)" and "poly vinyl alcohol" both map to PVA
4. **Subtype preservation**: When canonicalization loses detail (e.g., "CNT" from "MWCNT"), preserve sub-type in a separate `additive_subtype` field
5. **Unknown names**: If a material/additive name is not in the vocabulary, keep the original but flag as `name_not_in_vocabulary: true`

## Value Normalization

### Ranges to Midpoint

When a value is a range: "80-90" → record as:
```json
{
  "value": 85.0,
  "value_type": "range_midpoint",
  "value_min": 80,
  "value_max": 90
}
```

### Approximate Values

When marked with "~", "≈", "about", "approximately", "ca.":
```json
{
  "value": 40,
  "value_type": "approximate",
  "precision": "low"
}
```

### Inequality Values

When marked with ">", "<", "≥", "≤":
```json
{
  "value": 90,
  "value_type": "lower_bound",
  "inequality": ">"
}
```

### Significant Figures

Normalize numeric precision to 1 decimal place (or 2 for values < 1). Do not invent precision:
- "90.5" stays as 90.5
- "90" stays as 90 (not 90.0)
- "0.05" stays as 0.05 (not 0.050)

## Script Execution

After LLM-guided normalization, run the deterministic script:

```bash
python scripts/normalize_data.py \
  --input 02_extracted/experiments_raw.json \
  --output 03_normalized/experiments_normalized.json \
  --vocabulary assets/pva_bopet_vocabulary.json \
  --unit-map assets/unit_conversions.json \
  --synonym-map assets/synonym_map.json
```

The script handles:
- Batch unit conversion using `assets/unit_conversions.json`
- Name canonicalization using `assets/synonym_map.json`
- Range-to-midpoint computation
- Export to CSV and Excel
- Generation of `normalization_log.json`

## Normalization Log

Every transformation must be logged:

```json
{
  "total_transformations": 523,
  "unit_conversions": [
    {"experiment_id": "SRC_001_E005", "field": "film_thickness", "from": "0.08 mm", "to": "80 μm", "multiplier": 1000}
  ],
  "name_normalizations": [
    {"experiment_id": "SRC_001_E001", "field": "additive", "from": "cellulose nanocrystal", "to": "CNC"},
    {"experiment_id": "SRC_003_E012", "field": "plasticizer", "from": "glycerin", "to": "glycerol"}
  ],
  "unconvertible": [
    {"experiment_id": "SRC_005_E023", "field": "pressure", "value": "3 bar_g", "reason": "gauge pressure"}
  ],
  "unrecognized_names": [
    {"experiment_id": "SRC_008_E045", "field": "additive", "value": "novel_copolymer_X", "action": "kept_original"}
  ]
}
```

## Edge Cases

| Scenario | Action |
|----------|--------|
| Paper uses "room temperature" without specifying value | Set `drying_temperature: null`; note `temperature: "room_temperature_unspecified"` in notes |
| Paper uses "ambient conditions" | Set all unspecified conditions to null; note `conditions: "ambient_unspecified"` |
| Unit is ambiguous (e.g., "%" without specifying wt%/vol%/mol%) | Assume wt% for solid additives, vol% for liquid additives; flag `unit_ambiguity: true` |
| Same material with different trade names across papers | Map to canonical name; preserve trade name in `name_original` |
| Chinese paper uses Chinese character units (摄氏度, 微米) | Recognize and normalize to standard units (°C, μm) |