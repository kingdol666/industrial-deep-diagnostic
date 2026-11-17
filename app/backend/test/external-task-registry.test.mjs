// External task registry — the task_id map must not grow without bound.
// Terminal entries are pruned on every task creation (24h TTL) and the map is
// hard-capped at 200 by evicting the OLDEST terminal entries first. Live
// (accepted/queued/running) entries are never evicted — a caller polling a
// running task must always find it.
//
// The cap test runs first against the freshly loaded module (empty registry);
// both tests stay correct if generated task ids ever collide (assertions are
// identity- and relation-based, never raw counts).
import { test, describe } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

const workDir = mkdtempSync(join(tmpdir(), 'idd-task-reg-'));
process.env.DATABASE_PATH = join(workDir, 'tasks.db');

const ext = await import('../src/services/external.service.mjs');

process.on('exit', () => {
  try { rmSync(workDir, { recursive: true, force: true }); } catch { /* windows lock */ }
});

const TASK_MAX = 200;

function terminalStamp(offsetMs) {
  return new Date(Date.now() + offsetMs).toISOString();
}

/**
 * Empty the registry via the public surface: every entry is forced terminal
 * and backdated past the TTL, then pruned. Tests then start from a known size
 * 0 instead of inheriting the previous test's leftovers.
 */
function drainRegistry() {
  for (const t of ext.listTaskEntries()) {
    const entry = ext.getTaskEntry(t.task_id);
    if (entry) Object.assign(entry, { status: 'completed', finished_at: terminalStamp(-30 * 3600 * 1000) });
  }
  ext.evictStaleTasks();
}

describe('task registry — hard cap', () => {
  test('cap 200 evicts the oldest terminal entries first and never live ones', () => {
    drainRegistry();
    assert.equal(ext.taskRegistrySize(), 0);

    const base = Date.now() - 60_000;
    // Three terminal entries, oldest first.
    const terminal = [0, 1, 2].map((i) => {
      const t = ext.createTask(`cap-term-${i}`, { intent: 'deep-diagnosis', harness: 'mock' });
      Object.assign(ext.getTaskEntry(t.task_id), {
        status: 'completed',
        finished_at: new Date(base + i * 1000).toISOString(),
      });
      return t;
    });
    assert.equal(ext.taskRegistrySize(), 3);

    // Fill past the cap: the two oldest terminal entries must be evicted.
    const liveIds = new Set();
    for (let i = 0; i < TASK_MAX - 1; i++) {
      liveIds.add(ext.createTask(`cap-live-${i}`, { intent: 'deep-diagnosis', harness: 'mock' }).task_id);
    }
    assert.ok(ext.taskRegistrySize() <= TASK_MAX, `cap exceeded: ${ext.taskRegistrySize()}`);

    const present = (id, prefix) => {
      const e = ext.getTaskEntry(id);
      return !!e && String(e.run_id).startsWith(prefix);
    };
    assert.equal(present(terminal[0].task_id, 'cap-term-'), false, 'oldest terminal evicted first');
    assert.equal(present(terminal[1].task_id, 'cap-term-'), false, 'second oldest terminal evicted next');
    assert.equal(present(terminal[2].task_id, 'cap-term-'), true, 'newest terminal kept');

    // Every live entry is still there (non-terminal is never evictable).
    for (const id of liveIds) {
      assert.ok(present(id, 'cap-live-'), `live task evicted: ${id}`);
    }

    // One more insertion evicts the last terminal entry, not a live one.
    ext.createTask('cap-live-final', { intent: 'deep-diagnosis', harness: 'mock' });
    assert.equal(present(terminal[2].task_id, 'cap-term-'), false, 'last terminal evicted');
    assert.ok(ext.taskRegistrySize() <= TASK_MAX);
  });
});

describe('task registry — terminal TTL', () => {
  test('prunes terminal tasks older than 24h, keeps fresh and live ones', () => {
    drainRegistry();
    const stale = ext.createTask('ttl-stale', { intent: 'deep-diagnosis', harness: 'mock' });
    const freshDone = ext.createTask('ttl-fresh', { intent: 'deep-diagnosis', harness: 'mock' });
    const live = ext.createTask('ttl-live', { intent: 'deep-diagnosis', harness: 'mock' });
    Object.assign(ext.getTaskEntry(stale.task_id), { status: 'completed', finished_at: terminalStamp(-25 * 3600 * 1000) });
    Object.assign(ext.getTaskEntry(freshDone.task_id), { status: 'failed', finished_at: terminalStamp(0) });

    ext.evictStaleTasks();
    assert.equal(ext.getTaskEntry(stale.task_id), null, 'stale terminal task pruned');
    assert.ok(ext.getTaskEntry(freshDone.task_id), 'recent terminal task kept');
    assert.ok(ext.getTaskEntry(live.task_id), 'live task kept');
    assert.equal(ext.getTaskEntry(live.task_id).status, 'accepted');
  });

  test('task creation itself prunes stale terminal entries', () => {
    drainRegistry();
    const stale = ext.createTask('ttl-stale-2', { intent: 'deep-diagnosis', harness: 'mock' });
    Object.assign(ext.getTaskEntry(stale.task_id), { status: 'stopped', finished_at: terminalStamp(-48 * 3600 * 1000) });

    const fresh = ext.createTask('ttl-trigger', { intent: 'deep-diagnosis', harness: 'mock' });
    assert.equal(ext.getTaskEntry(stale.task_id), null);
    assert.ok(ext.getTaskEntry(fresh.task_id));
  });
});
