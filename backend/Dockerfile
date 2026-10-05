FROM python:3.13-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
ENV PATH="/app/.venv/bin:$PATH"
RUN useradd --create-home app && mkdir -p /data/media /data/celery /data/static && chown -R app:app /data
ENV TAPME_MEDIA_ROOT=/data/media
COPY --chown=app:app . .
USER app
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "--access-logformat", "%(h)s %(s)s %(D)s"]
