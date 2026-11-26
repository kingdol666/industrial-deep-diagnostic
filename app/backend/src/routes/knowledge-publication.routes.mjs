import { Router } from 'express';
import { requireAuth } from '../middleware/auth.middleware.mjs';
import {
  KnowledgePublicationError, createAsset, createVersion, publishVersion, withdrawVersion,
  setVersionGrant, revokeVersionGrant, listCatalog, getPublishedVersion, downloadDataset,
} from '../services/knowledge-publication.service.mjs';

// Mount at /api, after the JSON parser and (where enabled) the global auth guard.
// Endpoint auth is always required, including when the legacy global guard is off.
const router = Router();
const versionPath = '/knowledge/assets/:assetId/versions/:version';
const grantPath = `${versionPath}/grants/:userId`;

function authenticate(req, res, next) {
  res.set('Cache-Control', 'private, no-store');
  if (req.user && req.auth_type) return next();
  return requireAuth(req, res, next);
}

function endpoint(handler) {
  return (req, res) => {
    try {
      return handler({ ...req.user, auth_type: req.auth_type }, req, res);
    } catch (err) {
      if (err instanceof KnowledgePublicationError) {
        return res.status(err.status).json({ success: false, code: err.code, error: err.message });
      }
      // Current source-line permissions govern create; don't echo identifiers,
      // arbitrary input, SQL, provenance or filesystem errors in HTTP responses.
      if (err?.status === 404 || err?.status === 403 || err?.status === 400) {
        return res.status(err.status).json({ success: false, code: err.code, error: '产线不可访问或不支持此操作' });
      }
      return res.status(500).json({ success: false, code: 'KNOWLEDGE_PUBLICATION_ERROR', error: '知识发布操作失败' });
    }
  };
}

function json(handler, status = 200) {
  return endpoint((actor, req, res) => res.status(status).json({ success: true, data: handler(actor, req) }));
}

function ref(req) { return { asset_id: req.params.assetId, version: req.params.version }; }

router.post('/lines/:lineId/assets', authenticate, json((actor, req) => createAsset(actor, req.params.lineId, req.body), 201));
router.post('/knowledge/assets/:assetId/versions', authenticate, json((actor, req) => createVersion(actor, req.params.assetId, req.body), 201));
router.post(`${versionPath}/publish`, authenticate, json((actor, req) => publishVersion(actor, ref(req), req.body)));
router.post(`${versionPath}/withdraw`, authenticate, json((actor, req) => withdrawVersion(actor, ref(req))));
router.put(grantPath, authenticate, json((actor, req) => setVersionGrant(actor, ref(req), req.params.userId, req.body)));
router.delete(grantPath, authenticate, json((actor, req) => revokeVersionGrant(actor, ref(req), req.params.userId)));
router.get('/knowledge/catalog', authenticate, json((actor, req) => listCatalog(actor, req.query)));
router.get(versionPath, authenticate, json((actor, req) => getPublishedVersion(actor, ref(req), 'read')));
router.get(`${versionPath}/download`, authenticate, endpoint((actor, req, res) => {
  const { bytes } = downloadDataset(actor, ref(req));
  return res.set('X-Content-Type-Options', 'nosniff').attachment('comparison.csv').type('application/octet-stream').send(bytes);
}));

export default router;
