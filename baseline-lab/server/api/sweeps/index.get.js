// GET /api/sweeps — list persisted sweeps.

import { defineEventHandler } from 'h3';
import { listSweeps } from '../../utils/runner.mjs';

export default defineEventHandler(() => ({ sweeps: listSweeps() }));
