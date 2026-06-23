#!/usr/bin/env bash
set -euo pipefail

DB_NAME=linguaalayam
DUMP_FILE=linguaalayam.sql.gz

echo "Dumping '${DB_NAME}'..."
# requires pv to track progress - apt-install or brew pv.
docker compose exec -T db pg_dump -v -U postgres -d "${DB_NAME}" --clean --if-exists | pv | gzip > "${DUMP_FILE}"

echo "Pushing to DVC remote..."
poetry run dvc add "${DUMP_FILE}"
poetry run dvc push

echo "Removing local copy (recoverable via 'dvc pull' anytime)..."
rm "${DUMP_FILE}"

echo "Done."
