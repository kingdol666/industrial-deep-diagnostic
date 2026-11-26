import { test } from 'node:test';
import assert from 'node:assert/strict';
import Database from 'better-sqlite3';
import { migrateKnowledgeRetrieval } from '../src/db/knowledge-retrieval.schema.mjs';

 test('completion lineage advances even when a run completes twice in the same second; the FTS projection is rebuildable', () => {
  const db = new Database(':memory:');
  try {
    db.exec(`CREATE TABLE diagnostic_runs(run_id TEXT PRIMARY KEY, status TEXT, completed_at TEXT);
      CREATE TABLE production_lines(line_id TEXT PRIMARY KEY);
      CREATE TABLE diagnosis_review_revisions(run_id TEXT, revision INTEGER);
      INSERT INTO diagnostic_runs VALUES('run1','completed','2026-11-26');
      INSERT INTO production_lines VALUES('line1');`);
    migrateKnowledgeRetrieval(db);
    const complete = db.prepare("UPDATE diagnostic_runs SET completed_at = '2026-11-26' WHERE run_id = 'run1'");
    complete.run();
    complete.run();
    assert.equal(db.prepare("SELECT completion_revision FROM diagnostic_runs WHERE run_id = 'run1'").pluck().get(), 2);
    db.prepare('INSERT INTO knowledge_observations(run_id,line_id,completion_revision,finding_id,subject,detail) VALUES(?,?,?,?,?,?)')
      .run('run1', 'line1', 2, 'finding1', '测温校准', '检查温度漂移');
    const search = db.prepare('SELECT subject FROM knowledge_observation_fts WHERE knowledge_observation_fts MATCH ?').pluck();
    assert.deepEqual(search.all('"测温校"'), ['测温校准']);
    db.exec("INSERT INTO knowledge_observation_fts(knowledge_observation_fts) VALUES ('rebuild')");
    assert.deepEqual(search.all('"测温校"'), ['测温校准']);
    db.exec('DELETE FROM knowledge_observations');
    assert.deepEqual(search.all('"测温校"'), []);
  } finally { db.close(); }
});
