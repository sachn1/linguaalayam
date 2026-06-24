#!/usr/bin/env bash
# Restore the database from the DVC-tracked dump.
#
# Usage:
#   scripts/db_restore.sh              # assumes dump already pulled (linguaalayam.sql.gz present)
#   dvc pull && scripts/db_restore.sh  # pull latest dump first, then restore
#
# Environment variables (all have defaults matching docker-compose.yml):
#   DB_NAME      — target database name (default: linguaalayam)
#   DB_USER      — Postgres superuser      (default: postgres)
#   DB_PASSWORD  — Postgres password       (required unless already set in env)
set -euo pipefail

DB_NAME="${DB_NAME:-linguaalayam}"
DB_USER="${DB_USER:-postgres}"
DUMP_FILE="linguaalayam.sql.gz"

if [[ ! -f "${DUMP_FILE}" ]]; then
    echo "ERROR: ${DUMP_FILE} not found. Run 'dvc pull' first." >&2
    exit 1
fi

echo "Restoring '${DB_NAME}' from ${DUMP_FILE}…"
gunzip --stdout "${DUMP_FILE}" | \
    docker compose exec -T \
        -e PGPASSWORD="${DB_PASSWORD:-}" \
        db psql -U "${DB_USER}" -d "${DB_NAME}"

echo "Done."
