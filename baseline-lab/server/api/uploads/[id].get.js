// GET    /api/uploads/:id  — inspect one upload (meta + real data preview)
// DELETE /api/uploads/:id  — remove it

import { defineEventHandler, getRouterParam, createError } from 'h3';
import { getUpload, deleteUpload, uploadMatrix } from '../../utils/uploads.mjs';
import { anomalyDigest } from '../../utils/dataset.mjs';

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, 'id');
  const meta = getUpload(id);
  if (!meta) throw createError({ statusCode: 404, statusMessage: `unknown upload: ${id}` });

  if (event.method === 'DELETE') {
    const ok = deleteUpload(id);
    return { ok, deleted: id };
  }

  // Preview from the ACTUAL parsed matrix — not from stored metadata — so the
  // UI proves the file was parsed rather than echoing what was uploaded.
  const matrix = uploadMatrix(id);
  return {
    upload: meta,
    parsed: {
      rows: matrix.n,
      numeric_columns: matrix.m,
      columns: matrix.colNames,
      first_rows: matrix.X.slice(0, 5).map((row) =>
        Object.fromEntries(matrix.colNames.map((c, j) => [c, Number(row[j].toFixed(6))]))),
    },
    digest: anomalyDigest(matrix, { topK: 10 }),
  };
});
