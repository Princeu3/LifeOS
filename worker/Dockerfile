# LifeOS worker — Procrastinate (no BuildKit mounts; Railway's builder rejects them).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app
COPY pyproject.toml ./
RUN uv sync
COPY . /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app
# Apply the Procrastinate schema (errors if already applied -> `|| true`), then run the worker.
CMD ["sh", "-c", "procrastinate --app=worker.app schema --apply || true; exec procrastinate --app=worker.app worker"]
