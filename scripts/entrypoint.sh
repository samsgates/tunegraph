#!/bin/sh
set -eu

if [ "${TUNEGRAPH_RUN_MIGRATIONS:-true}" = "true" ]; then
  alembic upgrade head
fi
exec "$@"
