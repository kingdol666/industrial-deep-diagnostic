import { createHash, randomUUID } from 'node:crypto';
import { db } from '../db/database.mjs';
import { requireLineAction } from './production-line.service.mjs';

const KINDS = new Set(['experience', 'memory_excerpt', 'dataset']);
const TEXT_RIGHTS = ['read', 'reuse'];
const DATASET_RIGHTS = ['read', 'download', 'analyze'];
const MAX_DATASET_BYTES = 1024 * 1024;
const MAX_FIELDS = 128;
const ASSET_ID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const SQLITE_TIMESTAMP = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/;
const DIGITS = /^[1-9]\d*$/;

export class KnowledgePublicationError extends Error {
  constructor(status, code, message) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function bad(message) { throw new KnowledgePublicationError(400, 'KNOWLEDGE_INVALID_INPUT', message); }
function missing() { throw new KnowledgePublicationError(404, 'KNOWLEDGE_VERSION_NOT_FOUND', '知识版本不存在或不可访问'); }
function invalidState() { throw new KnowledgePublicationError(409, 'KNOWLEDGE_INVALID_STATE', '知识版本当前状态不允许此操作'); }

function authenticated(actor) {
  const user = Number.isSafeInteger(actor?.id) && db.prepare('SELECT id, role FROM users WHERE id = ?').get(actor.id);
  if (!user) throw new KnowledgePublicationError(401, 'AUTH_REQUIRED', '需要认证');
  return user;
}

function curator(actor) {
  const user = authenticated(actor);
  if (actor.auth_type !== 'session') {
    throw new KnowledgePublicationError(403, 'KNOWLEDGE_SESSION_REQUIRED', '发布管理需要登录会话');
  }
  return user;
}

function onlyFields(value, allowed) {
  return value != null && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).every((key) => allowed.includes(key));
}

function numberId(value) {
  if (typeof value === 'string' && DIGITS.test(value)) value = Number(value);
  return Number.isSafeInteger(value) && value > 0 ? value : null;
}

function assetId(value) {
  if (typeof value !== 'string' || !ASSET_ID.test(value)) missing();
  return value;
}

function strictRef(ref) {
  if (!onlyFields(ref, ['asset_id', 'version']) || !numberId(ref.version)) missing();
  return { asset_id: assetId(ref.asset_id), version: numberId(ref.version) };
}

function boundedText(value, max, field, optional = false) {
  const clean = typeof value === 'string' && value.isWellFormed() ? value.trim() : null;
  if (optional && value === undefined) return '';
  if (clean === null || (!optional && !clean) || clean.length > max || clean.includes('\0')) {
    bad(`${field} 必须为不超过 ${max} 字符的有效文本`);
  }
  return clean;
}

// Validate the exact uploaded representation without rewriting it. A strict,
// bounded comma/quote parser also prevents inconsistent field descriptions and
// rejects formula-like cells before offering a spreadsheet-compatible download.
function validateCsv(csv, fields) {
  const fail = () => bad('csv 必须是与 fields 匹配、无公式的 UTF-8 逗号分隔表格，至少一行数据，最大 1 MiB');
  if (typeof csv !== 'string' || csv.length > MAX_DATASET_BYTES || !csv.isWellFormed()
      || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(csv) || Buffer.byteLength(csv) > MAX_DATASET_BYTES) fail();
  let i = csv.startsWith('\uFEFF') ? 1 : 0;
  let row = 0;
  while (i < csv.length) {
    let col = 0;
    let separator;
    do {
      const quoted = csv[i] === '"';
      let field;
      if (quoted) {
        const start = ++i;
        for (;;) {
          i = csv.indexOf('"', i);
          if (i < 0) fail();
          if (csv[i + 1] !== '"') break;
          i += 2;
        }
        field = csv.slice(start, i++).replaceAll('""', '"');
      } else {
        const start = i;
        while (i < csv.length && !',\r\n'.includes(csv[i])) {
          if (csv[i++] === '"') fail();
        }
        field = csv.slice(start, i);
      }
      const clean = field.trim();
      if (col >= fields.length || (row === 0 && field !== fields[col].name)) fail();
      if (/^[\t\r\n]/.test(field) || (/^[=+\-@＝＋－＠]/.test(clean) && !/^[+-](?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(clean))) fail();
      col++;
      separator = csv[i++];
    } while (separator === ',');
    if (col !== fields.length || (separator !== undefined && separator !== '\r' && separator !== '\n')) fail();
    if (separator === '\r' && csv[i++] !== '\n') fail();
    row++;
  }
  if (row < 2) fail();
  return Buffer.from(csv, 'utf8');
}

function parseSnapshot(kind, body, initial) {
  const dataset = kind === 'dataset';
  const extras = dataset ? ['csv', 'fields', 'use_restrictions'] : ['content', 'applicability'];
  if (!onlyFields(body, ['title', 'summary', ...extras, ...(initial ? ['kind'] : [])])) bad('不支持的快照字段');
  const title = boundedText(body.title, 120, 'title');
  const summary = boundedText(body.summary, 240, 'summary');
  const payload = { title, summary, content: null, applicability: null, bytes: null, sha256: null, fields_json: null, use_restrictions: null };
  if (!dataset) {
    payload.content = boundedText(body.content, 1600, 'content');
    payload.applicability = boundedText(body.applicability, 240, 'applicability', true);
    return payload;
  }
  if (!Array.isArray(body.fields) || body.fields.length < 1 || body.fields.length > MAX_FIELDS) bad('fields 必须为 1–128 项的字段说明');
  const fields = body.fields.map((field) => {
    if (!onlyFields(field, ['name', 'description'])) bad('fields 仅接受 name 和 description');
    return { name: boundedText(field.name, 120, 'name'), description: boundedText(field.description, 500, 'description') };
  });
  if (new Set(fields.map((field) => field.name)).size !== fields.length) bad('fields 不允许重名');
  payload.bytes = validateCsv(body.csv, fields);
  payload.sha256 = sha256(payload.bytes);
  payload.fields_json = JSON.stringify(fields);
  payload.use_restrictions = boundedText(body.use_restrictions, 1000, 'use_restrictions');
  return payload;
}

function sha256(bytes) { return createHash('sha256').update(bytes).digest('hex'); }

function brief(row) {
  const { asset_id, version, kind, title, summary, published_at } = row;
  return { asset_id, version, kind, title, summary, published_at };
}

function detail(row) {
  if (row.kind !== 'dataset') return { ...brief(row), content: row.content, applicability: row.applicability };
  return {
    ...brief(row), sha256: row.sha256, size_bytes: row.size_bytes, mime_type: 'text/csv',
    fields: JSON.parse(row.fields_json), use_restrictions: row.use_restrictions,
  };
}

function manageAsset(user, id) {
  const asset = db.prepare('SELECT asset_id, line_id, kind FROM knowledge_assets WHERE asset_id = ?').get(assetId(id));
  if (!asset) missing();
  try {
    requireLineAction(user, asset.line_id, 'manage');
  } catch (err) {
    if (err.status === 403 || err.status === 404) missing();
    throw err;
  }
  return asset;
}

function audit(user, ref, action, change = {}, target = null) {
  db.prepare(`INSERT INTO knowledge_publication_audit (asset_id, version, actor_user_id, action, target_user_id, change_json)
    VALUES (?, ?, ?, ?, ?, ?)`).run(ref.asset_id, ref.version, user.id, action, target, JSON.stringify(change));
}

function transaction(work) { return db.transaction(work).immediate(); }

function createDraft(user, asset, version, payload) {
  const draft = { asset_id: asset.asset_id, version };
  db.prepare(`INSERT INTO knowledge_asset_versions
    (asset_id, version, title, summary, content, applicability, dataset_bytes, sha256, fields_json, use_restrictions, created_by_user_id)
    VALUES (@asset_id,@version,@title,@summary,@content,@applicability,@bytes,@sha256,@fields_json,@use_restrictions,@created_by)`)
    .run({ ...draft, ...payload, created_by: user.id });
  audit(user, draft, 'draft_created');
  return { ...draft, kind: asset.kind, state: 'draft', title: payload.title, summary: payload.summary };
}

export function createAsset(actor, lineId, body) {
  return transaction(() => {
    const user = curator(actor);
    requireLineAction(user, lineId, 'manage');
    if (!KINDS.has(body?.kind)) bad('kind 不受支持');
    const payload = parseSnapshot(body.kind, body, true);
    const asset = { asset_id: randomUUID(), kind: body.kind };
    db.prepare('INSERT INTO knowledge_assets (asset_id,line_id,kind,created_by_user_id) VALUES (?,?,?,?)')
      .run(asset.asset_id, lineId, asset.kind, user.id);
    return createDraft(user, asset, 1, payload);
  });
}

export function createVersion(actor, id, body) {
  return transaction(() => {
    const user = curator(actor);
    const asset = manageAsset(user, id);
    const payload = parseSnapshot(asset.kind, body, false);
    const { nextVersion } = db.prepare('SELECT MAX(version) + 1 AS nextVersion FROM knowledge_asset_versions WHERE asset_id = ?').get(id);
    return createDraft(user, asset, nextVersion, payload);
  });
}

function forManagedVersion(actor, versionRef, expectedState, action) {
  return transaction(() => {
    const user = curator(actor);
    const ref = strictRef(versionRef);
    const asset = manageAsset(user, ref.asset_id);
    const row = db.prepare('SELECT state FROM knowledge_asset_versions WHERE asset_id = @asset_id AND version = @version').get(ref);
    if (!row) missing();
    if (row.state !== expectedState) invalidState();
    return action(user, ref, asset.kind);
  });
}

export function publishVersion(actor, versionRef, body) {
  return forManagedVersion(actor, versionRef, 'draft', (user, ref, kind) => {
    if (!onlyFields(body, ['confirmed', 'visibility', 'public_read']) || body.confirmed !== true) bad('发布需要明确确认脱敏和可共享范围');
    const { visibility = 'private', public_read = false } = body;
    if (!['private', 'catalog'].includes(visibility) || typeof public_read !== 'boolean' || (public_read && visibility !== 'catalog')) {
      bad('visibility 或 public_read 不受支持');
    }
    const { published_at } = db.prepare(`UPDATE knowledge_asset_versions
      SET state = 'published', visibility = @visibility, public_read = @publicRead, published_at = datetime('now')
      WHERE asset_id = @asset_id AND version = @version RETURNING published_at`).get({ ...ref, visibility, publicRead: Number(public_read) });
    audit(user, ref, 'published', { visibility, public_read });
    return { ...ref, kind, state: 'published', visibility, public_read, published_at };
  });
}

export function withdrawVersion(actor, versionRef) {
  return forManagedVersion(actor, versionRef, 'published', (user, ref, kind) => {
    const { withdrawn_at } = db.prepare(`UPDATE knowledge_asset_versions SET state = 'withdrawn', withdrawn_at = datetime('now')
      WHERE asset_id = @asset_id AND version = @version RETURNING withdrawn_at`).get(ref);
    audit(user, ref, 'withdrawn');
    return { ...ref, kind, state: 'withdrawn', withdrawn_at };
  });
}

function changeGrant(actor, versionRef, grantee, body, revoke) {
  return forManagedVersion(actor, versionRef, 'published', (user, ref, kind) => {
    const user_id = numberId(grantee);
    if (!user_id) bad('userId 须为有效用户 ID');
    if (!revoke && !db.prepare('SELECT id FROM users WHERE id = ?').get(user_id)) {
      throw new KnowledgePublicationError(404, 'KNOWLEDGE_GRANTEE_NOT_FOUND', '授权目标用户不存在');
    }
    const allowed = kind === 'dataset' ? DATASET_RIGHTS : TEXT_RIGHTS;
    if (!revoke && (!onlyFields(body, ['rights']) || !Array.isArray(body.rights) || body.rights.length < 1
        || body.rights.length > allowed.length || new Set(body.rights).size !== body.rights.length
        || !body.rights.every((right) => allowed.includes(right)))) bad('rights 必须为该类型支持的非空权限列表');
    const target = { ...ref, user_id };
    const rights = revoke ? [] : [...body.rights].sort();
    const previous = db.prepare(`SELECT right FROM knowledge_asset_grants
      WHERE asset_id = @asset_id AND version = @version AND user_id = @user_id ORDER BY right`).pluck().all(target);
    if (previous.length !== rights.length || previous.some((right, i) => right !== rights[i])) {
      db.prepare('DELETE FROM knowledge_asset_grants WHERE asset_id = @asset_id AND version = @version AND user_id = @user_id').run(target);
      const insert = db.prepare('INSERT INTO knowledge_asset_grants (asset_id,version,user_id,right) VALUES (@asset_id,@version,@user_id,@right)');
      for (const right of rights) insert.run({ ...target, right });
      audit(user, ref, revoke ? 'grant_revoked' : 'grant_set', { previous, rights }, user_id);
    }
    return { ...target, rights };
  });
}

export function setVersionGrant(actor, ref, userId, body) { return changeGrant(actor, ref, userId, body, false); }
export function revokeVersionGrant(actor, ref, userId) { return changeGrant(actor, ref, userId, undefined, true); }

const BRIEF_COLUMNS = 'v.asset_id, v.version, a.kind, v.title, v.summary, v.published_at';
const GRANT_EXISTS = `EXISTS (SELECT 1 FROM knowledge_asset_grants AS g
  WHERE g.asset_id = v.asset_id AND g.version = v.version AND g.user_id = @userId AND g.right = @right)`;

function authorizedVersion(actor, versionRef, right, includeBytes = false) {
  const user = authenticated(actor);
  const ref = strictRef(versionRef);
  if (!TEXT_RIGHTS.includes(right) && !DATASET_RIGHTS.includes(right)) bad('不支持的知识访问权限');
  const row = db.prepare(`SELECT ${BRIEF_COLUMNS}, v.content, v.applicability, v.sha256, v.fields_json,
      v.use_restrictions, length(v.dataset_bytes) AS size_bytes ${includeBytes ? ', v.dataset_bytes' : ''}
    FROM knowledge_asset_versions AS v JOIN knowledge_assets AS a USING (asset_id)
    WHERE v.asset_id = @asset_id AND v.version = @version AND v.state = 'published'
      AND (@right = 'read' OR (a.kind <> 'dataset' AND @right = 'reuse')
        OR (a.kind = 'dataset' AND @right IN ('download', 'analyze')))
      AND ((@right = 'read' AND v.public_read = 1) OR ${GRANT_EXISTS})`)
    .get({ ...ref, userId: user.id, right });
  if (!row) missing();
  return row;
}

/** A published version is never an authorization to read an underlying line/run. */
export function getPublishedVersion(actor, versionRef, right) {
  return detail(authorizedVersion(actor, versionRef, right));
}

function datasetSnapshot(actor, versionRef, right) {
  const row = authorizedVersion(actor, versionRef, right, true);
  if (!Buffer.isBuffer(row.dataset_bytes) || sha256(row.dataset_bytes) !== row.sha256) {
    throw new KnowledgePublicationError(409, 'KNOWLEDGE_DATASET_UNAVAILABLE', '数据集快照不可用');
  }
  return { bytes: row.dataset_bytes, metadata: detail(row) };
}

export function downloadDataset(actor, versionRef) { return datasetSnapshot(actor, versionRef, 'download'); }

/** Server-owned target scope only. Returns bytes, not a path; no engine dispatch. */
export function stageComparisonDataset(scope, versionRef) {
  return db.transaction(() => {
    const user = authenticated(scope?.actor);
    requireLineAction(user, scope.line_id, 'run');
    return datasetSnapshot(user, versionRef, 'analyze');
  })();
}

function decodeCursor(cursor) {
  if (cursor === undefined) return { at: null, id: null, version: null };
  if (typeof cursor !== 'string' || !/^[a-zA-Z0-9_-]{1,128}$/.test(cursor)) bad('cursor 无效');
  const [at, id, rawVersion, extra] = Buffer.from(cursor, 'base64url').toString('utf8').split('|');
  const version = numberId(rawVersion);
  if (!SQLITE_TIMESTAMP.test(at) || !ASSET_ID.test(id || '') || !version || extra !== undefined) bad('cursor 无效');
  return { at, id, version };
}

export function listCatalog(actor, options = {}) {
  const user = authenticated(actor);
  const { kind, q, cursor, limit = 20 } = options;
  if (kind !== undefined && !KINDS.has(kind)) bad('kind 不受支持');
  const keyword = boundedText(q, 120, 'q', true);
  const pageSize = numberId(limit);
  if (!pageSize || pageSize > 50) bad('limit 须为 1–50 的整数');
  const rows = db.prepare(`SELECT ${BRIEF_COLUMNS}
    FROM knowledge_asset_versions AS v JOIN knowledge_assets AS a USING (asset_id)
    WHERE v.state = 'published' AND (v.visibility = 'catalog' OR ${GRANT_EXISTS})
      AND (@kind IS NULL OR a.kind = @kind)
      AND (@q = '' OR instr(lower(v.title), lower(@q)) > 0 OR instr(lower(v.summary), lower(@q)) > 0)
      AND (@at IS NULL OR (v.published_at, v.asset_id, v.version) < (@at, @id, @version))
    ORDER BY v.published_at DESC, v.asset_id DESC, v.version DESC LIMIT @limit`)
    .all({ userId: user.id, right: 'read', kind: kind ?? null, q: keyword, ...decodeCursor(cursor), limit: pageSize + 1 });
  const last = rows.length > pageSize ? rows[pageSize - 1] : null;
  return {
    items: rows.slice(0, pageSize).map(brief),
    next_cursor: last ? Buffer.from(`${last.published_at}|${last.asset_id}|${last.version}`).toString('base64url') : null,
  };
}
