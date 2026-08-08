#!/usr/bin/env bash
# Bootstrap GrahaRekha on a fresh Debian/Ubuntu GCE VM.
# Run as a user with sudo (or root). Idempotent enough to re-run.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/ritesh1sinha-cyber/astro-palmistry.git}"
REPO_DIR="${REPO_DIR:-$HOME/astro-palmistry}"
BRANCH="${BRANCH:-main}"

echo "==> Installing Docker Engine + Compose plugin"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker "${SUDO_USER:-$USER}" || true
fi
systemctl enable --now docker

echo "==> Cloning / updating $REPO_URL → $REPO_DIR"
if [[ -d "$REPO_DIR/.git" ]]; then
  git -C "$REPO_DIR" fetch origin
  git -C "$REPO_DIR" checkout "$BRANCH"
  git -C "$REPO_DIR" pull --ff-only origin "$BRANCH"
else
  git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
fi
# Pull LFS weights for local mounts of site/; image build also pulls LFS.
if command -v git-lfs >/dev/null 2>&1 || apt-get install -y git-lfs; then
  git -C "$REPO_DIR" lfs install
  git -C "$REPO_DIR" lfs pull || true
fi

ENV_FILE="$REPO_DIR/deploy/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$REPO_DIR/deploy/.env.gcp.example" "$ENV_FILE"
  # Generate secrets if still placeholders
  SECRET=$(openssl rand -hex 32)
  PGPW=$(openssl rand -hex 16)
  sed -i "s/^APP_SECRET=.*/APP_SECRET=$SECRET/" "$ENV_FILE"
  sed -i "s/^PG_PASSWORD=.*/PG_PASSWORD=$PGPW/" "$ENV_FILE"
  echo "==> Wrote $ENV_FILE with fresh APP_SECRET / PG_PASSWORD"
  echo "    Edit DOMAIN / ACME_EMAIL / GOOGLE_CLIENT_ID before first up."
else
  echo "==> Keeping existing $ENV_FILE"
fi

cd "$REPO_DIR"
echo "==> Building and starting stack (first build can take 15–25 minutes)"
docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env up -d --build

echo
echo "==> Done. Check:"
echo "    docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env ps"
echo "    curl -sS http://127.0.0.1/health   # via Caddy once DOMAIN resolves"
echo "    docker compose -f deploy/docker-compose.gcp.yml --env-file deploy/.env logs -f api"
