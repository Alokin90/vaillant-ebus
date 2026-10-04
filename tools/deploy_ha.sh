#!/usr/bin/env bash
# Deploy the integration to Home Assistant: run the CI-equivalent checks, then tools/deploy_ha.py (SSH, credentials from .env).
# Usage: tools/deploy_ha.sh [--restart] [--skip-validate] [--dry-run] [--accept-new-host-key]
# Restarting Home Assistant is better done with the HA-MCP `ha_restart` tool; --restart uses `sudo -n ha core restart`.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=".venv/Scripts/python"
[ -x "$PY" ] || PY=".venv/bin/python"

skip_validate=0
args=()
for arg in "$@"; do
  if [ "$arg" = "--skip-validate" ]; then skip_validate=1; else args+=("$arg"); fi
done

if [ "$skip_validate" -eq 0 ]; then
  "$PY" tools/validate.py
fi

"$PY" tools/deploy_ha.py "${args[@]}"
