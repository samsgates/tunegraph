# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.13.1 AS uv
FROM python:3.13-slim AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv sync --no-dev --no-editable

FROM python:3.13-slim AS runtime
RUN groupadd --system --gid 10001 tunegraph \
    && useradd --system --uid 10001 --gid tunegraph --home /app tunegraph
WORKDIR /app
COPY --from=builder --chown=tunegraph:tunegraph /app/.venv /app/.venv
COPY --chown=tunegraph:tunegraph alembic alembic
COPY --chown=tunegraph:tunegraph alembic.ini ./
COPY --chown=tunegraph:tunegraph scripts/entrypoint.sh /entrypoint.sh
RUN chmod 0555 /entrypoint.sh && mkdir -p /app/var/artifacts && chown -R tunegraph:tunegraph /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER tunegraph
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "tunegraph.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
