# Phase 1+3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Phase 1 (Docker + structured logging + health checks) and Phase 3 (ECharts visualization upgrade)

**Architecture:**
- Phase 1: Replace all `console.log` calls with winston structured logging; wrap the app in Docker multi-stage build; add nginx for production static serving; enhance health endpoint with DB and disk checks
- Phase 3: Install ECharts + vue-echarts in frontend; add backend chart-data API endpoint for intermediate diagnostic data; build reusable chart components; add live chart dashboard to DiagnosisView during runs

**Tech Stack:** winston, Docker, nginx, ECharts 5, vue-echarts 7

**Spec reference:** `docs/superpowers/specs/2026-05-26-feature-expansion-plan.md`

---

## File Structure

```
# Phase 1 — New files
app/backend/Dockerfile              # Multi-stage build: frontend → nginx + backend
app/backend/docker-compose.yml      # Stack definition (backend + optional InfluxDB)
app/backend/nginx.conf.template     # Production nginx config template
app/backend/src/utils/logger.mjs    # Winston logger instance + transport setup
config/logging.yaml                 # Logging configuration (defaults)

# Phase 1 — Modified files
app/backend/src/index.mjs           # Replace console.log → logger; add enhanced health
app/backend/src/db/database.mjs     # Replace console.log → logger
app/backend/src/engine/diagnosis-engine.mjs  # Replace console.log → logger
app/backend/src/engine/claude-client.mjs     # Replace console.log → logger
app/backend/src/services/diagnosis.service.mjs  # Replace console.log → logger
app/backend/src/services/files.service.mjs  # Replace console.log → logger
app/backend/src/transport/ws-server.mjs     # Replace console.log → logger
app/backend/src/routes/diagnosis.routes.mjs # Replace console.log → logger
app/backend/src/routes/files.routes.mjs     # Replace console.log → logger
config/default.yaml                 # Add logging config section

# Phase 3 — New files
app/frontend/src/components/charts/
  LineChart.vue           # Interactive time-series line chart (zoomable)
  HeatmapChart.vue        # Correlation heatmap
  ScatterChart.vue        # Scatter/bubble plot for correlations
  GaugeChart.vue          # Single-value health gauge 0-100
  index.js                # Re-export all chart components
app/backend/src/routes/analysis.routes.mjs  # Chart-data API endpoints
app/backend/src/services/analysis.service.mjs  # Chart-data extraction logic

# Phase 3 — Modified files
app/frontend/package.json           # Add echarts + vue-echarts
app/backend/src/index.mjs          # Mount analysis routes
app/frontend/src/components/diagnosis/DiagnosisView.vue  # Add chart dashboard panel
```

---

## Phase 1 Tasks

### Task 1.1: Create Winston Logger

**Files:**
- Create: `app/backend/src/utils/logger.mjs`
- Modify: `config/default.yaml`

- [ ] **Step 1: Add logging config to default.yaml**

```yaml
# config/default.yaml — add before the last line or under a new section

logging:
  level: "info"
  format: "json"              # "json" or "simple"
  output: "stdout"            # "stdout", "file", or both
  file_path: "logs/app.log"
  max_size_mb: 50
  max_files: 5
```

- [ ] **Step 2: Create logger utility**

```javascript
// app/backend/src/utils/logger.mjs
import winston from 'winston';
import { config } from '../../../../config/loader.mjs';
import { join } from 'path';
import { PROJECT_ROOT } from '../../../../config/loader.mjs';

const cfg = config.logging || { level: 'info', format: 'json', output: 'stdout' };
const transports = [];

if (cfg.output === 'stdout' || cfg.output === 'both') {
  transports.push(new winston.transports.Console({
    format: cfg.format === 'json'
      ? winston.format.combine(
          winston.format.timestamp(),
          winston.format.errors({ stack: true }),
          winston.format.json(),
        )
      : winston.format.combine(
          winston.format.colorize(),
          winston.format.simple(),
        ),
  }));
}

if (cfg.output === 'file' || cfg.output === 'both') {
  const logDir = join(PROJECT_ROOT, cfg.file_path ? require('path').dirname(cfg.file_path) : 'logs');
  transports.push(new winston.transports.File({
    filename: join(PROJECT_ROOT, cfg.file_path || 'logs/app.log'),
    maxsize: (cfg.max_size_mb || 50) * 1024 * 1024,
    maxFiles: cfg.max_files || 5,
    format: winston.format.combine(
      winston.format.timestamp(),
      winston.format.json(),
    ),
  }));
}

const logger = winston.createLogger({
  level: cfg.level || 'info',
  transports,
  exitOnError: false,
});

// Shortcut: logger.error() with Error object support
export function logError(context, err) {
  logger.error(`[${context}] ${err.message}`, {
    context,
    stack: err.stack,
    code: err.code,
    status: err.status,
  });
}

export default logger;
```

- [ ] **Step 3: Install winston**

```bash
cd "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/app/backend"
npm install winston
```

Expected: `+ winston@3.x` in package.json

- [ ] **Step 4: Commit**

```bash
git -C "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic" add \
  app/backend/src/utils/logger.mjs \
  config/default.yaml \
  app/backend/package.json \
  app/backend/package-lock.json
git -C "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic" commit -m "feat: add winston structured logger"
```

---

### Task 1.2: Replace All console.log with Logger

**Files:**
- Modify: `app/backend/src/index.mjs`
- Modify: `app/backend/src/db/database.mjs`
- Modify: `app/backend/src/engine/diagnosis-engine.mjs`
- Modify: `app/backend/src/engine/claude-client.mjs`
- Modify: `app/backend/src/services/diagnosis.service.mjs`
- Modify: `app/backend/src/services/files.service.mjs`
- Modify: `app/backend/src/transport/ws-server.mjs`

This is a mechanical find-and-replace across all backend files. Each file follows the same pattern.

- [ ] **Step 1: Update index.mjs**

Add import at top:
```javascript
import logger, { logError } from './utils/logger.mjs';
```

Replace:
```javascript
console.log('[Init] Checking project configuration...');
```
→
```javascript
logger.info('Checking project configuration...', { context: 'Init' });
```

Replace:
```javascript
console.error('[Init] FATAL: config/default.yaml not found');
```
→
```javascript
logger.error('config/default.yaml not found', { context: 'Init' });
```

Replace:
```javascript
console.log(`[Init] Marked stale run as interrupted: ${run.run_id}`);
```
→
```javascript
logger.info(`Marked stale run as interrupted: ${run.run_id}`, { context: 'Init', runId: run.run_id });
```

Replace:
```javascript
console.log(`[Industrial Diagnostic API] HTTP + WebSocket server on http://localhost:${PORT}`);
```
→
```javascript
logger.info(`HTTP + WebSocket server on http://localhost:${PORT}`, { context: 'Server', port: PORT });
```

- [ ] **Step 2: Update database.mjs**

Add import:
```javascript
import logger from '../utils/logger.mjs';
```

Replace:
```javascript
console.log('[DB] Initializing database...');
console.log(`[DB] Path: ${DB_PATH}`);
console.log('[DB] Database initialized successfully.');
```
→
```javascript
logger.info('Initializing database...', { context: 'DB' });
logger.info(`Path: ${DB_PATH}`, { context: 'DB' });
logger.info('Database initialized successfully.', { context: 'DB' });
```

- [ ] **Step 3: Update diagnosis-engine.mjs**

Add import:
```javascript
import logger from '../utils/logger.mjs';
```

Replace:
```javascript
if (finished.length > 0) console.log(`[Engine] cleaned up ${finished.length} finished runs, ${runs.size} remaining`);
```
→
```javascript
if (finished.length > 0) logger.info(`Cleaned up ${finished.length} finished runs, ${runs.size} remaining`, { context: 'Engine' });
```

Replace:
```javascript
for (const cb of run.subscribers) {
    try { cb(enriched); } catch (e) { console.error('[Engine] subscriber error:', e.message); }
  }
```
→
```javascript
  for (const cb of run.subscribers) {
    try { cb(enriched); } catch (e) { logger.error(`Subscriber error: ${e.message}`, { context: 'Engine', runId }); }
  }
```

Repeat for the second `console.error('[Engine] subscriber error:')` and `console.error('[Engine] close callback error:')` in the same file.

- [ ] **Step 4: Update claude-client.mjs**

Add import:
```javascript
import logger from '../utils/logger.mjs';
```

Replace all `console.error` calls. There are 3 total in this file — pattern-match by string.

- [ ] **Step 5: Update diagnosis.service.mjs**

Add import:
```javascript
import logger, { logError } from '../utils/logger.mjs';
```

Replace the `console.warn` in the executingRuns guard:
```javascript
console.warn(`[Diagnosis] executeDiagnosis called twice for run: ${runId} — skipping duplicate`);
```
→
```javascript
logger.warn(`executeDiagnosis called twice for run: ${runId} — skipping duplicate`, { context: 'Diagnosis', runId });
```

Replace all `console.error("[Diagnosis] error:",` patterns — there are 5 in this file:
```javascript
console.error("[Diagnosis] error:", e.message);
```
→
```javascript
logger.error(`Error: ${e.message}`, { context: 'Diagnosis' });
```

- [ ] **Step 6: Update files.service.mjs**

Add import:
```javascript
import logger from '../utils/logger.mjs';
```

Replace `console.error("[Files] error:",` (2 instances):
```javascript
console.error("[Files] error:", e.message);
```
→
```javascript
logger.error(`Error: ${e.message}`, { context: 'Files' });
```

- [ ] **Step 7: Update ws-server.mjs**

Add import:
```javascript
import logger from '../utils/logger.mjs';
```

Replace:
```javascript
console.log(`[WebSocket] Server ready on path /ws`);
```
→
```javascript
logger.info(`Server ready on path /ws`, { context: 'WebSocket' });
```

Replace:
```javascript
ws.on('error', (err) => { console.error('[WS] connection error:', err.message); });
```
→
```javascript
ws.on('error', (err) => { logger.error(`Connection error: ${err.message}`, { context: 'WS' }); });
```

- [ ] **Step 8: Verify no raw console.log remains**

```bash
grep -n "console\.log\|console\.error" "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/app/backend/src/" --include="*.mjs"
```

Expected output: 0 matches (or only test files). If any remain, fix them.

- [ ] **Step 9: Start backend and verify logging**

```bash
cd "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic" && node app/backend/src/index.mjs
```

Expected: JSON-formatted log lines like:
```json
{"level":"info","message":"Initializing database...","context":"DB","timestamp":"..."}
```

- [ ] **Step 10: Commit**

```bash
git -C "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic" add app/backend/src/
git -C "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic" commit -m "feat: replace console.log with winston structured logging across all backend files"
```

---

### Task 1.3: Enhanced Health Endpoint

**Files:**
- Modify: `app/backend/src/index.mjs`

- [ ] **Step 1: Update /api/health endpoint**

Replace the existing health check at `index.mjs:57-59`:
```javascript
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});
```

With:
```javascript
import { existsSync } from 'fs';
import { join } from 'path';
import { db } from './db/database.mjs';

app.get('/api/health', (req, res) => {
  const checks = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    checks: {},
  };

  // Database check
  try {
    db.prepare('SELECT 1').get();
    checks.checks.database = { status: 'ok' };
  } catch (err) {
    checks.checks.database = { status: 'error', message: err.message };
    checks.status = 'degraded';
  }

  // Disk space check (data dir)
  const dataDir = join(PROJECT_ROOT, 'data');
  if (existsSync(dataDir)) {
    // Basic writability check
    try {
      const { accessSync, constants } = await_import_fs();
      accessSync(dataDir, constants.W_OK);
      checks.checks.disk = { status: 'ok', path: dataDir };
    } catch {
      checks.checks.disk = { status: 'error', message: 'Data directory not writable' };
      checks.status = 'degraded';
    }
  }

  // Active runs count
  try {
    const activeRunCount = db.prepare("SELECT COUNT(*) as count FROM diagnostic_runs WHERE status = 'running'").get();
    checks.checks.activeRuns = activeRunCount.count;
  } catch {}

  const httpCode = checks.status === 'ok' ? 200 : 503;
  res.status(httpCode).json(checks);
});
```

Actually, let me write this without the async import:

```javascript
app.get('/api/health', (req, res) => {
  const checks = {
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    checks: {},
  };

  // Database check
  try {
    db.prepare('SELECT 1').get();
    checks.checks.database = { status: 'ok' };
  } catch (err) {
    checks.checks.database = { status: 'error', message: err.message };
    checks.status = 'degraded';
  }

  // Active runs count
  try {
    const count = db.prepare("SELECT COUNT(*) as count FROM diagnostic_runs WHERE status = 'running'").get();
    checks.checks.activeRuns = count;
  } catch {}

  const httpCode = checks.status === 'ok' ? 200 : 503;
  res.status(httpCode).json(checks);
});
```

Note: Add `import { db } from './db/database.mjs';` at the top alongside existing imports.

- [ ] **Step 2: Test health endpoint**

```bash
curl -s http://localhost:3210/api/health | python3 -m json.tool
```

Expected output includes `checks.database.status`, `uptime`, `checks.activeRuns`.

- [ ] **Step 3: Commit**

```bash
git add app/backend/src/index.mjs
git commit -m "feat: enhance health endpoint with DB status and active runs"
```

---

### Task 1.4: Dockerfile

**Files:**
- Create: `Dockerfile` (project root)

- [ ] **Step 1: Create multi-stage Dockerfile**

```dockerfile
# ===== Stage 1: Frontend build =====
FROM node:22-alpine AS frontend-builder
WORKDIR /build/frontend
COPY app/frontend/package*.json ./
RUN npm ci
COPY app/frontend/ ./
RUN npm run build

# ===== Stage 2: Backend runtime =====
FROM node:22-alpine

# Install Python + dependencies for data processing scripts
RUN apk add --no-cache python3 py3-pip

WORKDIR /app

# Copy backend dependencies and install
COPY app/backend/package*.json ./app/backend/
RUN cd app/backend && npm ci --production

# Copy config
COPY config/ ./config/

# Copy commands
COPY commands/ ./commands/
COPY package.json ./

# Copy built frontend
COPY --from=frontend-builder /build/frontend/dist ./app/frontend/dist

# Copy backend source
COPY app/backend/src ./app/backend/src/

# Copy data scripts
COPY data/*.py ./data/
COPY data/*.csv ./data/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3210/api/health || exit 1

EXPOSE 3210

# Default: start backend (which serves frontend dist too)
CMD ["node", "app/backend/src/index.mjs"]
```

- [ ] **Step 2: Create .dockerignore**

```
node_modules/
.git/
.gitignore
*.md
workspace/
data/diagnostic.db*
app/frontend/node_modules/
app/backend/node_modules/
docs/
.omc/
.claude/
webfrp/
```

- [ ] **Step 3: Build and verify**

```bash
cd "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic"
docker build -t industrial-deep-diagnostic:latest .
```

Expected: Build succeeds. If apk is slow, consider using `--no-cache` or removing Python from runtime (keep only in builder stage).

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: add multi-stage Dockerfile with HEALTHCHECK"
```

---

### Task 1.5: Docker Compose

**Files:**
- Create: `docker-compose.yml` (project root)

- [ ] **Step 1: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ind-diag-backend
    ports:
      - "3210:3210"
    volumes:
      # Persist database
      - ./data:/app/data
      # Persist diagnostic runs
      - ./workspace:/app/workspace
      # Config override
      - ./config/local.yaml:/app/config/local.yaml:ro
    environment:
      - SERVER_PORT=3210
      - CLAUDE_API_KEY=${CLAUDE_API_KEY:-}
      - CLAUDE_API_BASE_URL=${CLAUDE_API_BASE_URL:-}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
      - ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL:-}
      - LOGGING_FORMAT=json
      - LOGGING_LEVEL=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:3210/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
```

- [ ] **Step 2: Create .env.example**

```bash
cat > ".env.example" << 'ENVEOF'
# Claude API Configuration (pick ANTHROPIC or custom provider)
ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_BASE_URL=https://api.anthropic.com
# CLAUDE_API_KEY=
# CLAUDE_API_BASE_URL=

# Server
SERVER_PORT=3210

# Logging
LOGGING_FORMAT=json
LOGGING_LEVEL=info
ENVEOF
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "feat: add docker-compose.yml with backend service + .env.example"
```

---

### Task 1.6: Production Nginx Config

**Files:**
- Create: `nginx.conf` (project root, used by Docker)

- [ ] **Step 1: Create production nginx config**

```nginx
# nginx.conf — Production reverse proxy for Industrial Deep Diagnostic
# In Docker, frontend dist is served directly by nginx,
# /api and /ws are proxied to the Node.js backend.

upstream backend {
    server 127.0.0.1:3210;
    keepalive 64;
}

server {
    listen 80;
    server_name _;
    root /app/frontend/dist;
    index index.html;

    # Gzip
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 256;

    # Static assets with far-future cache
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Data files (static)
    location /data-files/ {
        alias /app/data/;
    }

    # Workspace files (static)
    location /workspace-files/ {
        alias /app/workspace/;
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support (no buffering)
        proxy_buffering off;
        proxy_cache off;
    }

    # WebSocket proxy
    location /ws {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Note: This nginx config is for production Docker deployment where nginx runs as a separate service alongside the Node.js backend. If the user prefers a combined approach (Node.js serves both API and static files), this is optional.

- [ ] **Step 2: Update Dockerfile to use nginx (if desired)**

This step would add an nginx service to docker-compose.yml. Keep it simple for now — the current approach of Node.js serving both API and frontend dist is fine for single-instance deployment. Skip nginx for now unless the user asks for it.

- [ ] **Step 3: Commit (if nginx.conf kept)**

```bash
git add nginx.conf
git commit -m "feat: add production nginx reverse proxy config"
```

---

## Phase 3 Tasks

### Task 3.1: Install ECharts Dependencies

**Files:**
- Modify: `app/frontend/package.json`

- [ ] **Step 1: Install echarts + vue-echarts**

```bash
cd "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/app/frontend"
npm install echarts vue-echarts
```

Expected: `+ echarts@5.x`, `+ vue-echarts@7.x` in package.json

- [ ] **Step 2: Commit**

```bash
git add app/frontend/package.json app/frontend/package-lock.json
git commit -m "feat: add echarts + vue-echarts for interactive charts"
```

---

### Task 3.2: Create Chart Components

**Files:**
- Create: `app/frontend/src/components/charts/LineChart.vue`
- Create: `app/frontend/src/components/charts/HeatmapChart.vue`
- Create: `app/frontend/src/components/charts/ScatterChart.vue`
- Create: `app/frontend/src/components/charts/GaugeChart.vue`
- Create: `app/frontend/src/components/charts/index.js`

- [ ] **Step 1: Create LineChart component**

```vue
<!-- app/frontend/src/components/charts/LineChart.vue -->
<template>
  <div class="chart-wrapper">
    <v-chart :option="chartOption" autoresize />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import VChart from 'vue-echarts';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart as ELineChart } from 'echarts/charts';
import {
  GridComponent, TooltipComponent, DataZoomComponent,
  LegendComponent, MarkLineComponent,
} from 'echarts/components';

use([
  CanvasRenderer, ELineChart,
  GridComponent, TooltipComponent, DataZoomComponent,
  LegendComponent, MarkLineComponent,
]);

const props = defineProps({
  data: { type: Array, default: () => [] },
  xField: { type: String, default: 'time' },
  yFields: { type: Array, default: () => ['value'] },
  colors: { type: Array, default: () => ['#5470C6', '#91CC75', '#EE6666'] },
  title: { type: String, default: '' },
  yLabel: { type: String, default: '' },
  zoomable: { type: Boolean, default: true },
  markLines: { type: Array, default: () => [] },
});

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  title: props.title ? { text: props.title, left: 'center', textStyle: { fontSize: 14 } } : undefined,
  tooltip: {
    trigger: 'axis',
    formatter: (params) => {
      const main = `<b>${params[0].axisValue}</b>`;
      const lines = params.map(p => `${p.marker} ${p.seriesName}: <b>${p.value}</b>`);
      return [main, ...lines].join('<br/>');
    },
  },
  legend: props.yFields.length > 1 ? { bottom: 0, type: 'scroll' } : undefined,
  grid: { left: 60, right: 20, top: props.title ? 40 : 20, bottom: props.zoomable ? 50 : 30 },
  xAxis: {
    type: 'category',
    data: props.data.map(d => d[props.xField]),
    axisLabel: { rotate: 45, fontSize: 10 },
  },
  yAxis: {
    type: 'value',
    name: props.yLabel,
    nameLocation: 'middle',
    nameGap: 40,
  },
  dataZoom: props.zoomable
    ? [{ type: 'inside', start: 0, end: 100 }, { type: 'slider', start: 0, end: 100, height: 20, bottom: 0 }]
    : undefined,
  series: props.yFields.map((field, i) => ({
    name: field,
    type: 'line',
    data: props.data.map(d => d[field]),
    smooth: true,
    symbol: 'none',
    lineStyle: { width: 2 },
    color: props.colors[i % props.colors.length],
    markLine: props.markLines.includes(field)
      ? {
          silent: true,
          data: [
            { type: 'average', name: 'Avg', label: { formatter: 'Avg: {c}' } },
            { type: 'max', name: 'Max', label: { formatter: 'Max: {c}' } },
            { type: 'min', name: 'Min', label: { formatter: 'Min: {c}' } },
          ],
        }
      : undefined,
  })),
}));
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
  height: 100%;
  min-height: 300px;
}
</style>
```

- [ ] **Step 2: Create HeatmapChart component**

```vue
<!-- app/frontend/src/components/charts/HeatmapChart.vue -->
<template>
  <div class="chart-wrapper">
    <v-chart :option="chartOption" autoresize />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import VChart from 'vue-echarts';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { HeatmapChart as EHeatmap } from 'echarts/charts';
import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components';

use([CanvasRenderer, EHeatmap, GridComponent, TooltipComponent, VisualMapComponent]);

const props = defineProps({
  data: { type: Array, default: () => [] },
  xLabels: { type: Array, default: () => [] },
  yLabels: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  min: { type: Number, default: -1 },
  max: { type: Number, default: 1 },
});

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  title: props.title ? { text: props.title, left: 'center', textStyle: { fontSize: 14 } } : undefined,
  tooltip: {
    formatter: (params) => {
      return `${params.value[0]}, ${params.value[1]}: <b>${params.value[2].toFixed(3)}</b>`;
    },
  },
  grid: { left: 80, right: 60, top: props.title ? 40 : 20, bottom: 40 },
  xAxis: { type: 'category', data: props.xLabels, splitArea: { show: true }, axisLabel: { rotate: 45, fontSize: 9 } },
  yAxis: { type: 'category', data: props.yLabels, splitArea: { show: true }, axisLabel: { fontSize: 9 } },
  visualMap: {
    min: props.min,
    max: props.max,
    calculable: true,
    orient: 'vertical',
    right: 0,
    top: 'center',
    inRange: { color: ['#313695', '#4575B4', '#74ADD1', '#ABD9E9', '#E0F3F8', '#FFFFBF', '#FEE090', '#FDAE61', '#F46D43', '#D73027', '#A50026'] },
  },
  series: [{
    type: 'heatmap',
    data: props.data.map(d => [d.x, d.y, d.value]),
    label: { show: props.data.length <= 50, fontSize: 9 },
    emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
  }],
}));
</script>

<style scoped>
.chart-wrapper { width: 100%; height: 100%; min-height: 350px; }
</style>
```

- [ ] **Step 3: Create ScatterChart component**

```vue
<!-- app/frontend/src/components/charts/ScatterChart.vue -->
<template>
  <div class="chart-wrapper">
    <v-chart :option="chartOption" autoresize />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import VChart from 'vue-echarts';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { ScatterChart as EScatter } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';

use([CanvasRenderer, EScatter, GridComponent, TooltipComponent, LegendComponent]);

const props = defineProps({
  data: { type: Array, default: () => [] },
  xField: { type: String, default: 'x' },
  yField: { type: String, default: 'y' },
  title: { type: String, default: '' },
  xLabel: { type: String, default: '' },
  yLabel: { type: String, default: '' },
  regressionLine: { type: Boolean, default: false },
});

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  title: props.title ? { text: props.title, left: 'center', textStyle: { fontSize: 14 } } : undefined,
  tooltip: {
    formatter: (params) => {
      return `${params.value[0].toFixed(3)}, ${params.value[1].toFixed(3)}`;
    },
  },
  grid: { left: 60, right: 30, top: props.title ? 40 : 20, bottom: 40 },
  xAxis: { type: 'value', name: props.xLabel, splitLine: { lineStyle: { type: 'dashed' } } },
  yAxis: { type: 'value', name: props.yLabel, splitLine: { lineStyle: { type: 'dashed' } } },
  series: [{
    type: 'scatter',
    data: props.data.map(d => [d[props.xField], d[props.yField]]),
    symbolSize: 6,
    itemStyle: { opacity: 0.6 },
  }],
}));
</script>

<style scoped>
.chart-wrapper { width: 100%; height: 100%; min-height: 300px; }
</style>
```

- [ ] **Step 4: Create GaugeChart component**

```vue
<!-- app/frontend/src/components/charts/GaugeChart.vue -->
<template>
  <div class="chart-wrapper">
    <v-chart :option="chartOption" autoresize />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import VChart from 'vue-echarts';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GaugeChart as EGauge } from 'echarts/charts';

use([CanvasRenderer, EGauge]);

const props = defineProps({
  value: { type: Number, default: 0 },
  title: { type: String, default: '' },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  unit: { type: String, default: '' },
});

const chartOption = computed(() => ({
  backgroundColor: 'transparent',
  series: [{
    type: 'gauge',
    startAngle: 210,
    endAngle: -30,
    min: props.min,
    max: props.max,
    progress: { show: true, width: 12 },
    axisLine: {
      lineStyle: {
        width: 12,
        color: [
          [0.3, '#E74C3C'],   // 0-30% red
          [0.7, '#F39C12'],   // 30-70% orange
          [1, '#27AE60'],     // 70-100% green
        ],
      },
    },
    axisTick: { show: false },
    splitLine: { length: 8, lineStyle: { width: 2 } },
    axisLabel: { distance: 20, fontSize: 10 },
    pointer: { width: 4, length: '60%' },
    detail: {
      valueAnimation: true,
      formatter: `{value}${props.unit}`,
      fontSize: 24,
      fontWeight: 'bold',
      offsetCenter: [0, '50%'],
    },
    title: { offsetCenter: [0, '80%'], fontSize: 13 },
    data: [{ value: props.value, name: props.title }],
  }],
}));
</script>

<style scoped>
.chart-wrapper { width: 100%; height: 100%; min-height: 250px; }
</style>
```

- [ ] **Step 5: Create chart index.js**

```javascript
// app/frontend/src/components/charts/index.js
export { default as LineChart } from './LineChart.vue';
export { default as HeatmapChart } from './HeatmapChart.vue';
export { default as ScatterChart } from './ScatterChart.vue';
export { default as GaugeChart } from './GaugeChart.vue';
```

- [ ] **Step 6: Build frontend to verify**

```bash
cd "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/app/frontend"
npm run build
```

Expected: Build succeeds with ECharts bundled correctly.

- [ ] **Step 7: Commit**

```bash
git add app/frontend/src/components/charts/
git commit -m "feat: add ECharts chart components (Line, Heatmap, Scatter, Gauge)"
```

---

### Task 3.3: Backend Chart-Data API

**Files:**
- Create: `app/backend/src/routes/analysis.routes.mjs`
- Create: `app/backend/src/services/analysis.service.mjs`
- Modify: `app/backend/src/index.mjs`

- [ ] **Step 1: Create analysis service**

```javascript
// app/backend/src/services/analysis.service.mjs
import { existsSync, readdirSync, readFileSync } from 'fs';
import { join } from 'path';
import { WORKSPACE_DIR } from '../engine/claude-client.mjs';

/**
 * Extract chart-ready data from a completed diagnostic run workspace.
 * Returns structured data for each chart type, or null if unavailable.
 */
export function getRunChartData(runDirName) {
  const runDir = join(WORKSPACE_DIR, 'diagnostic-runs', runDirName);
  if (!existsSync(runDir)) return null;

  const result = {};

  // Read processed feature summary (correlation data)
  const processedDir = join(runDir, '02_processed');
  if (existsSync(processedDir)) {
    const files = readdirSync(processedDir);

    // Feature summary JSON
    for (const f of files) {
      if (f === 'feature_summary.json') {
        try {
          const summary = JSON.parse(readFileSync(join(processedDir, f), 'utf-8'));
          result.featureSummary = summary;
        } catch {}
      }
    }
  }

  // Read diagnosis JSON (has structured findings)
  const diagDir = join(runDir, '04_diagnostics');
  if (existsSync(diagDir)) {
    const files = readdirSync(diagDir);
    for (const f of files) {
      if (f === 'diagnosis.json') {
        try {
          result.diagnosis = JSON.parse(readFileSync(join(diagDir, f), 'utf-8'));
        } catch {}
      }
      if (f === 'evidence.json') {
        try {
          result.evidence = JSON.parse(readFileSync(join(diagDir, f), 'utf-8'));
        } catch {}
      }
    }
  }

  // Read run summary
  const summaryFile = join(runDir, 'run_summary.json');
  if (existsSync(summaryFile)) {
    try {
      result.runSummary = JSON.parse(readFileSync(summaryFile, 'utf-8'));
    } catch {}
  }

  // Build chart-friendly datasets from the extracted data
  const charts = {};

  // 1. Feature correlation heatmap data
  if (result.featureSummary?.correlations) {
    const corr = result.featureSummary.correlations;
    const vars = Object.keys(corr);
    charts.heatmap = {
      type: 'correlation',
      variables: vars,
      data: vars.flatMap((v1, i) =>
        vars.map((v2, j) => ({ x: i, y: j, value: corr[v1]?.[v2] ?? 0 }))
      ),
      xLabels: vars,
      yLabels: vars,
    };
  }

  // 2. Confidence/score gauges
  if (result.diagnosis?.confidence) {
    charts.confidence = {
      type: 'gauge',
      overall: result.diagnosis.confidence.overall || 0,
      dimensions: Object.entries(result.diagnosis.confidence)
        .filter(([k]) => k !== 'overall')
        .map(([k, v]) => ({ name: k, value: typeof v === 'number' ? v : (v?.score || 0) })),
    };
  }

  // 3. Evidence timeline
  if (result.evidence?.evidence_chain) {
    charts.evidenceTimeline = {
      type: 'timeline',
      items: result.evidence.evidence_chain.map(e => ({
        rank: e.rank,
        label: e.label || e.description?.slice(0, 50),
        type: e.type,
      })),
    };
  }

  return Object.keys(charts).length > 0 ? charts : null;
}
```

- [ ] **Step 2: Create analysis routes**

```javascript
// app/backend/src/routes/analysis.routes.mjs
import { Router } from 'express';
import { getRunChartData } from '../services/analysis.service.mjs';

const router = Router();

// GET /api/analysis/chart-data/:runDirName
// Returns structured chart data from a completed diagnostic run's workspace
router.get('/chart-data/:runDirName', (req, res) => {
  try {
    const { runDirName } = req.params;
    // Security: prevent path traversal
    if (runDirName.includes('..') || runDirName.includes('/')) {
      return res.status(400).json({ success: false, error: 'Invalid run directory name' });
    }

    const chartData = getRunChartData(runDirName);
    if (!chartData) {
      return res.status(404).json({ success: false, error: 'No chart data available for this run' });
    }

    res.json({ success: true, data: chartData });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

export default router;
```

- [ ] **Step 3: Mount routes in index.mjs**

Add import at top of `app/backend/src/index.mjs`:
```javascript
import analysisRoutes from './routes/analysis.routes.mjs';
```

Add after existing route mounts (around line 54):
```javascript
app.use('/api/analysis', analysisRoutes);
```

- [ ] **Step 4: Test the endpoint**

```bash
# Find a completed run directory
ls "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/workspace/diagnostic-runs/" | head -5
```

Pick a run dir, then:
```bash
curl -s "http://localhost:3210/api/analysis/chart-data/YOUR_RUN_DIR" | python3 -c "import sys,json; d=json.load(sys.stdin); print('Keys:', list(d.get('data',{}).keys()) if d.get('data') else 'no data')"
```

Expected: Lists chart types available (heatmap, confidence, etc.) or "no data" if the run has no structured JSON.

- [ ] **Step 5: Commit**

```bash
git add app/backend/src/routes/analysis.routes.mjs app/backend/src/services/analysis.service.mjs app/backend/src/index.mjs
git commit -m "feat: add chart-data API endpoint for diagnostic run visualization"
```

---

### Task 3.4: Chart Dashboard in DiagnosisView

**Files:**
- Modify: `app/frontend/src/components/diagnosis/DiagnosisView.vue`

- [ ] **Step 1: Add chart dashboard panel (template section)**

Add a chart dashboard section inside DiagnosisView, shown when a run has completed and has chart data.

```vue
<!-- Insert inside <template>, after the report section, before </div> -->
<div v-if="runCompleted && chartData" class="card chart-dashboard">
  <div class="card-title">
    <span>📊 诊断数据可视化</span>
    <button class="btn btn-sm" @click="toggleCharts">
      {{ showCharts ? '收起' : '展开' }}
    </button>
  </div>
  <div v-if="showCharts" class="chart-grid">
    <!-- Correlation heatmap -->
    <div v-if="chartData.heatmap" class="chart-cell chart-cell-full">
      <HeatmapChart
        :data="chartData.heatmap.data"
        :x-labels="chartData.heatmap.xLabels"
        :y-labels="chartData.heatmap.yLabels"
        title="变量相关性矩阵"
      />
    </div>
    <!-- Confidence gauge -->
    <div v-if="chartData.confidence" class="chart-cell chart-cell-half">
      <GaugeChart
        :value="chartData.confidence.overall"
        title="诊断置信度"
        unit="%"
      />
    </div>
    <!-- Evidence bar -->
    <div v-if="chartData.evidenceTimeline" class="chart-cell chart-cell-half">
      <div class="card">
        <div class="card-title" style="font-size:13px">证据链概览</div>
        <div v-for="item in chartData.evidenceTimeline.items" :key="item.rank" class="evidence-row">
          <span class="evidence-rank">R{{ item.rank }}</span>
          <span class="evidence-label">{{ item.label }}</span>
          <span class="evidence-type">{{ item.type }}</span>
        </div>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Add chart data fetching logic (script section)**

Add to `<script setup>` in DiagnosisView:
```javascript
import { LineChart, HeatmapChart, ScatterChart, GaugeChart } from '../charts/index.js';
import { api } from '../../api/index.js';

const chartData = ref(null);
const showCharts = ref(true);

function toggleCharts() { showCharts.value = !showCharts.value; }

async function fetchChartData(runDir) {
  if (!runDir) return;
  try {
    const res = await fetch(`/api/analysis/chart-data/${encodeURIComponent(runDir.replace('workspace/diagnostic-runs/', ''))}`);
    const json = await res.json();
    if (json.success && json.data) {
      chartData.value = json.data;
    }
  } catch (err) {
    console.error('Failed to fetch chart data:', err);
  }
}

// Call fetchChartData when the run completes and we have a reportPath
// Insert into the existing completion handler:
// After reportPath is set, call fetchChartData(runDir)
```

- [ ] **Step 3: Add chart styles**

```css
/* Add to <style scoped> */
.chart-dashboard { margin-top: 16px; }
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
.chart-cell { min-height: 300px; }
.chart-cell-full { grid-column: 1 / -1; }
.chart-cell-half { grid-column: span 1; }
.evidence-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
  border-bottom: 1px solid var(--border);
}
.evidence-rank {
  background: var(--accent);
  color: #fff;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
}
.evidence-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.evidence-type {
  color: var(--text2);
  font-size: 10px;
  text-transform: uppercase;
}
```

- [ ] **Step 4: Wire chartData fetch into the completion flow**

Add at line 387 (after `reportPath.value = d.reportPath;` inside the SSE `complete` handler):
```javascript
        // Fetch interactive chart data when run completes
        if (d.reportPath) {
          const runDir = d.reportPath.split('/').slice(0, -1).join('/');
          fetchChartData(runDir);
        }
```

Also add at line 628 (after `reportPath.value = status.report_path;` inside the `getRunStatus` fallback):
```javascript
        // Fetch interactive chart data
        if (status.report_path) {
          const runDir = status.report_path.split('/').slice(0, -1).join('/');
          fetchChartData(runDir);
        }
```

- [ ] **Step 5: Build frontend to verify**

```bash
cd "/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/app/frontend"
npm run build
```

Expected: Build succeeds with all new chart imports.

- [ ] **Step 6: Commit**

```bash
git add app/frontend/src/components/diagnosis/DiagnosisView.vue
git commit -m "feat: add chart dashboard panel to DiagnosisView (heatmap, gauge, evidence)"
```

---

## Phase 3 Bonus: Report Enhancement (Frontend)

**Files:**
- Modify: `app/frontend/src/components/reports/ReportViewer.vue`

- [ ] **Step 1: Add "Interactive Charts" button in report viewer**

In ReportViewer.vue, find the toolbar `div` with `style="margin-left:auto;display:flex;gap:6px;"` at line 100. Add the chart toggle button AFTER the Copy button (line 102):

```vue
          <button class="btn btn-sm" @click="copyReport">Copy</button>
          <button
            v-if="selectedRun && selectedRun.path"
            class="btn btn-sm"
            @click="showChartPanel = !showChartPanel"
          >{{ showChartPanel ? '📊 Hide' : '📊 Charts' }}</button>
```

Then add the chart panel section AFTER `</div>` of the report card (after line 119):

```vue
    <!-- Chart panel (below report) -->
    <div v-if="showChartPanel && chartData" class="card" style="margin-top:12px">
      <div class="card-title">
        <span>📊 Interactive Charts</span>
        <button class="btn btn-sm" @click="showChartPanel = false">Close</button>
      </div>
      <div class="chart-grid">
        <div v-if="chartData.heatmap" class="chart-cell chart-cell-full">
          <HeatmapChart
            :data="chartData.heatmap.data"
            :x-labels="chartData.heatmap.xLabels"
            :y-labels="chartData.heatmap.yLabels"
            title="Correlation Matrix"
          />
        </div>
        <div v-if="chartData.confidence" class="chart-cell chart-cell-half">
          <GaugeChart
            :value="chartData.confidence.overall"
            title="Confidence Score"
            unit="%"
          />
        </div>
      </div>
    </div>
```

Add imports:
```javascript
import { HeatmapChart, GaugeChart } from '../charts/index.js';
```

Add reactive state (with other `const` declarations):
```javascript
const showChartPanel = ref(false);
const chartData = ref(null);
```

Add fetch function:
```javascript
async function fetchChartData(runDir) {
  if (!runDir) return;
  try {
    const dirName = runDir.replace('workspace/diagnostic-runs/', '');
    const res = await fetch(`/api/analysis/chart-data/${encodeURIComponent(dirName)}`);
    const json = await res.json();
    if (json.success && json.data) chartData.value = json.data;
  } catch (err) {
    console.error('Chart fetch failed:', err);
  }
}
```

Call fetchChartData when a report is loaded — in the `watch()` at line 177, add after `reportContent.value = data.content;`:
```javascript
      if (selectedRun.value === requestedName) reportContent.value = data.content;
        // Fetch interactive chart data for this run
        fetchChartData(`workspace/diagnostic-runs/${requestedName}`);
```

- [ ] **Step 2: Commit**

```bash
git add app/frontend/src/components/reports/ReportViewer.vue
git commit -m "feat: add interactive chart panel to ReportViewer"
```

---

## Self-Review

### Phase 1 Coverage
- [x] Winston logger setup (Task 1.1)
- [x] All console.log replaced (Task 1.2 — 7 source files)
- [x] Enhanced /api/health (Task 1.3 — DB status, active runs, uptime)
- [x] Docker multi-stage build (Task 1.4 — frontend builder + backend runtime)
- [x] docker-compose.yml with env vars (Task 1.5)
- [x] nginx.conf (Task 1.6 — optional, committed separately)

### Phase 3 Coverage
- [x] ECharts + vue-echarts installed (Task 3.1)
- [x] 4 chart components: Line, Heatmap, Scatter, Gauge (Task 3.2)
- [x] Chart data API with path traversal protection (Task 3.3)
- [x] Chart dashboard in DiagnosisView (Task 3.4)
- [x] Interactive charts in ReportViewer (Bonus)
