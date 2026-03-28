FROM python:3.11-slim

# Устанавливаем Node.js 20.x напрямую (быстрее чем apt nodejs + 361 зависимость)
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

# Копируем uv из отдельного образа
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# ── Слой зависимостей (кешируется, пока lock-файлы не изменятся) ──
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

RUN npm ci \
  && npm ci --prefix frontend \
  && cd backend && uv sync

# ── Слой исходного кода (тонкий, пересобирается при каждом деплое) ──
COPY . .

EXPOSE 3000 5001

CMD ["npm", "run", "dev"]
