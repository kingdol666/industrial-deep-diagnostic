import { randomUUID } from 'node:crypto';
import { z } from 'zod';
import { db } from '../db/database.mjs';
import { requireLineAction, requireRunKnowledgeScope } from './production-line.service.mjs';
import { getPublishedVersion } from './knowledge-publication.service.mjs';

const searchInput = z.strictObject({
  query: z.string().trim().min(2).max(200),
  signals: z.array(z.string().trim().min(1).max(80)).max(8).optional(),
  limit: z.number().int().min(1).max(10).default(5),
});
const fail = (status, code, message) => Object.assign(new Error(message), { status, code });
const unavailable = () => fail(404, 'KNOWLEDGE_ITEM_NOT_FOUND', '参考资料不存在或不再可用');
const clean = (value, max) => String(value ?? '').replace(/[\p{Cc}\p{Cf}]/gu, ' ').replace(/\s+/gu, ' ').trim().slice(0, max);
const normalize = (value) => value.normalize('NFKC').toLowerCase();
const sourceKey = ({ source_kind, source_id, source_version }) => JSON.stringify([source_kind, source_id, source_version]);
const termsFor = ({ query, signals }) => [...new Set([query, ...query.split(/[^\p{L}\p{N}_-]+/u), ...(signals ?? [])]
  .map(normalize).filter((s) => [...s].length >= 2))].slice(0, 16);
const ftsFor = (terms) => terms.filter((s) => [...s].length >= 3).map((s) => `"${s.replaceAll('"', '""')}"`).join(' OR ');

const eligible = `r.line_id = @line AND r.owner_user_id = @actor AND CAST(r.owner_user_id AS TEXT) = r.user_id
  AND r.run_id <> @run AND r.status = 'completed' AND r.harness <> 'mock' AND r.deleted_at IS NULL`;
const reviewJoin = `JOIN diagnosis_review_revisions h ON h.run_id = r.run_id
  AND h.revision = (SELECT MAX(v.revision) FROM diagnosis_review_revisions v WHERE v.run_id = r.run_id)`;
const reviewCurrent = `h.source_completed_at IS r.completed_at AND COALESCE(h.source_completion_revision, 0) = r.completion_revision`;
const reviewFields = `r.run_id, r.completion_revision, h.revision, COALESCE(NULLIF(h.takeaway,''), NULLIF(h.manual_summary,''), h.original_summary) AS detail`;
const reviewFilter = `${eligible} AND ${reviewCurrent} AND h.status = 'confirmed' AND h.reuse_enabled = 1`;
const observationJoin = `FROM knowledge_observations o JOIN diagnostic_runs r ON r.run_id = o.run_id
  WHERE ${eligible} AND o.line_id = @line AND o.completion_revision = r.completion_revision
  AND NOT EXISTS (SELECT 1 FROM diagnosis_review_revisions h WHERE h.run_id = r.run_id
    AND h.revision = (SELECT MAX(v.revision) FROM diagnosis_review_revisions v WHERE v.run_id = r.run_id)
    AND (h.status <> 'confirmed' OR h.reuse_enabled = 0 OR NOT (${reviewCurrent})))`;
const observationFields = 'o.id, o.completion_revision, o.subject, o.detail';

const localReviews = db.prepare(`SELECT ${reviewFields} FROM diagnostic_runs r ${reviewJoin} WHERE ${reviewFilter}`);
const oneReview = db.prepare(`SELECT ${reviewFields} FROM diagnostic_runs r ${reviewJoin} WHERE ${reviewFilter} AND r.run_id = @source`);
const localObservations = db.prepare(`SELECT ${observationFields} ${observationJoin}
  AND ((@fts <> '' AND o.id IN (SELECT rowid FROM knowledge_observation_fts WHERE knowledge_observation_fts MATCH NULLIF(@fts,'')))
    OR EXISTS (SELECT 1 FROM json_each(@terms) t WHERE instr(lower(o.subject),t.value)>0 OR instr(lower(o.detail),t.value)>0))`);
const oneObservation = db.prepare(`SELECT ${observationFields} ${observationJoin} AND o.id = @source`);
const upsertObservation = db.prepare(`INSERT OR IGNORE INTO knowledge_observations(run_id,line_id,completion_revision,finding_id,subject,detail)
  VALUES (@run_id,@line_id,@completion_revision,@finding_id,@subject,@detail)`);
const currentRun = db.prepare('SELECT * FROM diagnostic_runs WHERE run_id = ?');
const historyInsert = db.prepare(`INSERT INTO knowledge_retrievals(retrieval_id,run_id,actor_user_id,attempt_id,action,outcome,item_count)
  VALUES (?,?,?,?,?,?,?)`);
const refInsert = db.prepare(`INSERT INTO knowledge_retrieval_refs(retrieval_id,ref_id,source_kind,source_id,source_version)
  VALUES (?,?,?,?,?)`);
const refLookup = db.prepare(`SELECT f.* FROM knowledge_retrieval_refs f JOIN knowledge_retrievals h USING(retrieval_id)
  WHERE f.ref_id = ? AND h.action = 'search' AND h.run_id = ? AND h.actor_user_id = ? AND h.attempt_id IS ? LIMIT 1`);
const budget = db.prepare('SELECT COUNT(*) FROM knowledge_retrievals WHERE attempt_id = ?').pluck();
const retrievals = db.prepare(`SELECT h.retrieval_id,h.action,h.outcome,h.item_count,h.created_at,
  CASE WHEN h.attempt_id IS NULL THEN 'preview' ELSE 'agent' END AS channel
  FROM knowledge_retrievals h WHERE h.run_id = ? AND h.actor_user_id = ?
  ORDER BY h.created_at DESC,h.rowid DESC LIMIT 100`);
const refDisplay = db.prepare('SELECT ref_id,source_kind,source_version FROM knowledge_retrieval_refs WHERE retrieval_id = ? ORDER BY rowid');

// Re-resolve membership and the persisted run policy even when called from an already-bound adapter.
function reauthorize(scope) {
  const actor = scope?.actor;
  const run = requireRunKnowledgeScope(actor, scope?.run_id);
  if (actor.id !== run.owner_user_id && String(actor.id) !== String(run.owner_user_id)) {
    throw fail(404, 'RUN_NOT_FOUND', '作业不存在或不可用');
  }
  return { ...run, actor, attempt_id: scope.attempt_id ?? null };
}

function enabled(scope) {
  if (!scope.line_id || scope.knowledge_policy?.mode !== 'on_demand') {
    throw fail(409, 'KNOWLEDGE_DISABLED', '此作业未启用按需记忆');
  }
  if (scope.line_id) requireLineAction(scope.actor, scope.line_id, 'run');
  if (scope.attempt_id && currentRun.get(scope.run_id)?.status !== 'running') throw unavailable();
}

const params = (scope) => ({ line: scope.line_id, actor: scope.actor.id, run: scope.run_id });
const reviewItem = (row) => ({
  source_kind: 'local_review', source_id: row.run_id, source_version: `${row.completion_revision}.${row.revision}`,
  title: '本线人工确认', detail: row.detail, human_review: 'confirmed', applicability: '以本次工况和数据核验',
});
const observationItem = (row) => ({
  source_kind: 'local_observation', source_id: String(row.id), source_version: String(row.completion_revision),
  title: row.subject, detail: row.detail, human_review: 'automatic', applicability: '本线历史观测；以本次数据核验',
});
function sharedItem(scope, ref) {
  try {
    const v = getPublishedVersion(scope.actor, ref, 'reuse');
    if (!['experience', 'memory_excerpt'].includes(v.kind)) return null;
    return { source_kind: 'published_asset', source_id: v.asset_id, source_version: String(v.version),
      title: v.title, excerpt: v.summary, detail: v.content, human_review: 'curated', applicability: v.applicability };
  } catch (err) {
    if (err.status === 404 || err.status === 403 || err.status === 409) return null;
    throw err;
  }
}

function publicItem(item, ref_id, detail = false) {
  return { ref_id, source_kind: item.source_kind, source_version: item.source_version,
    ...(item.source_kind === 'published_asset' && { asset_id: item.source_id }),
    title: clean(item.title, 160), excerpt: clean(item.excerpt || item.detail, 240), evidence_level: 'L5',
    human_review: item.human_review, applicability: clean(item.applicability, 240),
    ...(detail && { detail: clean(item.detail, 1600) }) };
}

function audit(scope, action, outcome, items = []) {
  const id = randomUUID();
  historyInsert.run(id, scope.run_id, scope.actor.id, scope.attempt_id, action, outcome, items.length);
  for (const item of items) refInsert.run(id, item.ref_id, item.source_kind, item.source_id, item.source_version);
  return id;
}

// Expected denials are recorded in the same transaction as reads. Throw after commit.
function read(scope, action, fn) {
  const tx = db.transaction(() => {
    const authorized = reauthorize(scope);
    if (authorized.attempt_id && budget.get(authorized.attempt_id) >= 20) {
      return { error: fail(429, 'KNOWLEDGE_BUDGET_EXCEEDED', '此运行尝试的检索次数已达上限') };
    }
    try { enabled(authorized); return { output: fn(authorized) }; } catch (err) {
      if (!err.status || err.status >= 500) throw err;
      audit(authorized, action, err.code || 'denied');
      return { error: err };
    }
  }).immediate();
  if (tx.error) throw tx.error;
  return tx.output;
}

export function searchForRun(scope, input) {
  const parsed = searchInput.safeParse(input);
  if (!parsed.success) throw fail(400, 'KNOWLEDGE_QUERY_INVALID', 'query、signals 或 limit 不符合检索格式');
  return read(scope, 'search', (authorized) => {
    const terms = termsFor(parsed.data);
    const hits = [];
    // Score from the scoped row itself. Global FTS frequency and scores are never returned or used.
    const consider = (item) => {
      if (!item?.detail) return;
      const title = normalize(item.title || '');
      const text = normalize(`${item.excerpt || ''} ${item.detail} ${item.applicability || ''}`);
      const rank = terms.reduce((n, term) => n + (title.includes(term) ? 3 : 0) + Number(text.includes(term)), 0);
      if (!rank) return;
      hits.push({ ...item, rank });
      hits.sort((a, b) => b.rank - a.rank || sourceKey(a).localeCompare(sourceKey(b)));
      if (hits.length > parsed.data.limit) hits.pop();
    };
    if (authorized.knowledge_policy.own_line) {
      for (const row of localReviews.iterate(params(authorized))) consider(reviewItem(row));
      for (const row of localObservations.iterate({ ...params(authorized), terms: JSON.stringify(terms), fts: ftsFor(terms) })) {
        consider(observationItem(row));
      }
    }
    for (const selected of authorized.knowledge_policy.references ?? []) consider(sharedItem(authorized, selected));
    const matched = hits.map((item) => ({ ...item, ref_id: randomUUID() }));
    const retrieval_id = audit(authorized, 'search', matched.length ? 'ok' : 'no_match', matched);
    return { items: matched.map((item) => publicItem(item, item.ref_id)), retrieval_id,
      ...(matched.length === 0 && { note: '授权来源内无匹配；未扩大检索范围。' }) };
  });
}

export function getForRun(scope, refId) {
  if (typeof refId !== 'string' || refId.length < 1 || refId.length > 128) throw unavailable();
  return read(scope, 'get', (authorized) => {
    const ref = refLookup.get(refId, authorized.run_id, authorized.actor.id, authorized.attempt_id);
    if (!ref) throw unavailable();
    let item = null;
    if (ref.source_kind === 'published_asset') {
      const selected = authorized.knowledge_policy.references?.find((v) => v.asset_id === ref.source_id && String(v.version) === ref.source_version);
      if (selected) item = sharedItem(authorized, selected);
    } else if (authorized.knowledge_policy.own_line) {
      const args = { ...params(authorized), source: ref.source_id };
      const row = ref.source_kind === 'local_review' ? oneReview.get(args) : oneObservation.get(args);
      if (row) item = ref.source_kind === 'local_review' ? reviewItem(row) : observationItem(row);
    }
    if (!item || item.source_version !== ref.source_version) throw unavailable();
    const retrieval_id = audit(authorized, 'get', 'ok', [{ ...item, ref_id: refId }]);
    return { item: publicItem(item, refId, true), retrieval_id };
  });
}

export function listLocalReviewedContext(scope) {
  const authorized = reauthorize(scope);
  if (!authorized.line_id || !authorized.knowledge_policy?.own_line || authorized.knowledge_policy.mode !== 'on_demand') return [];
  requireLineAction(authorized.actor, authorized.line_id, 'run');
  return localReviews.all(params(authorized)).sort((a, b) => b.revision - a.revision || a.run_id.localeCompare(b.run_id))
    .slice(0, 3).map((row) => ({ run_id: row.run_id, revision: row.revision, status: 'confirmed', takeaway: clean(row.detail, 240) }));
}

export function listRunRetrievals(scope) {
  const authorized = reauthorize(scope);
  return { items: retrievals.all(authorized.run_id, authorized.actor.id).map((r) => ({ ...r, refs: refDisplay.all(r.retrieval_id) })) };
}

// The completion hook supplies observations from its allowlisted deterministic artifacts,
// not free text provided by the model, not publication bodies, and not comparisons.
export const recordCompletedEvidence = db.transaction((runId, completionRevision, findings) => {
  const run = currentRun.get(runId);
  if (!run?.line_id || !run.owner_user_id || String(run.owner_user_id) !== run.user_id || run.deleted_at || run.harness === 'mock'
      || run.status !== 'completed' || !completionRevision || run.completion_revision !== completionRevision
      || run.dataset_refs_json !== '[]') return 0;
  let changes = 0;
  for (const f of findings.slice(0, 100)) {
    const subject = normalize(clean(f.subject, 160));
    const detail = normalize(clean(f.detail, 1600));
    if (!subject || !detail || !f.finding_id) continue;
    changes += upsertObservation.run({ run_id: runId, line_id: run.line_id, completion_revision: completionRevision,
      finding_id: String(f.finding_id), subject, detail }).changes;
  }
  return changes;
}).immediate;
