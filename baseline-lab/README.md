# IDD Baseline Lab

A dedicated Nuxt workbench that **actually runs** the comparator diagnostic
algorithms for the Industrial Deep Diagnostic (IDD) benchmark — instead of
citing them.

It reads the IDD repository's 12 benchmark scenarios, datasets and truth files as
the single source of truth, and never writes outside `baseline-lab/results/`.

```
baseline-lab/
├── server/utils/algorithms/   15 executable comparator modules (meta + run(ctx))
├── server/utils/llm/          provider adapter + blind prompt builders
├── server/api/                Nuxt server routes (state / audit / run / sweeps)
├── app/                       Nuxt 4 UI (audit · run · results · algorithms · cases)
├── scripts/                   CLI drivers and reproduction gates
└── results/                   sweeps, per-answer provenance archives
```

---

## 1. Why this exists — the audit finding

Before this lab, the repository had **exactly one runnable comparator**: the
deterministic PCA script `scripts/benchmark/baseline_pca.mjs`. Everything else
fell into one of three gaps:

| Claimed comparator | Actual state before this lab |
|---|---|
| 经典 PCA 基线 | ✅ Runnable (`scripts/benchmark/baseline_pca.mjs`) |
| 同模型裸 LLM 基线 | ⚠️ **Frozen answer archive, no execution path.** 23 genuine answers in `results/benchmark/baseline_fe_answers/`, but `baseline_llm.mjs check` only prints a *manual* execution contract. 2 of 25 expected answers missing (`tep_d00_normal_control.*`). |
| FaultExplainer | ⚠️ **Cloned but not runnable.** `baselines/FaultExplainer` @ `2fcfee9` is a complete clone, but `backend/.env` has an empty `OPENAI_API_KEY`, no sklearn/fastapi env, and `backend/results.txt` is 0 bytes. No end-to-end execution record exists. |
| CoT / ReAct / AutoGen 多代理 / XGBoost / LSTM | ❌ **Never implemented.** `docs/publication-strategy-report.md` §5.2 lists them as baseline arms; no runnable implementation existed. |

This lab closes those gaps. Open the **复现审计 / Audit** page to see the same
finding rendered from live repository state, with machine-checkable evidence
per claim.

---

## 2. The 15 runnable comparators

All are pure JavaScript with **zero external npm dependencies** — the numerics
(Jacobi eigendecomposition, F-distribution ppf, GBDT, backprop, isolation
forest) are implemented in `server/utils/linalg.mjs` and the algorithm modules.

### Classical statistical process monitoring (deterministic, offline)

| id | protocol |
|---|---|
| `pca-t2-spe` | Normal-reference PCA, 95% cumulative variance, Hotelling T² + SPE, 99th-percentile limits, SPE-contribution top-3 |
| `kpca-rbf` | RBF-kernel PCA, feature-space centring, local-scale (nearest-neighbour) bandwidth, T² + SPE |
| `ica-fastica` | FastICA on PCA-whitened data, I² + SPE monitoring |
| `spc-ewma-cusum` | Univariate EWMA (λ=0.2) + two-sided CUSUM (k=0.5σ, h=5σ) ensemble |
| `knn-fdd` | k-NN (k=5) distance to the reference set, 99th-percentile limit |
| `iforest` | Isolation Forest (100 trees, ψ=256, seeded) |

### Supervised / deep (deterministic, trained on real labelled TEP)

| id | protocol |
|---|---|
| `xgb-gbdt` | Gradient-boosted trees, 120 estimators, depth 4, one-vs-rest logistic |
| `rf-forest` | Random forest, 120 trees, Gini, mtry=√p |
| `mlp-classifier` | MLP 156→64→32→16, ReLU + softmax, real backprop, momentum SGD |
| `ae-reconstruction` | Autoencoder 52→16→6→16→52, trained on normal rows only, MSE threshold |

Trained **only** on `baselines/FaultExplainer/backend/data/fault*.csv` (real
labelled TEP runs). They declare `domains: ['tep']` and return
`applicable: false` with an empty verdict on SKAB/IndPenSim rather than
fabricating a prediction.

### LLM comparators (genuine provider calls — never fabricated)

| id | protocol |
|---|---|
| `llm-direct` | Bare single call over the blind statistical digest (2 regimes) |
| `llm-cot` | Chain-of-thought scaffold: unit attribution → deviation direction → control compensation → candidate elimination |
| `llm-react` | ReAct agent with 4 **real** data tools (`column_stats`, `top_changed_columns`, `correlate`, `window_compare`), ≤6 steps, full trajectory archived |
| `llm-debate` | 3 role-separated specialists (process / utilities / instrumentation) + rebuttal round + chair adjudication (5 calls) |
| `fe-official` | **FaultExplainer's published protocol**, reproduced from its source |

---

## 3. Reproduction gates (run these to check the claims)

Every gate is a hard, numeric pass/fail — not an assertion.

```bash
cd baseline-lab

node scripts/verify-pca.mjs          # lab PCA == repository's archived PCA numbers
node scripts/verify-fe.mjs           # FE replica == FaultExplainer's own committed outputs
node scripts/check-fe-scaler.mjs     # FE StandardScaler convention pinned
node scripts/verify-classical.mjs    # classical detectors run + are deterministic
node scripts/verify-supervised.mjs   # supervised models train/predict/refuse out-of-domain
node scripts/provider-selftest.mjs --live   # provider makes genuine, isolated calls
```

Verified results at the time of writing:

| Gate | Result |
|---|---|
| `verify-pca.mjs` | **12/12 PASS** — detection rates and retained-component counts identical to `results/benchmark/baseline_pca_rca.json` |
| `check-fe-scaler.mjs` | **12/12 exact** — pins FE's convention: all 500 rows, population std (ddof=0) |
| `verify-fe.mjs` | **21/21 PASS** — `t2_stat` relative error ~2e-12, `anomaly` flag 500/500 agreement, per-feature contributions ~1e-13, **identical trigger index** on every file |
| `verify-classical.mjs` | **60/60 PASS** |
| `verify-supervised.mjs` | **620/620 PASS** |

### The FaultExplainer fidelity result

`scripts/verify-fe.mjs` feeds the raw TEP columns from FaultExplainer's **own
committed outputs** (`baselines/FaultExplainer/frontend/public/fault*.csv`)
back through the lab's reimplementation and compares three quantities:

```
file       rows  t2_maxrelerr  anom_match  contrib_meanrelerr  trigger   verdict
fault0.csv 500   2.02e-12      500/500     7.60e-13            null/null PASS
fault1.csv 500   2.01e-12      500/500     1.31e-13            31/31     PASS
...
fault20.csv 500  2.01e-12      500/500     5.15e-13            48/48     PASS
PASS 21  FAIL 0
```

Agreement at the 1e-12 level on 52 features × 500 rows × 21 files is what makes
it defensible to call this *the* FaultExplainer protocol rather than an
approximation of it.

One subtlety the gate caught: FE clips **each component's** contribution term at
zero *before* summing (`np.maximum(c_ji, 0)` sits inside `calculate_c`). Clipping
the sum instead changed the contributions by ~40%; the per-component order is
what makes them match.

---

## 4. Truthfulness contract

These are enforced in code and auditable in the UI:

1. **No fabricated answers.** A failed or unavailable LLM call yields
   `status: skipped_no_provider` / `error` with an **empty** `top3`. Nothing is
   invented to fill a gap
   (`docs/benchmark/reproduction-guide.md` §10 red line).
2. **Truth isolation.** Algorithms receive a sanitized case
   (`loadCaseForAlgorithm` strips `truth` / `keywords` / `literature_baseline`).
   Scoring happens only *after* the algorithm returns.
3. **No per-case tuning.** Thresholds are calibrated on the reference
   (normal-control) file of the same dataset — never on the file under test.
4. **Bare-LLM isolation.** CLI harnesses run with a neutral `cwd` and tools
   disabled, so the comparator cannot read this repository's `CLAUDE.md` /
   `AGENTS.md` / skills. `provider-selftest.mjs --live` checks this explicitly.
5. **Provenance.** Every LLM reply is archived verbatim under
   `results/answers/<case>/<algorithm>.<timestamp>.json` with provider, model,
   latency, prompt and raw text.
6. **Self-test stub excluded.** The deterministic `selftest` provider is tagged
   `fabricated: true`, is off by default, and is never scored.

### Model comparability warning

The repository's archived LLM baseline was produced with a **GLM-family**
deployment (`results/benchmark/baselines.json`). The lab auto-detects whatever
harness CLI is installed — on this machine that is **Claude**. A fresh LLM run
is therefore **a different experiment**, not a reproduction of the archived
numbers.

The lab detects this and shows a `CONFOUND` banner in the sidebar, on the Run
page and on the Results page. To align with the archive, point the lab at the
original model:

```bash
BASELINE_LLM_PROVIDER=openai-compatible \
BASELINE_LLM_BASE_URL=https://<glm-endpoint>/v1 \
BASELINE_LLM_API_KEY=... \
BASELINE_LLM_MODEL=glm-4.6 \
npm run dev
```

---

## 5. Measured results (120 deterministic runs, 26.4 s)

**Top-1%** is the repository's rubric (rank-1 hits a mechanism keyword *or* names
the true IDV). **exact IDV** requires rank-1 to name the true IDV number. Both
are reported because fault families such as `{IDV4, IDV11, IDV14}` share their
keywords verbatim — a keyword hit does **not** mean the fault was distinguished
within its family.

| algorithm | Top-1 | Top-1% | Wilson 95% | exact IDV | ctrl pass | false alarms | abstain |
|---|---|---|---|---|---|---|---|
| `pca-t2-spe` | 4/9 | 44% | [18.9, 73.3] | 1/6 | 3/3 | 0 | 4 |
| `kpca-rbf` | 4/9 | 44% | [18.9, 73.3] | 2/6 | 3/3 | 0 | 4 |
| `ica-fastica` | 4/9 | 44% | [18.9, 73.3] | 1/6 | 3/3 | 0 | 4 |
| `spc-ewma-cusum` | 4/9 | 44% | [18.9, 73.3] | 1/6 | 3/3 | 0 | 3 |
| `knn-fdd` | 4/9 | 44% | [18.9, 73.3] | 2/6 | 3/3 | 0 | 4 |
| `iforest` | 3/9 | 33% | [12.1, 64.6] | 0/6 | 3/3 | 0 | 5 |
| `xgb-gbdt` | 6/9 | 67% | [35.4, 87.9] | **6/6** | 2/3 | 1 | 3 |
| `rf-forest` | 6/9 | 67% | [35.4, 87.9] | **6/6** | **3/3** | **0** | 3 |
| `mlp-classifier` | 4/9 | 44% | [18.9, 73.3] | 4/6 | 2/3 | 1 | 3 |
| `ae-reconstruction` | 4/9 | 44% | [18.9, 73.3] | 2/6 | 2/3 | 1 | 3 |

Reproduce with:

```bash
node scripts/sweep.mjs --algorithms pca-t2-spe,kpca-rbf,ica-fastica,spc-ewma-cusum,knn-fdd,iforest,xgb-gbdt,rf-forest,mlp-classifier,ae-reconstruction --label full-deterministic
```

### LLM comparators (20 runs, 39 min, real provider calls)

Scoped to the four TEP scenarios with a control (`d01`, `d04`, `d07`, `d00-control`),
since the `fe-official` cause list and the `with_candidates` regime are TEP-specific.

| algorithm | Top-1 | exact IDV | FE@3 | control | false alarms | calls/scenario |
|---|---|---|---|---|---|---|
| `llm-direct` | 1/3 | 0/3 | 0/3 | 0/1 | 1 | 1 |
| `llm-cot` | 1/3 | 0/3 | 0/3 | 0/1 | 1 | 1 |
| `llm-react` | 2/3 | 0/3 | 0/3 | 0/1 | 1 | up to 7 |
| `llm-debate` | 1/3 | 0/3 | 0/3 | 0/1 | 1 | 5 |
| `fe-official` | 2/3 | **2/3** | **3/3** | **1/1** | **0** | 1 |

```bash
node scripts/sweep.mjs --algorithms llm-direct,llm-cot,llm-react,llm-debate,fe-official \
  --cases tep_d01_ac_feed_ratio,tep_d04_reactor_cooling_step,tep_d07_header_pressure,tep_d00_normal_control \
  --label full-llm
```

**How to read it**

- **`fe-official` is the strongest and the only one that does not false-alarm on the
  normal control** — because its statistical front end *gates* the model call (no
  6-consecutive T² violation ⇒ it reports normal instead of asking the model to
  invent a cause). Prompting alone does not buy that.
- **These numbers are far below the archived baseline's claimed 9/9 strict**, and
  that is expected: the archive came from a GLM deployment, this run used Claude.
  It is a different model, hence a different experiment — see the confound banner
  in §4. Do not read this column as "the baseline got worse".
- Every answer is archived verbatim (prompt, provider, model, latency, raw reply)
  under `results/answers/<case>/`. The `llm-debate` trajectory archives all five
  panel turns including the rebuttals, so the debate is auditable rather than
  summarised.

**How to read it**

- The classical detectors look like 44%, but their **exact-IDV rate is only
  17–33%**. They rank contributing *variables* faithfully; the variable →
  mechanism step is a separate knowledge table, and family-level discrimination
  largely fails. This is consistent with the repository's own note that
  IDV3/IDV4 are a PCA-undetectable set (Chiang et al. 2001).
- The supervised models identify **6/6 TEP faults exactly**, but `xgb`, `mlp` and
  `ae` each raise one false alarm on the normal control. **`rf-forest` is the
  only algorithm that is both 6/6 exact and 0 false alarms.**
- Every algorithm largely abstains on SKAB/IndPenSim: no published
  variable→cause table exists for those domains, and the lab **refuses to invent
  one**. Supervised models report `not_applicable` there by design.

---

## 6. Running it

```bash
cd baseline-lab
npm install
npm run dev            # http://localhost:5190
```

Then:

- **复现审计** — the audit finding, with evidence
- **运行基线** — pick algorithms × cases, watch a live progress table
- **结果对比** — per-scenario × per-algorithm decision matrix + Wilson CIs
- **算法清单** — the registry, including declared-but-missing modules
- **场景与数据** — the 12 scenarios and the repository contract

### CLI

```bash
node scripts/sweep.mjs --list
node scripts/sweep.mjs --family classical
node scripts/sweep.mjs --algorithms pca-t2-spe,rf-forest --cases tep_d01_ac_feed_ratio
node scripts/sweep.mjs --algorithms llm-direct --cases tep_d01_ac_feed_ratio
node scripts/sweep.mjs --help
```

### Reading the metrics

- **Top-1%** — IDD rubric: rank-1 hits a mechanism keyword *or* names the true
  IDV number. **This is family-level for fault families that share keywords**:
  `{IDV4, IDV11, IDV14}` all read "reactor cooling water" / "冷却水".
- **精确 IDV / exact** — rank-1 explicitly names the **true IDV number**. This is
  strictly harder and is the number to quote when claiming fault discrimination.
- **FE@3** — FaultExplainer's lenient criterion: true IDV or an alias-class IDV
  anywhere in top-3.
- **对照通过 / ctrl** — control cases returning "normal". **误报 / FA** — controls
  that alarmed. A detector that alarms on normal data is worse than one that
  abstains.
- **弃权 / abstain** — no detection, so no root-cause claim. Honest, not a miss
  to be hidden.

### Provider configuration

| Variable | Meaning |
|---|---|
| `BASELINE_LLM_PROVIDER` | `auto` (default) or `cli:claude`, `cli:dsh`, `cli:codex`, `cli:omp`, `openai-compatible`, … |
| `BASELINE_LLM_CLI_PATH` | Absolute path to a harness binary (overrides PATH search) |
| `BASELINE_LLM_CLI_DIR` | Extra directory to search for harness binaries |
| `BASELINE_LLM_BASE_URL` / `BASELINE_LLM_API_KEY` / `BASELINE_LLM_MODEL` | OpenAI-compatible HTTP endpoint |
| `BASELINE_LLM_TIMEOUT_MS` | Per-call timeout (default 300000) |
| `BASELINE_LLM_ALLOW_SELFTEST` | `1` enables the plumbing stub (never scored) |
| `IDD_REPO_ROOT` | Override the IDD repository location |

Visit `/api/provider-doctor` to see exactly what the server can discover.

---

## 7. Honest gaps

### Algorithm-level methodological disclosures

Reported because they change how a row should be read — none of them were
adjusted per case, and each is machine-readable in the algorithm's output.

- **`spc-ewma-cusum` uses a multiplicity-corrected decision rule.** Per-column 1%
  charts combined with "≥1 column alarms" has no multiplicity control: measured
  uncorrected union false-alarm rates on the reference files are 48.1% (TEP,
  m=52), 13.0% (SKAB, m=8), 27.4% (IndPenSim, m=32) — matching
  `1−(1−0.01)^m` — which made SPC alarm on all three controls. The operative
  limit is therefore the 99th percentile of the **reference combined exceedance
  statistic** `a_t = max_j max(|EWMA|/limit_j, CUSUM_j/limit_j)`. The literal
  uncorrected rate is still reported as `detection.any_column_alarm_rate` and the
  rule is named in `decision_rule`. This is a global rule, not per-case tuning.
- **`kpca-rbf`'s T² chart contributes zero detections; every kPCA alarm comes
  from SPE.** Fault-window T² sits *below* the reference limit because
  retained-subspace energy saturates downward. Also, the RBF kernel genuinely
  saturates on d01/d07/d14 (mean `k(x,·)` collapses to 2.6e-3 / 4.5e-2 / 9.9e-3
  against a reference 0.343), so SPE pins at its saturation constant there and
  detection is an out-of-support/novelty flag rather than a graded deviation.
- **`ica-fastica` does not reach its convergence tolerance on TEP** — it hits the
  500-iteration cap at a=35 (it converges in 47/49 iterations on SKAB and
  IndPenSim). Exposed as `ica_converged: false` / `ica_iterations: 500`.
- **`iforest` is the weakest classical detector** (d04/d14/IndPenSim all read as
  normal; 0/6 exact IDV). Its per-variable attribution is a documented
  split-participation depth *proxy*, not an additive path-length decomposition.
- **`tep_d03` (IDV-3, D-feed-temperature step) is missed by 4 of 5 classical
  detectors** — consistent with the archived PCA baseline
  (`results/benchmark/baseline_pca_rca.json`: T² 0.0288 / SPE 0.0475), i.e. the
  known-hard fault rather than an implementation bug. SPC catches it (0.4462)
  because a univariate chart reacts to a small single-channel shift.

### Coverage gaps

Recorded in the audit page as `citation_only`, not hidden:

- **FaultExplainer's Python pipeline is not run natively.** It needs an OpenAI
  key and a scientific-Python environment. The `fe-official` module reproduces
  its algorithm instead — and is validated to ~1e-12 against FE's own outputs,
  which is stronger evidence than "we ran their script once".
- **Gong et al. (JII 2026) is not reproducible.** FailureSensorIQ is an MCQA
  dataset; the agent orchestration is not open-sourced. `llm-debate` is a local,
  framework-free implementation of the same *shape*, not their system.
- **AutoGen / CrewAI are not installed.** `llm-debate` is framework-free.
- **Published XGBoost/LSTM/BeatGAN numbers are citation-only** — different task
  (per-sample detection vs root-cause). `xgb`/`rf`/`mlp`/`ae` are same-family
  models measured on *this* benchmark.
- **Supervised models are TEP-only** and return `applicable: false` elsewhere.
  Known caveats from their verification: a training/evaluation window mismatch
  (80 vs 800 samples), XGB train accuracy 1.000 (interpolates 336 samples), and
  the AE's calibration does not transfer per-row between the two TEP encodings.
  These are reported, not tuned away.
- **`tep_d00_normal_control` has 2 missing archived LLM answers** in the
  repository's own archive.
- **The 12-scenario set is small.** Wilson intervals are reported everywhere, but
  a 9-fault benchmark cannot support fine-grained ranking claims.
