FROM python:3.12-slim AS backend

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY backend/ .
RUN mkdir -p /app/uploads /app/logs

FROM nginx:alpine AS frontend
COPY frontend/dist /usr/share/nginx/html

FROM python:3.12-slim AS final

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Backend Python (deps + código) vindo do stage backend
COPY --from=backend /app /app
COPY --from=backend /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend /usr/local/bin /usr/local/bin

# Frontend dist + nginx config
COPY --from=frontend /usr/share/nginx/html /usr/share/nginx/html
COPY nginx-full.conf /etc/nginx/sites-enabled/default

# Script de start (uvicorn em bg + nginx em fg)
COPY start.sh /start.sh
RUN chmod +x /start.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:80/health || exit 1

CMD ["/start.sh"]
# v2: start.sh replaces supervisord (2026-07-06)
