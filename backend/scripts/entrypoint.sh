#!/bin/sh
set -e

# Wait for PostgreSQL to be ready (fail fast instead of looping forever).
echo "[entrypoint] Waiting for PostgreSQL..."
retries=30
until pg_isready -h postgres -p 5432 -U cda_user; do
  retries=$((retries - 1))
  if [ "$retries" -le 0 ]; then
    echo "[entrypoint] ERROR: PostgreSQL did not become ready in time" >&2
    exit 1
  fi
  sleep 2
done

# Enable the pgvector extension.
echo "[entrypoint] Enabling pgvector extension..."
PGPASSWORD=cda_password psql -h postgres -U cda_user -d cda_db -c "CREATE EXTENSION IF NOT EXISTS vector;" || true

# Run database migrations.
echo "[entrypoint] Running migrations..."
alembic upgrade head

# Seed sample documents (idempotent). Non-fatal: a failed download must not
# prevent the backend from starting.
echo "[entrypoint] Seeding sample documents..."
python -m scripts.seed_documents || echo "[entrypoint] WARNING: seeding failed, continuing without sample documents"

# Start the backend.
echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
