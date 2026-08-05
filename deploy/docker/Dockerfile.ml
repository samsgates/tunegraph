# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.8.3 AS uv
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04 AS builder
COPY --from=uv /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends python3.12 python3.12-venv ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV UV_PYTHON=python3.12 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv sync --no-dev --extra ml --no-editable

FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04
RUN apt-get update && apt-get install -y --no-install-recommends python3.12 ca-certificates \
    && groupadd --system --gid 10001 tunegraph \
    && useradd --system --uid 10001 --gid tunegraph --home /app tunegraph \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder --chown=tunegraph:tunegraph /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER tunegraph
CMD ["tunegraph-worker"]
