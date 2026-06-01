# syntax=docker/dockerfile:1.7

# ---------------------------------------------------------------------------
# Stage 1: builder — instala deps + compila wheels
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip wheel \
    && pip install --prefix=/install "."

# ---------------------------------------------------------------------------
# Stage 2: runtime — playwright base + libs
# ---------------------------------------------------------------------------
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:${PATH}" \
    PEM_PLAYWRIGHT_HEADLESS=true

# libpq + tools minimos para asyncpg/psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 tini \
    && rm -rf /var/lib/apt/lists/*

# Copia deps instaladas do builder
COPY --from=builder /install /usr/local

WORKDIR /app
COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY data ./data

# Cria usuario nao-root
RUN groupadd -r pem && useradd -r -g pem -d /app -s /bin/bash pem \
    && mkdir -p /app/storage/snapshots /app/logs \
    && chown -R pem:pem /app
USER pem

EXPOSE 8000 9090
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "pos_editais_monitor.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
