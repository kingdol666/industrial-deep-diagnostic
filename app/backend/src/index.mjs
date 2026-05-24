import { createServer } from 'http';
import express from 'express';
import cors from 'cors';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import fileRoutes from './routes/files.mjs';
import diagnosisRoutes from './routes/diagnosis.mjs';
import historyRoutes from './routes/history.mjs';
import { initWebSocket } from './ws-server.mjs';
import { stmts } from './db.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PORT = process.env.PORT || 3210;

const app = express();

app.use(cors());
app.use(express.json({ limit: '10mb' }));

// Serve uploaded data files statically (for preview/download)
const projectRoot = join(__dirname, '..', '..', '..');
app.use('/data-files', express.static(join(projectRoot, 'data')));
app.use('/workspace-files', express.static(join(projectRoot, 'workspace')));

// API routes
app.use('/api/files', fileRoutes);
app.use('/api/diagnosis', diagnosisRoutes);
app.use('/api/history', historyRoutes);

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Serve Vue frontend in production
const frontendDist = join(__dirname, '..', '..', 'frontend', 'dist');
app.use(express.static(frontendDist));
app.get('*', (req, res) => {
  if (!req.path.startsWith('/api/') && !req.path.startsWith('/ws')) {
    res.sendFile(join(frontendDist, 'index.html'));
  }
});

// Create HTTP server (shared by Express + WebSocket)
const server = createServer(app);

// Initialize WebSocket server on /ws
initWebSocket(server);

// Mark any stale 'running' runs as interrupted (server was restarted)
const staleRuns = stmts.getActiveRuns.all();
for (const run of staleRuns) {
  stmts.failRun.run({ runId: run.run_id, error: 'Server restarted — diagnosis interrupted' });
  console.log(`[Industrial Diagnostic API] Marked stale run as interrupted: ${run.run_id}`);
}

server.listen(PORT, () => {
  console.log(`[Industrial Diagnostic API] HTTP + WebSocket server on http://localhost:${PORT}`);
  console.log(`[Industrial Diagnostic API] WebSocket endpoint: ws://localhost:${PORT}/ws`);
  console.log(`[Industrial Diagnostic API] Project root: ${projectRoot}`);
  console.log(`[Industrial Diagnostic API] Data dir: ${join(projectRoot, 'data')}`);
});

export default app;
