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

# Force CPU-only torch and speed up uv
ENV UV_EXTRA_INDEX_URL="https://download.pytorch.org/whl/cpu"
ENV UV_LINK_MODE="copy"

# Copy uv binary into the stage
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/
COPY backend/pyproject.toml backend/uv.lock ./
# Use --no-dev and --no-install-project to cache heavy ML dependencies (torch, etc.)
RUN uv sync --no-dev --no-install-project

# --- Stage 3: Final Runtime ---
FROM python:3.11-slim
WORKDIR /app

# Install minimal Node.js runtime and process management for concurrently
RUN apt-get update && apt-get install -y --no-install-recommends curl procps \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && npm install -g concurrently \
  && rm -rf /var/lib/apt/lists/*

# Copy uv binary into the final stage as it is used by the concurrently runner
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# 1. СНАЧАЛА копируем весь ваш исходный код
COPY . .

# 2. ЗАТЕМ копируем собранные зависимости (чтобы локальные файлы их не затерли)
COPY --from=uv-builder /app/backend/.venv /app/backend/.venv
COPY --from=frontend-builder /app/frontend/node_modules /app/frontend/node_modules
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Устанавливаем пакеты для корневой папки (на всякий случай, если они нужны для запуска)
RUN npm install

# Set environment variables to use the virtual environment
ENV PATH="/app/backend/.venv/bin:$PATH"

EXPOSE 3000 5001

# Запускаем наш сервер!
CMD ["npm", "run", "dev"]