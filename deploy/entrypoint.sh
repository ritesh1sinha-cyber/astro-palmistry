#!/bin/sh
# Optional: install Swiss Ephemeris data from a mounted volume at boot.
# Set EPHE_PATH=/data/ephe and drop the *.se1 files there for JHora parity.
set -e

if [ -n "$EPHE_PATH" ] && ls "$EPHE_PATH"/*.se1 >/dev/null 2>&1; then
  DEST="/usr/local/lib/python3.12/site-packages/jhora/data/ephe"
  mkdir -p "$DEST"
  cp "$EPHE_PATH"/*.se1 "$DEST"/
  echo "[entrypoint] installed $(ls "$EPHE_PATH"/*.se1 | wc -l) ephemeris files"
else
  echo "[entrypoint] no ephemeris files (set EPHE_PATH for JHora-exact positions)"
fi

exec "$@"
