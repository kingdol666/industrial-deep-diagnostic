// Ontology Routes — asset store browsing (optimization plan v4 / L1)

import { Router } from 'express';
import { listStore } from '../../../../.claude/shared/scripts/ontology_store.mjs';

const router = Router();

// GET /api/ontology/store — list all scenes/versions in the ontology asset store
router.get('/store', (_req, res) => {
  try {
    res.json({ success: true, data: listStore() });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

export default router;
