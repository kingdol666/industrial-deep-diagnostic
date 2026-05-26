# ===== Stage 1: Frontend build =====
FROM node:22-alpine AS frontend-builder
WORKDIR /build
COPY app/frontend/package*.json ./frontend/
RUN cd frontend && npm ci
COPY app/frontend/ ./frontend/
COPY config/ /config/
WORKDIR /build/frontend
RUN npm run build

# ===== Stage 2: Backend runtime =====
FROM node:22-alpine

RUN apk add --no-cache python3 py3-pip

WORKDIR /app

# Copy backend dependencies
COPY app/backend/package*.json ./app/backend/
RUN cd app/backend && npm ci --production

# Copy config
COPY config/ ./config/

# Copy commands
COPY commands/ ./commands/

# Copy data scripts
COPY data/*.py ./data/
COPY data/*.csv ./data/
COPY package.json ./

# Copy built frontend from stage 1
COPY --from=frontend-builder /build/frontend/dist ./app/frontend/dist

# Copy backend source
COPY app/backend/src ./app/backend/src/

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3210/api/health || exit 1

EXPOSE 3210

CMD ["node", "app/backend/src/index.mjs"]
