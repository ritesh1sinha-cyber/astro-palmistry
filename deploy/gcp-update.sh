#!/usr/bin/env bash
# Pull latest site + rebuild API image (API code is baked in at docker build, not git pull alone).
set -euo pipefail
cd "$(dirname "$0")/.."
ENV_FILE=deploy/.env
COMPOSE="docker compose -f deploy/docker-compose.gcp.yml --env-file $ENV_FILE"

echo "==> git pull"
git pull

SHA="$(git rev-parse HEAD)"
export RAILWAY_GIT_COMMIT_SHA="$SHA"
echo "==> rebuild API from commit $SHA (invalidates Docker cache for git clone)"
$COMPOSE build --build-arg "RAILWAY_GIT_COMMIT_SHA=$SHA" api
$COMPOSE up -d api

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

echo "==> verify enquiries route inside container"
if $COMPOSE exec -T api python -c "import pathlib; p=pathlib.Path('api.py').read_text(); assert '/api/admin/enquiries' in p" 2>/dev/null; then
  echo "api.py contains /api/admin/enquiries"
else
  echo "ERROR: api.py in container is still old — try: $COMPOSE build --no-cache api && $COMPOSE up -d api"
  exit 1
fi

echo "==> enquiries endpoint"
CODE="$(curl -sS -o /dev/null -w '%{http_code}' https://gcp.graharekha.com/api/admin/enquiries || true)"
echo "GET /api/admin/enquiries -> HTTP $CODE"
if [ "$CODE" = "404" ]; then
  echo "ERROR: still 404 — Caddy may be pointing at an old container; check: $COMPOSE ps"
  exit 1
fi

if grep -q '^SMTP_HOST=$' "$ENV_FILE" 2>/dev/null || ! grep -q '^SMTP_HOST=' "$ENV_FILE" 2>/dev/null; then
  echo ""
  echo "NOTE: SMTP_HOST is empty in $ENV_FILE — contact-form saves to DB but no email is sent."
  echo "Add Titan mail settings, then: $COMPOSE up -d --force-recreate api"
fi

echo "Done."
