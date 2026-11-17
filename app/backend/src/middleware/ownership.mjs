// Ownership helpers (P0-6 multi-tenancy) — the single source of the
// "who may see / administer this row" contract. Another wave consumes these to
// add ownership filtering to runs, chats, folders and logs; keeping the policy
// here means every consumer answers the same question the same way.
//
// Contract:
//   - Rows carry `owner_user_id` (INTEGER, nullable — see migrations v3).
//   - NULL owner = legacy/unowned row → visible and administrable to admins only.
//   - Admin sees everything (own rows, other users' rows, unowned rows).
//   - A regular user sees exactly their own rows.
//   - An unauthenticated caller sees nothing.
//
// Usage (listing — one clause, params spread in order):
//   const { clause, params } = applyOwnerScope(req.user, { alias: 'r' });
//   db.prepare(`SELECT * FROM diagnostic_runs r WHERE ${clause} ORDER BY …`).all(...params);
//
// Usage (single row):
//   if (!canAccessOwner(req.user, row.owner_user_id)) return res.status(404)…

export const OWNER_COLUMN = 'owner_user_id';

/** True when the user is an administrator (role === 'admin'). */
export function isAdmin(user) {
  return !!user && user.role === 'admin';
}

/**
 * May `user` access a row owned by `ownerId`?
 * own OR admin OR (ownerId === NULL && admin).
 */
export function canAccessOwner(user, ownerId) {
  if (!user || user.id === undefined || user.id === null) return false;
  if (isAdmin(user)) return true;
  if (ownerId === undefined || ownerId === null) return false; // unowned rows are admin-only
  return Number(ownerId) === Number(user.id);
}

/** Scope clause matching every row (admins). */
export const OWNER_SCOPE_ALL = Object.freeze({ clause: '1=1', params: [] });
/** Scope clause matching no row (unauthenticated callers). */
export const OWNER_SCOPE_NONE = Object.freeze({ clause: '1=0', params: [] });

/**
 * Build the SQL fragment restricting a query to the rows `user` may see.
 *
 * @param {{id:number, role:string}|null|undefined} user
 * @param {{alias?:string}} [opts] table alias used in the query (`''` → no prefix)
 * @returns {{clause:string, params:Array<number>}} bind `clause` after WHERE and spread `params`
 */
export function applyOwnerScope(user, { alias = 't' } = {}) {
  if (isAdmin(user)) return { clause: OWNER_SCOPE_ALL.clause, params: [] };
  if (!user || user.id === undefined || user.id === null) {
    return { clause: OWNER_SCOPE_NONE.clause, params: [] };
  }
  const column = alias ? `${alias}.${OWNER_COLUMN}` : OWNER_COLUMN;
  return { clause: `${column} = ?`, params: [user.id] };
}

/**
 * Convenience: the ownership column expression for a given alias
 * (`ownerColumn('r')` → `'r.owner_user_id'`), for callers that need the raw
 * column rather than a scope clause.
 */
export function ownerColumn(alias = '') {
  return alias ? `${alias}.${OWNER_COLUMN}` : OWNER_COLUMN;
}
