# syntax=docker/dockerfile:1
# ============================================================
# Industrial Deep Diagnostic — production image (multi-stage)
#
#   frontend-builder  node:22-alpine   build the Vue/Vite SPA
#   web               nginx:1.27-alpine SPA + /api + /ws reverse proxy
#                                      (built as `--target web`; the repo's
#                                       nginx.conf is mounted at runtime)
#   backend-deps      node:22-alpine   npm install with the native toolchain
#   runtime           node:22-alpine   non-root app runtime (DEFAULT target —
#                                      it is the LAST stage, so a bare
#                                      `docker build .` still produces the
#                                      backend image)
#
# Build toolchain (g++/make/py3-pip) exists ONLY in backend-deps: better-sqlite3
# is a native addon (better-sqlite3@12's prebuilt musl binaries are not
# guaranteed), so the compile happens in a stage that is thrown away.
# ============================================================

# ===== Stage 1: Frontend build =====
FROM node:22-alpine AS frontend-builder
WORKDIR /build
COPY app/frontend/package*.json ./frontend/
RUN cd frontend && npm ci
COPY app/frontend/ ./frontend/
# vite.config.js imports '../../config/loader.mjs' → /config/loader.mjs from the
# build root; the config dir is needed for the BUILD only (not copied into web).
COPY config/ /config/
WORKDIR /build/frontend
RUN npm run build

# ===== Stage 2: nginx web tier =====
# Front door of the compose deployment: serves the built SPA and reverse-proxies
# /api + /ws. The repo nginx.conf is NOT baked in — docker-compose.yml mounts it
# at /etc/nginx/conf.d/default.conf so the hardened config stays the single
# source of truth. The SPA dist is baked here so the web container needs no
# host-side build output and no shared volume (see docker-compose.yml).
FROM nginx:1.27-alpine AS web
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist

# ===== Stage 3: Dependencies (native build toolchain lives only here) =====
FROM node:22-alpine AS backend-deps
# python3 (node-gyp) + make/g++ (C++ compile of better-sqlite3). py3-pip is
# pulled in for node-gyp's tooling expectations; none of it reaches runtime.
RUN apk add --no-cache python3 py3-pip make g++
WORKDIR /app
# ROOT package.json first: config/loader.mjs imports js-yaml and node resolves
# bare imports by walking UP from config/ → it needs /app/node_modules. Without
# this install the container dies with `Cannot find package 'js-yaml' imported
# from /app/config/loader.mjs` (the pre-existing image copied package.json but
# never installed it).
COPY package*.json ./
RUN npm ci --omit=dev
# Backend package.json (express/better-sqlite3/the agent SDK/…)
COPY app/backend/package*.json ./app/backend/
RUN cd app/backend && npm ci --omit=dev

# ===== Stage 4: Backend runtime (LAST stage = default `docker build` target) =====
FROM node:22-alpine AS runtime

ENV NODE_ENV=production

# Runtime interpreter question, decided by grep evidence:
#   grep -rn "spawn|execFile|child_process" app/backend/src  → the backend spawns
#     ONLY engine CLIs (claude/omp/codex/… clients); it never spawns python.
#   grep -rn "python|uv " app/backend/src → the only hits are two PROMPT strings
#     (app/backend/src/engine/claude-client.mjs:117,149) that tell an in-container
#     *agent* to run the html/report helper scripts via `uv run … python …`.
#     The harness assets this image DOES ship (.claude/shared/, see below) are
#     node-only .mjs scripts, so the backend still has no python code path.
#     python3 is kept anyway: it is the interpreter a mounted skill tree / engine
#     CLI / extra analysis script would need, it is not a compiler, and it keeps
#     the image functionally equivalent to the previous single-stage build.
#     Delete this line if engines always run on the host (smallest image).
# pip/make/g++ are NOT installed here — they were build-only.
RUN apk add --no-cache python3

WORKDIR /app

# Everything the app reads is owned by the unprivileged `node` user (uid/gid
# 1000 in the official node image — the same ids docker-compose.yml expects for
# the bind-mounted data/ + workspace/).
COPY --chown=node:node config/ ./config/
COPY --chown=node:node commands/ ./commands/
COPY --chown=node:node package.json ./
COPY --from=backend-deps --chown=node:node /app/node_modules ./node_modules
COPY --chown=node:node app/backend/package*.json ./app/backend/
COPY --from=backend-deps --chown=node:node /app/app/backend/node_modules ./app/backend/node_modules
COPY --chown=node:node app/backend/src ./app/backend/src/
COPY --from=frontend-builder --chown=node:node /build/frontend/dist ./app/frontend/dist
# Harness assets the BACKEND loads at runtime (verified: without them the
# container dies on `Cannot find module /app/.claude/shared/scripts/ontology_store.mjs`):
#   app/backend/src/services/ontology.service.mjs:24  → import ontology_store.mjs
#   .claude/shared/scripts/ontology_store.mjs:48      → .claude/skills/industrial-ontology-builder/schemas/ontology_schema.json
#   .claude/shared/scripts/ontology_store.mjs spawns validate.mjs (node, zero deps)
# Everything else under .claude/ (skills, agents, the 370 MB python venv) stays
# out of the image — see .dockerignore.
COPY --chown=node:node .claude/shared/ ./.claude/shared/
COPY --chown=node:node .claude/skills/industrial-ontology-builder/ ./.claude/skills/industrial-ontology-builder/
# NOTE: the previous `COPY data/*.py ./data/` / `COPY data/*.csv ./data/` lines
# are gone — the repo has no data/*.py at all (a non-matching COPY glob is a
# hard build failure) and data/ is a runtime bind mount in compose; the SQLite
# DB is created by the app at ./data/diagnostic.db.

# Writable state dirs with node ownership: a container run without any bind
# mount still works (DB + runs + logs land here), and compose bind mounts must
# be writable by uid 1000 on the host (see docker-compose.yml).
RUN mkdir -p data workspace logs \
 && chown -R node:node /app/data /app/workspace /app/logs

USER node

# Liveness probe = GET /api/health (process up + DB reachable). Readiness
# (dependency health) is GET /api/health/ready — used by compose/nginx/k8s
# style probes, not by HEALTHCHECK: a liveness check must not restart the
# container over a transient dependency hiccup.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:3210/api/health || exit 1

EXPOSE 3210

CMD ["node", "app/backend/src/index.mjs"]
