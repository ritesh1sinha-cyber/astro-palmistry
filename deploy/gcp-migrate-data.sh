#!/usr/bin/env bash
# Copy Railway Postgres (+ optional LOCAL_STORE tarball) into the GCP compose stack.
#
# Usage (on the GCE VM, from the repo root):
#   export RAILWAY_DATABASE_URL='postgresql://…'   # Railway public URL
#   # optional: place railway-storage.tgz in $HOME first
#   bash deploy/gcp-migrate-data.sh
#
# Or restore from an existing dump:
#   DUMP=~/railway.dump bash deploy/gcp-migrate-data.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE=(docker compose -f "$REPO_DIR/deploy/docker-compose.gcp.yml" --env-file "$REPO_DIR/deploy/.env")
DUMP="${DUMP:-$HOME/railway.dump}"
STORAGE_TGZ="${STORAGE_TGZ:-$HOME/railway-storage.tgz}"
PG_USER="${PG_USER:-astro}"
PG_DB="${PG_DB:-astro}"

cd "$REPO_DIR"

if [[ ! -f "$REPO_DIR/deploy/.env" ]]; then
  echo "Missing deploy/.env — copy from deploy/.env.gcp.example first." >&2
  exit 1
fi

echo "==> Ensuring postgres is up"
"${COMPOSE[@]}" up -d postgres
"${COMPOSE[@]}" exec -T postgres pg_isready -U "$PG_USER" >/dev/null

if [[ ! -f "$DUMP" ]]; then
  if [[ -z "${RAILWAY_DATABASE_URL:-}" ]]; then
    echo "No dump at $DUMP and RAILWAY_DATABASE_URL unset." >&2
    echo "  pg_dump --no-owner --no-acl \"\$RAILWAY_DATABASE_URL\" -Fc -f $DUMP" >&2
    exit 1
  fi
  echo "==> Dumping Railway → $DUMP"
  pg_dump --no-owner --no-acl "$RAILWAY_DATABASE_URL" -Fc -f "$DUMP"
fi

echo "==> Restoring $DUMP into compose Postgres ($PG_DB)"
# Clean restore: drop and recreate so role/extension noise from Railway is gone.
"${COMPOSE[@]}" exec -T postgres psql -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 <<SQL
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$PG_DB' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS $PG_DB;
CREATE DATABASE $PG_DB OWNER $PG_USER;
SQL

"${COMPOSE[@]}" exec -T postgres pg_restore --no-owner --no-acl -U "$PG_USER" -d "$PG_DB" \
  < "$DUMP" || true
# pg_restore exits 1 on benign warnings (extensions already present); verify tables:
"${COMPOSE[@]}" exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -c '\dt' | head -40

if [[ -f "$STORAGE_TGZ" ]]; then
  echo "==> Restoring report store from $STORAGE_TGZ"
  VOL=$("${COMPOSE[@]}" volume ls -q | grep reportstore | head -1 || true)
  if [[ -z "$VOL" ]]; then
    # volume name is often <project>_reportstore
    VOL=$(docker volume ls -q | grep -E 'reportstore$' | head -1 || true)
  fi
  if [[ -z "$VOL" ]]; then
    echo "No reportstore volume found — start the api once, then re-run." >&2
    exit 1
  fi
  docker run --rm \
    -v "$VOL":/data \
    -v "$(dirname "$STORAGE_TGZ")":/backup:ro \
    alpine \
    sh -c "mkdir -p /data/storage && tar xzf /backup/$(basename "$STORAGE_TGZ") -C /data"
  "${COMPOSE[@]}" restart api || true
else
  echo "==> No $STORAGE_TGZ — skipping LOCAL_STORE copy (reports may 404 until you add it)"
fi

echo "==> Done. Spot-check:"
echo "    curl -sS https://gcp.graharekha.com/health"
echo "    open https://gcp.graharekha.com and confirm My reports load"
