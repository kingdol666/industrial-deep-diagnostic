export function migrateKnowledgeRetrieval(db) {
  db.exec(`
    ALTER TABLE diagnostic_runs ADD COLUMN completion_revision INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE diagnosis_review_revisions ADD COLUMN source_completion_revision INTEGER;
    CREATE TRIGGER knowledge_track_completion AFTER UPDATE OF completed_at ON diagnostic_runs
    WHEN NEW.status = 'completed' AND NEW.completed_at IS NOT NULL
    BEGIN
      UPDATE diagnostic_runs SET completion_revision = OLD.completion_revision + 1 WHERE run_id = NEW.run_id;
    END;

    CREATE TABLE knowledge_observations (
      id INTEGER PRIMARY KEY,
      run_id TEXT NOT NULL REFERENCES diagnostic_runs(run_id) ON DELETE CASCADE,
      line_id TEXT NOT NULL REFERENCES production_lines(line_id),
      completion_revision INTEGER NOT NULL,
      finding_id TEXT NOT NULL,
      subject TEXT NOT NULL,
      detail TEXT NOT NULL,
      UNIQUE(run_id, completion_revision, finding_id)
    );
    CREATE INDEX knowledge_observations_scope ON knowledge_observations(line_id, run_id, completion_revision);
    CREATE VIRTUAL TABLE knowledge_observation_fts USING fts5(subject, detail,
      content='knowledge_observations', content_rowid='id', tokenize='trigram');
    CREATE TRIGGER knowledge_index_insert AFTER INSERT ON knowledge_observations BEGIN
      INSERT INTO knowledge_observation_fts(rowid, subject, detail) VALUES (NEW.id, NEW.subject, NEW.detail);
    END;
    CREATE TRIGGER knowledge_index_delete AFTER DELETE ON knowledge_observations BEGIN
      INSERT INTO knowledge_observation_fts(knowledge_observation_fts, rowid, subject, detail)
        VALUES ('delete', OLD.id, OLD.subject, OLD.detail);
    END;

    CREATE TABLE knowledge_retrievals (
      retrieval_id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL REFERENCES diagnostic_runs(run_id) ON DELETE CASCADE,
      actor_user_id INTEGER NOT NULL,
      attempt_id TEXT,
      action TEXT NOT NULL CHECK(action IN ('search', 'get')),
      outcome TEXT NOT NULL,
      item_count INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
    );
    CREATE INDEX knowledge_retrieval_run ON knowledge_retrievals(run_id, created_at);
    CREATE INDEX knowledge_attempt_budget ON knowledge_retrievals(attempt_id) WHERE attempt_id IS NOT NULL;
    CREATE TABLE knowledge_retrieval_refs (
      retrieval_id TEXT NOT NULL REFERENCES knowledge_retrievals(retrieval_id) ON DELETE CASCADE,
      ref_id TEXT NOT NULL,
      source_kind TEXT NOT NULL,
      source_id TEXT NOT NULL,
      source_version TEXT NOT NULL,
      PRIMARY KEY(retrieval_id, ref_id)
    );
    CREATE INDEX knowledge_lookup_ref ON knowledge_retrieval_refs(ref_id);
  `);
}
