// POST /api/diagnose — execute a diagnosis of an uploaded dataset.
//
// Body (JSON):
//   { uploadId, algorithms: string[], options?: {} }
//
// Returns { job_id, algorithms, refused } immediately. The diagnosis runs in the
// background and publishes events that GET /api/diagnose/:jobId/stream replays
// live. This is the endpoint the frontend calls; it performs real work — the
// algorithms genuinely execute against the uploaded rows and every LLM
// comparator makes a genuine model request.

import { defineEventHandler, readBody, createError } from 'h3';
import { startDiagnosis, pruneDiagnosisJobs } from '../../utils/diagnosis.mjs';
import { getUpload } from '../../utils/uploads.mjs';

export default defineEventHandler(async (event) => {
  pruneDiagnosisJobs();
  const body = await readBody(event);
  const uploadId = body?.uploadId;
  if (!uploadId) throw createError({ statusCode: 400, statusMessage: 'uploadId is required' });

  const meta = getUpload(uploadId);
  if (!meta) throw createError({ statusCode: 404, statusMessage: `unknown upload: ${uploadId}` });

  try {
    const job = startDiagnosis({
      uploadId,
      algorithms: Array.isArray(body?.algorithms) ? body.algorithms : [],
      options: body?.options || {},
      config: body?.config || {},
    });
    return {
      job_id: job.job_id,
      upload_id: job.upload_id,
      dataset_label: job.dataset_label,
      algorithms: job.algorithms,
      refused: job.refused,
      stream_url: `/api/diagnose/${job.job_id}/stream`,
      result_url: `/api/diagnose/${job.job_id}`,
      started_at: job.started_at,
    };
  } catch (err) {
    throw createError({ statusCode: 400, statusMessage: String(err && err.message ? err.message : err) });
  }
});
