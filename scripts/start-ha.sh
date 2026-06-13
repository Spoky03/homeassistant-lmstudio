#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required but not installed." >&2
  exit 1
fi

mkdir -p config

echo "Starting Home Assistant (http://127.0.0.1:8123) ..."
docker compose up -d

echo
echo "Custom component mounted from: $ROOT/custom_components/lmstudio"
echo "Add the integration via Settings → Devices & services → Add integration → LM Studio"
echo "Use host 127.0.0.1 and port 2137 for your LM Studio server."
echo
echo "Logs: docker compose logs -f homeassistant"
