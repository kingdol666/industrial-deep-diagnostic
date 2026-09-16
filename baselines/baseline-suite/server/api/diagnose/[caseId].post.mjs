// POST /api/diagnose/:caseId — run baseline diagnosis arms on one scenario.
// Body: { arm: "pca" | "fe" | "llm", regime?: "no_candidates" | "with_candidates" | "fe_official" }
// Every response is written to runs/<case_id>.<arm>[_<regime>].json for the
// benchmark-side comparison report builder.
import { defineEventHandler, getRouterParam, readBody, createError } from 'h3';
import fs from 'node:fs';
import path from 'node:path';
import { routingFor, briefFor, tepCauseTable, SUITE_ROOT } from '../../utils/repo.mjs';
import { runPcaArm } from '../../utils/pca.mjs';
import { runFeArm } from '../../utils/fe.mjs';
import { runLlmArm, buildBlindPrompt } from '../../utils/llm.mjs';

const RUNS = path.join(SUITE_ROOT, 'runs');

export default defineEventHandler(async (event) => {
  const caseId = getRouterParam(event, 'caseId');
  const body = await readBody(event).catch(() => ({}));
  const arm = body.arm || 'pca';
  const regime = body.regime || 'no_candidates';

  const routing = routingFor(caseId); // truth-free routing facts only
  const brief = briefFor(caseId);
  const startedAt = new Date().toISOString();

  let result;
  if (arm === 'pca') {
    result = runPcaArm(routing);
  } else if (arm === 'fe') {
    if (routing.dataset !== 'tep') throw createError({ statusCode: 400, statusMessage: 'FE protocol applies to TEP scenarios only' });
    result = runFeArm(routing);
  } else if (arm === 'llm') {
    const prompt = buildBlindPrompt(brief, regime, tepCauseTable());
    result = await runLlmArm({ caseId, brief, regime, causeTable: tepCauseTable(), prompt });
  } else {
    throw createError({ statusCode: 400, statusMessage: `unknown arm: ${arm} (pca | fe | llm)` });
  }

  const record = {
    case_id: caseId,
    dataset: routing.dataset,
    control: routing.control,
    executed_at: startedAt,
    ...result,
  };
  fs.mkdirSync(RUNS, { recursive: true });
  const file = path.join(RUNS, `${caseId}.${arm}${arm === 'llm' ? `.${regime}` : ''}.json`);
  fs.writeFileSync(file, JSON.stringify(record, null, 1) + '\n');
  return { ...record, saved_to: path.relative(SUITE_ROOT, file) };
});
