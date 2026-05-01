#!/bin/sh
set -eu

MAX_ATTEMPTS="${DB_WAIT_MAX_ATTEMPTS:-30}"
SLEEP_SECONDS="${DB_WAIT_SLEEP_SECONDS:-2}"
UVICORN_RELOAD="${UVICORN_RELOAD:-true}"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set"
  exit 1
fi

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  if python - <<'PY'
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
with engine.connect() as connection:
    connection.execute(text("SELECT 1"))
PY
  then
    echo "Database is ready"
    break
  fi

  if [ "$attempt" -eq "$MAX_ATTEMPTS" ]; then
    echo "Database did not become ready after $MAX_ATTEMPTS attempts"
    exit 1
  fi

  echo "Database not ready yet, retrying in ${SLEEP_SECONDS}s (${attempt}/${MAX_ATTEMPTS})"
  attempt=$((attempt + 1))
  sleep "$SLEEP_SECONDS"
done

alembic upgrade head

if [ "$UVICORN_RELOAD" = "true" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
