#!/usr/bin/env bash
# Pull latest site + rebuild API image (API code is baked in at docker build, not git pull alone).
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE=deploy/.env
COMPOSE="docker compose -f deploy/docker-compose.gcp.yml --env-file $ENV_FILE"

echo "==> git pull"
git pull

echo "==> rebuild + restart API (picks up new api.py from GitHub)"
$COMPOSE up -d --build api

echo "==> refresh Caddy static site"
$COMPOSE up -d --force-recreate caddy

echo "==> wait for health"
for i in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:3000/health >/dev/null 2>&1 || \
     curl -fsS https://gcp.graharekha.com/health >/dev/null 2>&1; then
    echo "health OK"
    break
  fi
  sleep 10
done

echo "==> enquiries endpoint"
curl -sS -o /dev/null -w "GET /api/admin/enquiries -> HTTP %{http_code}\n" \
  https://gcp.graharekha.com/api/admin/enquiries || true

if grep -q '^SMTP_HOST=$' "$ENV_FILE" 2>/dev/null || ! grep -q '^SMTP_HOST=' "$ENV_FILE" 2>/dev/null; then
  echo ""
  echo "NOTE: SMTP_HOST is empty in $ENV_FILE — contact-form saves to DB but no email is sent."
  echo "Add Titan mail settings, then: $COMPOSE up -d --force-recreate api"
fi

echo "Done."
