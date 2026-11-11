#!/usr/bin/env bash
set -euo pipefail
root=${TAPME_STAGING_ROOT:-$HOME/apps/flower-crm-staging}
mkdir -p "$root/state"
exec 8>"$root/state/runner.lock"
flock -n 8 || exit 0
cd "$root/runner"
exec ./run.sh
