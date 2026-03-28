# --- Stage 1: Frontend Build ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Backend Dependencies ---
FROM python:3.11-slim AS uv-builder
WORKDIR /app/backend
# Copy uv binary into the stage
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/
COPY backend/pyproject.toml backend/uv.lock ./
# Use --no-dev and --no-install-project to cache heavy ML dependencies (torch, etc.)
RUN uv sync --no-dev --no-install-project

# --- Stage 3: Final Runtime ---
FROM python:3.11-slim
WORKDIR /app

# Install minimal Node.js runtime for the root concurrently runner
RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

# Copy pre-built virtual environment and frontend dist
COPY --from=uv-builder /app/backend/.venv /app/backend/.venv
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Copy application source code
COPY . .

# Set environment variables to use the virtual environment
ENV PATH="/app/backend/.venv/bin:$PATH"

EXPOSE 3000 5001

# Note: npm run dev will still work but now benefits from pre-cached layers
CMD ["npm", "run", "dev"]
