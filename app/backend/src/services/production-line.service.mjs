import { randomUUID } from 'node:crypto';
import { db, stmts } from '../db/database.mjs';

const MEMBER_LEVEL = Object.freeze({ read: 1, run: 2, manage: 3 });
const NAME_MAX = 120;
const MAX_REFS = 8;
const TERMINAL = new Set(['completed', 'failed', 'stopped', 'interrupted', 'expired']);
const UUID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
export const DEFAULT_KNOWLEDGE_POLICY = Object.freeze({ mode: 'on_demand', own_line: true, references: Object.freeze([]) });

function fail(status, code, message) {
  throw Object.assign(new Error(message), { status, code });
}
const lineNotFound = () => fail(404, 'LINE_NOT_FOUND', 'Production line not found');
const runNotFound = () => fail(404, 'RUN_NOT_FOUND', 'Run not found');

function positiveId(value) {
  const id = typeof value === 'string' && /^[1-9]\d*$/.test(value) ? Number(value) : value;
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

function requireActor(actor) {
  const id = positiveId(actor?.id);
  const user = id && stmts.getUserById.get(id);
  if (!user) fail(401, 'AUTH_REQUIRED', '请先登录');
  return user;
}

function parseJson(value) {
  try { return JSON.parse(value); } catch { return null; }
}

function lineView({ aliases_json, ...line }) {
  return { ...line, aliases: parseJson(aliases_json) ?? [] };
}

const getLine = db.prepare('SELECT * FROM production_lines WHERE line_id = ?');
const getMembership = db.prepare('SELECT role FROM production_line_members WHERE line_id = ? AND user_id = ?').pluck();
const insertLine = db.prepare('INSERT INTO production_lines (line_id, name, created_by_user_id) VALUES (?, ?, ?)');
const insertMember = db.prepare(`INSERT INTO production_line_members (line_id, user_id, role)
  VALUES (?, ?, ?) ON CONFLICT(line_id, user_id) DO UPDATE SET role = excluded.role, updated_at = datetime('now')`);
const listAccessible = db.prepare(`SELECT l.*, m.role AS member_role
  FROM production_lines l JOIN production_line_members m ON m.line_id = l.line_id
  WHERE m.user_id = ? ORDER BY l.created_at, l.line_id`);
const updateLineMeta = db.prepare(`UPDATE production_lines SET name = ?, aliases_json = ?, updated_at = datetime('now') WHERE line_id = ?`);
const members = `SELECT m.line_id, m.user_id, m.role, m.created_at, m.updated_at, u.username
  FROM production_line_members m JOIN users u ON u.id = m.user_id WHERE m.line_id = ?`;
const listMembers = db.prepare(`${members} ORDER BY m.user_id`);
const getMemberView = db.prepare(`${members} AND m.user_id = ?`);
const deleteMember = db.prepare('DELETE FROM production_line_members WHERE line_id = ? AND user_id = ?');
const managerCount = db.prepare("SELECT COUNT(*) FROM production_line_members WHERE line_id = ? AND role = 'manage'").pluck();
const pendingBindings = db.prepare(`SELECT run_id, scene_name, status, created_at, owner_user_id, user_id
  FROM diagnostic_runs WHERE line_id IS NULL AND deleted_at IS NULL ORDER BY created_at DESC, run_id LIMIT ? OFFSET ?`);
const manualBinding = db.prepare('SELECT line_id FROM production_line_run_bindings WHERE run_id = ? ORDER BY id DESC LIMIT 1').pluck();
const updateBinding = db.prepare("UPDATE diagnostic_runs SET line_id = ?, updated_at = datetime('now') WHERE run_id = ?");
const auditBinding = db.prepare('INSERT INTO production_line_run_bindings (run_id, prior_line_id, line_id, actor_user_id) VALUES (?, ?, ?, ?)');
const listBindings = db.prepare(`SELECT run_id, prior_line_id, line_id, actor_user_id, created_at
  FROM production_line_run_bindings WHERE line_id = ? OR prior_line_id = ? ORDER BY id DESC LIMIT ? OFFSET ?`);

function lineName(value) {
  const name = typeof value === 'string' ? value.trim() : '';
  if (!name || !name.isWellFormed() || name.includes('\0')) fail(400, 'LINE_NAME_REQUIRED', 'name must be a non-empty string');
  if (name.length > NAME_MAX) fail(400, 'LINE_NAME_TOO_LONG', `name must be ≤ ${NAME_MAX} characters`);
  return name;
}

export const createLine = db.transaction((actor, { name } = {}) => {
  const { id } = requireActor(actor);
  const line_id = randomUUID();
  const clean = lineName(name);
  insertLine.run(line_id, clean, id);
  insertMember.run(line_id, id, 'manage');
  return { line_id, name: clean };
}).immediate;

export function requireLineAction(actor, lineId, action) {
  const { id } = requireActor(actor);
  if (typeof action !== 'string' || !Object.hasOwn(MEMBER_LEVEL, action)) {
    fail(400, 'LINE_ACTION_INVALID', 'action must be read, run, or manage');
  }
  if (typeof lineId !== 'string' || !UUID.test(lineId)) lineNotFound();
  const row = getLine.get(lineId);
  const role = getMembership.get(lineId, id);
  if (!row || !role) lineNotFound();
  if (MEMBER_LEVEL[role] < MEMBER_LEVEL[action]) fail(403, 'LINE_FORBIDDEN', `Line membership does not permit ${action}`);
  return lineView({ ...row, member_role: role });
}

// One ownership rule for knowledge: the tenancy owner is authoritative; an
// inconsistent historical user_id is a conflict, not a second route to access.
function ownershipConflict(run) {
  return run.user_id != null && run.owner_user_id != null && String(run.user_id) !== String(run.owner_user_id);
}

export function requireRunKnowledgeScope(actor, runId) {
  const { id } = requireActor(actor);
  const run = typeof runId === 'string' && stmts.getRunById.get(runId);
  if (!run || run.deleted_at || run.owner_user_id !== id || ownershipConflict(run)) runNotFound();
  if (run.line_id) requireLineAction(actor, run.line_id, 'read');
  return {
    run_id: run.run_id,
    line_id: run.line_id,
    owner_user_id: run.owner_user_id,
    knowledge_policy: run.line_id ? parseJson(run.knowledge_policy_json) : null,
    dataset_refs: run.line_id ? parseJson(run.dataset_refs_json) : null,
  };
}

export function listLines(actor) {
  const { id } = requireActor(actor);
  return listAccessible.all(id).map(lineView);
}

export const updateLine = db.transaction((actor, lineId, { name, aliases } = {}) => {
  const current = requireLineAction(actor, lineId, 'manage');
  const clean = name === undefined ? current.name : lineName(name);
  let nextAliases = current.aliases;
  if (aliases !== undefined) {
    if (!Array.isArray(aliases) || aliases.length > 50) {
      fail(400, 'LINE_ALIASES_INVALID', 'aliases must be an array of up to 50 display labels');
    }
    nextAliases = [...new Set(aliases.map(lineName))];
  }
  updateLineMeta.run(clean, JSON.stringify(nextAliases), lineId);
  return { line_id: lineId, name: clean, aliases: nextAliases };
}).immediate;

export function listLineMembers(actor, lineId) {
  requireLineAction(actor, lineId, 'manage');
  return listMembers.all(lineId);
}

function targetMemberId(userId) {
  const targetId = positiveId(userId);
  if (!targetId) fail(400, 'LINE_MEMBER_INVALID', 'userId must be a positive integer');
  return targetId;
}

function guardLastManager(lineId, userId) {
  if (getMembership.get(lineId, userId) === 'manage' && managerCount.get(lineId) <= 1) {
    fail(409, 'LINE_LAST_MANAGER', 'A production line must retain at least one manager');
  }
}

export const setLineMember = db.transaction((actor, lineId, userId, role) => {
  requireLineAction(actor, lineId, 'manage');
  const targetId = targetMemberId(userId);
  if (typeof role !== 'string' || !Object.hasOwn(MEMBER_LEVEL, role)) fail(400, 'LINE_ROLE_INVALID', 'role must be read, run, or manage');
  if (!stmts.getUserById.get(targetId)) fail(404, 'USER_NOT_FOUND', 'User not found');
  if (role !== 'manage') guardLastManager(lineId, targetId);
  insertMember.run(lineId, targetId, role);
  return getMemberView.get(lineId, targetId);
}).immediate;

export const removeLineMember = db.transaction((actor, lineId, userId) => {
  requireLineAction(actor, lineId, 'manage');
  const targetId = targetMemberId(userId);
  guardLastManager(lineId, targetId);
  const { changes } = deleteMember.run(lineId, targetId);
  return { line_id: lineId, user_id: targetId, removed: changes !== 0 };
}).immediate;

function page({ limit, offset } = {}) {
  const size = limit === undefined ? 50 : positiveId(limit);
  const start = offset === undefined || offset === '0' || offset === 0 ? 0 : positiveId(offset);
  if (size == null || start == null) fail(400, 'LINE_PAGE_INVALID', 'Invalid limit or offset');
  return [Math.min(size, 200), start];
}

export function listLegacyRuns(actor, options) {
  if (requireActor(actor).role !== 'admin') fail(403, 'FORBIDDEN', '需要角色: admin');
  return pendingBindings.all(...page(options)).map(({ user_id, owner_user_id, ...run }) => ({
    ...run,
    ownership: ownershipConflict({ user_id, owner_user_id }) ? 'conflict' : owner_user_id == null ? 'unknown' : 'identified',
    owner_user_id,
  }));
}

// Historical binding can only be confirmed by a manager on the destination,
// for their own run (or as a site admin). A correction also needs management
// of the previous line and only applies to a run originally bound by this flow.
export const bindLegacyRun = db.transaction((actor, lineId, runId) => {
  const user = requireActor(actor);
  requireLineAction(user, lineId, 'manage');
  const run = typeof runId === 'string' && stmts.getRunById.get(runId);
  if (!run || run.deleted_at || (run.owner_user_id !== user.id && user.role !== 'admin')) runNotFound();
  if (!TERMINAL.has(run.status)) fail(409, 'RUN_ACTIVE', 'Only a terminal run can be bound or corrected');
  if (ownershipConflict(run)) fail(409, 'RUN_OWNERSHIP_CONFLICT', 'Run ownership metadata conflicts');
  if (!run.owner_user_id || !stmts.getUserById.get(run.owner_user_id)) {
    fail(409, 'RUN_OWNERSHIP_UNKNOWN', 'Run owner cannot be verified');
  }
  if (!(MEMBER_LEVEL[getMembership.get(lineId, run.owner_user_id)] >= MEMBER_LEVEL.run)) {
    fail(409, 'RUN_OWNER_NOT_LINE_MEMBER', 'Run owner needs run access to the destination line');
  }
  if (run.line_id) {
    if (manualBinding.get(runId) !== run.line_id) fail(409, 'RUN_ALREADY_BOUND', 'Run already has an original production line');
    if (run.line_id === lineId) return { run_id: runId, line_id: lineId, already_bound: true };
    requireLineAction(user, run.line_id, 'manage');
  }
  updateBinding.run(lineId, runId);
  auditBinding.run(runId, run.line_id, lineId, user.id);
  return { run_id: runId, line_id: lineId, already_bound: false };
}).immediate;

export function listLineRunBindings(actor, lineId, options) {
  requireLineAction(actor, lineId, 'manage');
  return listBindings.all(lineId, lineId, ...page(options));
}

function versionRefs(value, code) {
  if (!Array.isArray(value) || value.length > MAX_REFS) fail(400, code, `At most ${MAX_REFS} version references are allowed`);
  return value.map((ref) => {
    const version = positiveId(ref?.version);
    if (!ref || typeof ref !== 'object' || Array.isArray(ref)
        || typeof ref.asset_id !== 'string' || !UUID.test(ref.asset_id) || !version
        || Object.keys(ref).some((key) => !['asset_id', 'version'].includes(key))) {
      fail(400, code, 'Each reference requires an asset_id UUID and a positive version');
    }
    return { asset_id: ref.asset_id, version };
  });
}

export function normalizeKnowledgeBinding(actor, lineId, knowledgePolicy, datasetRefs) {
  if (lineId === undefined || lineId === null) {
    if (knowledgePolicy !== undefined || datasetRefs !== undefined) {
      fail(400, 'LINE_REQUIRED', 'lineId is required when specifying knowledgePolicy or datasetRefs');
    }
    return { lineId: null, knowledgePolicy: null, datasetRefs: null };
  }
  requireLineAction(actor, lineId, 'run');
  const policy = knowledgePolicy === undefined ? DEFAULT_KNOWLEDGE_POLICY : knowledgePolicy;
  if (!policy || typeof policy !== 'object' || Array.isArray(policy)
      || !['on_demand', 'disabled'].includes(policy.mode)
      || typeof policy.own_line !== 'boolean'
      || Object.keys(policy).some((key) => !['mode', 'own_line', 'references'].includes(key))) {
    fail(400, 'KNOWLEDGE_POLICY_INVALID', 'knowledgePolicy requires mode, own_line, and references');
  }
  return {
    lineId,
    knowledgePolicy: {
      mode: policy.mode, own_line: policy.own_line,
      references: versionRefs(policy.references, 'KNOWLEDGE_REFERENCE_INVALID'),
    },
    datasetRefs: versionRefs(datasetRefs === undefined ? [] : datasetRefs, 'DATASET_REFERENCE_INVALID'),
  };
}
