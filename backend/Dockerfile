# SentinelOps backend — FastAPI + uvicorn
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# App source.
COPY app ./app

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Liveness probe against /health on the active port (PORT injected by the platform,
# else 8000 for local/compose).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request,sys; p=os.getenv('PORT','8000'); sys.exit(0 if urllib.request.urlopen(f'http://localhost:{p}/health', timeout=4).status == 200 else 1)"

# Bind the platform-provided $PORT when present (Render/Fly/etc.), defaulting to
# 8000 for local + docker-compose. Shell form so $PORT is expanded at runtime.
# SIM_AUTOSTART keeps the demo engine running; override via env in production.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
