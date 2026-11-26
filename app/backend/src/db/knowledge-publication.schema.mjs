// Append-only migration callback. The migration runner owns the transaction and version stamp.
export function migrateKnowledgePublication(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS knowledge_assets (
      asset_id TEXT PRIMARY KEY NOT NULL,
      line_id TEXT NOT NULL REFERENCES production_lines(line_id),
      kind TEXT NOT NULL CHECK (kind IN ('experience', 'memory_excerpt', 'dataset')),
      created_by_user_id INTEGER NOT NULL REFERENCES users(id),
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- The version key is the dataset's object reference. Store only a separately
    -- submitted snapshot, never a file location or a source run identifier.
    CREATE TABLE IF NOT EXISTS knowledge_asset_versions (
      asset_id TEXT NOT NULL REFERENCES knowledge_assets(asset_id),
      version INTEGER NOT NULL CHECK (version > 0),
      state TEXT NOT NULL DEFAULT 'draft' CHECK (state IN ('draft', 'published', 'withdrawn')),
      visibility TEXT NOT NULL DEFAULT 'private' CHECK (visibility IN ('private', 'catalog')),
      public_read INTEGER NOT NULL DEFAULT 0 CHECK (public_read IN (0, 1)),
      title TEXT NOT NULL,
      summary TEXT NOT NULL,
      content TEXT,
      applicability TEXT,
      dataset_bytes BLOB,
      sha256 TEXT,
      fields_json TEXT,
      use_restrictions TEXT,
      created_by_user_id INTEGER NOT NULL REFERENCES users(id),
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      published_at TEXT,
      withdrawn_at TEXT,
      PRIMARY KEY (asset_id, version),
      CHECK (public_read = 0 OR visibility = 'catalog'),
      CHECK (
        (state = 'draft' AND visibility = 'private' AND published_at IS NULL AND withdrawn_at IS NULL)
        OR (state = 'published' AND published_at IS NOT NULL AND withdrawn_at IS NULL)
        OR (state = 'withdrawn' AND published_at IS NOT NULL AND withdrawn_at IS NOT NULL)
      ),
      CHECK (
        (content IS NOT NULL AND applicability IS NOT NULL AND dataset_bytes IS NULL
          AND sha256 IS NULL AND fields_json IS NULL AND use_restrictions IS NULL)
        OR
        (content IS NULL AND applicability IS NULL AND typeof(dataset_bytes) = 'blob'
          AND length(dataset_bytes) BETWEEN 1 AND 1048576 AND sha256 IS NOT NULL AND length(sha256) = 64
          AND fields_json IS NOT NULL AND use_restrictions IS NOT NULL)
      )
    );

    CREATE TABLE IF NOT EXISTS knowledge_asset_grants (
      asset_id TEXT NOT NULL,
      version INTEGER NOT NULL,
      user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      right TEXT NOT NULL CHECK (right IN ('read', 'reuse', 'download', 'analyze')),
      PRIMARY KEY (asset_id, version, user_id, right),
      FOREIGN KEY (asset_id, version) REFERENCES knowledge_asset_versions(asset_id, version)
    );

    CREATE TABLE IF NOT EXISTS knowledge_publication_audit (
      id INTEGER PRIMARY KEY,
      asset_id TEXT NOT NULL,
      version INTEGER NOT NULL,
      actor_user_id INTEGER NOT NULL,
      action TEXT NOT NULL CHECK (action IN ('draft_created', 'published', 'withdrawn', 'grant_set', 'grant_revoked')),
      target_user_id INTEGER,
      change_json TEXT NOT NULL,
      created_at TEXT NOT NULL DEFAULT (datetime('now')),
      FOREIGN KEY (asset_id, version) REFERENCES knowledge_asset_versions(asset_id, version)
    );

    CREATE INDEX IF NOT EXISTS idx_knowledge_versions_catalog
      ON knowledge_asset_versions(published_at DESC, asset_id DESC, version DESC) WHERE state = 'published';
    CREATE INDEX IF NOT EXISTS idx_knowledge_publication_audit_ref
      ON knowledge_publication_audit(asset_id, version, id);

    CREATE TRIGGER IF NOT EXISTS knowledge_assets_immutable
      BEFORE UPDATE ON knowledge_assets
      BEGIN SELECT RAISE(ABORT, 'knowledge asset identity is immutable'); END;
    CREATE TRIGGER IF NOT EXISTS knowledge_version_payload_immutable
      BEFORE UPDATE OF asset_id, version, title, summary, content, applicability, dataset_bytes,
        sha256, fields_json, use_restrictions, created_by_user_id, created_at ON knowledge_asset_versions
      BEGIN SELECT RAISE(ABORT, 'knowledge version payload is immutable'); END;
    CREATE TRIGGER IF NOT EXISTS knowledge_version_no_delete
      BEFORE DELETE ON knowledge_asset_versions
      BEGIN SELECT RAISE(ABORT, 'knowledge version is immutable'); END;
    CREATE TRIGGER IF NOT EXISTS knowledge_version_transition
      BEFORE UPDATE OF state, visibility, public_read, published_at, withdrawn_at ON knowledge_asset_versions
      WHEN NOT (
        (OLD.state = 'draft' AND NEW.state = 'published')
        OR (OLD.state = 'published' AND NEW.state = 'withdrawn'
          AND NEW.visibility = OLD.visibility AND NEW.public_read = OLD.public_read AND NEW.published_at = OLD.published_at)
      )
      BEGIN SELECT RAISE(ABORT, 'invalid knowledge version transition'); END;
  `);
}
