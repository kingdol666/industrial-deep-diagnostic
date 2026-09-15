// TEP variable -> root-cause affinity, and the classical "contribution plot +
// knowledge-based diagnosis" step.
//
// HONESTY CONTRACT
// ----------------
// Classical detectors (PCA/KPCA/ICA/SPC/kNN/IForest) do NOT produce mechanism
// verdicts. What they produce is a ranked list of CONTRIBUTING VARIABLES.
// Turning that into a root-cause claim requires a separate, explicitly
// knowledge-based mapping step. This module implements that step so the
// comparison is meaningful, and it is reported as a distinct field
// (`diagnosis_step`) so no reader can mistake it for free detector output.
//
// The affinity map is standard Downs & Vogel plant knowledge: each TEP fault
// perturbs a physical stream or utility loop, so its signature concentrates on
// the measurements and manipulators of that loop.

import { loadCauseTable } from './paths.mjs';

/** variable -> ordered candidate IDVs (most specific first). */
export const TEP_VARIABLE_AFFINITY = {
  // --- feed streams -------------------------------------------------------
  XMEAS_1: ['IDV6'],                       // A feed flow (Stream 1)
  XMEAS_2: ['IDV3', 'IDV9'],               // D feed flow (Stream 2)
  XMEAS_3: ['IDV3', 'IDV9'],               // E feed flow
  XMEAS_4: ['IDV1', 'IDV2', 'IDV7', 'IDV8', 'IDV10'], // A and C feed (Stream 4)
  XMEAS_5: ['IDV1', 'IDV7', 'IDV2', 'IDV8'],
  XMEAS_6: ['IDV1', 'IDV2', 'IDV6', 'IDV7', 'IDV8'],
  XMV_1: ['IDV3', 'IDV9'],                 // D feed load
  XMV_3: ['IDV6'],                         // A feed load
  XMV_4: ['IDV1', 'IDV2', 'IDV7', 'IDV8', 'IDV10'], // A/C feed load
  // --- reactor cooling loop ----------------------------------------------
  XMEAS_9: ['IDV4', 'IDV11', 'IDV14'],     // reactor temperature
  XMEAS_21: ['IDV4', 'IDV11', 'IDV14'],    // reactor coolant outlet temp
  XMV_10: ['IDV4', 'IDV11', 'IDV14'],      // reactor coolant flow
  // --- condenser cooling loop --------------------------------------------
  XMEAS_11: ['IDV5', 'IDV12', 'IDV15'],    // product separator temperature
  XMEAS_22: ['IDV5', 'IDV12', 'IDV15'],    // separator coolant outlet temp
  XMV_11: ['IDV5', 'IDV12', 'IDV15'],      // condenser coolant flow
  // --- composition train --------------------------------------------------
  XMEAS_23: ['IDV1', 'IDV2', 'IDV8'],      // A to reactor
  XMEAS_24: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_25: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_26: ['IDV1', 'IDV2', 'IDV8', 'IDV13'],
  XMEAS_27: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_28: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_29: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_30: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_31: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_32: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_33: ['IDV1', 'IDV2', 'IDV8', 'IDV10'],
  XMEAS_34: ['IDV2', 'IDV8'],
  XMEAS_35: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_36: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_37: ['IDV1', 'IDV2', 'IDV8'],      // D in product
  XMEAS_38: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_39: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_40: ['IDV1', 'IDV2', 'IDV8'],
  XMEAS_41: ['IDV2', 'IDV8'],
  // --- pressure / level headers ------------------------------------------
  XMEAS_7: ['IDV7', 'IDV13', 'IDV4'],
  XMEAS_8: ['IDV4', 'IDV13'],
  XMEAS_10: ['IDV7', 'IDV6', 'IDV13'],
  XMEAS_13: ['IDV5', 'IDV7'],
  XMEAS_15: ['IDV7', 'IDV5'],
  XMEAS_16: ['IDV7', 'IDV1', 'IDV5'],
  XMEAS_17: ['IDV7', 'IDV5'],
  XMEAS_18: ['IDV7', 'IDV3'],
  XMEAS_19: ['IDV7', 'IDV3'],
  XMEAS_20: ['IDV7', 'IDV13'],
  XMEAS_12: ['IDV5', 'IDV7'],
  XMEAS_14: ['IDV5', 'IDV1'],
  XMV_5: ['IDV7', 'IDV13'],
  XMV_6: ['IDV7', 'IDV6'],
  XMV_7: ['IDV5'],
  XMV_8: ['IDV7', 'IDV5'],
  XMV_9: ['IDV7', 'IDV3'],
  XMV_2: ['IDV3', 'IDV9'],
};

/**
 * Map a ranked list of contributing variables to ranked IDV candidates.
 * Score = sum over positions of (weight / rank), so a fault named by several
 * high-ranked contributors outranks one named once at the bottom.
 */
export function variablesToCandidates(rankedVars, { maxCandidates = 3 } = {}) {
  const causes = loadCauseTable();
  const scores = new Map();
  rankedVars.forEach((v, i) => {
    const aff = TEP_VARIABLE_AFFINITY[v];
    if (!aff) return;
    const w = 1 / (i + 1);
    aff.forEach((idv, k) => {
      const specificity = 1 / (1 + 0.35 * k); // first-listed cause is most specific
      scores.set(idv, (scores.get(idv) || 0) + w * specificity);
    });
  });
  const ranked = [...scores.entries()].sort((a, b) => b[1] - a[1]);
  return ranked.slice(0, maxCandidates).map(([idv, score]) => ({
    idv,
    score: Number(score.toFixed(4)),
    label: `${idv}: ${causes.faults[idv] || idv}`,
  }));
}

/**
 * Non-TEP domains have no published per-variable cause table. Rather than
 * invent one, the mapping step is declared unavailable and the classical
 * baselines report variables only (verdict = fault/normal from detection).
 */
export function affinityAvailable(dataset) {
  return dataset === 'tep';
}
