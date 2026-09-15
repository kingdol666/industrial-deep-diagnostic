// POST /api/uploads — accept a user's own data file and store it for real.
//
// multipart/form-data fields:
//   file                 (required) the CSV to analyse
//   label                (optional) display name
//   process_description  (optional) domain context fed verbatim to the LLM
//                        comparators — the ONLY domain knowledge available for
//                        user data, since no variable->cause table exists
//   calibration_fraction (optional) share of rows used to calibrate thresholds
//
// The file is parsed and validated BEFORE anything is written: a file with fewer
// than 2 numeric columns, fewer than 10 rows, or over the size cap is rejected
// with the reason, and nothing is stored.

import { defineEventHandler, readMultipartFormData, createError } from 'h3';
import { createUpload } from '../../utils/uploads.mjs';

export default defineEventHandler(async (event) => {
  const parts = await readMultipartFormData(event);
  if (!parts || !parts.length) {
    throw createError({ statusCode: 400, statusMessage: 'no multipart form data received' });
  }

  const field = (name) => parts.find((p) => p.name === name && !p.filename)?.data?.toString('utf8') ?? '';
  const filePart = parts.find((p) => (p.name === 'file' || p.name === 'data') && p.filename);
  // Optional second file: labelled examples that make the supervised comparators
  // runnable on a user's own process.
  const trainingPart = parts.find((p) => p.name === 'training' && p.filename);

  if (!filePart) {
    throw createError({
      statusCode: 400,
      statusMessage: 'no file part found — send the CSV under the form field name "file"',
    });
  }
  if (!filePart.data?.length) {
    throw createError({ statusCode: 400, statusMessage: `uploaded file is empty: ${filePart.filename}` });
  }

  try {
    const meta = createUpload(filePart.data, filePart.filename, {
      label: field('label'),
      process_description: field('process_description'),
      cause_list: field('cause_list'),
      calibration_fraction: field('calibration_fraction') || undefined,
      notes: field('notes'),
      training_buffer: trainingPart?.data,
      training_filename: trainingPart?.filename,
      label_column: field('label_column'),
    });
    return {
      ok: true,
      upload: meta,
      // Echo back what was actually measured, so the UI can show the user the
      // real shape of what it accepted rather than a generic success toast.
      summary:
        `Accepted ${meta.original_name}: ${meta.rows} rows x ${meta.numeric_columns} numeric columns`
        + (meta.dropped_non_numeric.length ? `; dropped ${meta.dropped_non_numeric.length} non-numeric column(s)` : '')
        + (meta.training ? `; training set: ${meta.training.rows} rows, ${meta.training.classes} classes (label '${meta.training.label_column}')` : '')
        + (meta.cause_list ? `; cause list: ${meta.cause_list.length} candidates` : ''),
    };
  } catch (err) {
    throw createError({ statusCode: 400, statusMessage: String(err && err.message ? err.message : err) });
  }
});
