export function preAuditPolicyValid({ runMode, preAuditExists, preAuditSkipped }) {
  if (runMode === 'fast') return !preAuditExists && preAuditSkipped;
  if (runMode === 'full') return preAuditExists && !preAuditSkipped;
  return false;
}

export function visualEvidenceSatisfied({ runMode, visualExists, captionsExist, vlmSkipped }) {
  if (visualExists) return true;
  return runMode === 'fast' && vlmSkipped && captionsExist;
}

export function requiredArtifactsForMode(required, { htmlOptOut = false } = {}) {
  return htmlOptOut
    ? required.filter(item => !['diagnostic-report.html', '05_review/html_review.json'].includes(item))
    : [...required];
}

export function validateSkippedStageEvidence(skippedStages, events) {
  const missing = [];
  for (const stage of skippedStages || []) {
    const name = stage?.stage;
    const reason = stage?.reason;
    const eventName = stage?.event;
    if (!name || !reason || eventName !== 'artifact_check_complete') {
      missing.push(name || '<unknown>');
      continue;
    }
    const found = (events || []).some((event) =>
      event?.event === eventName &&
      event?.skipped_stage === name &&
      event?.reason === reason
    );
    if (!found) missing.push(name);
  }
  return missing;
}
