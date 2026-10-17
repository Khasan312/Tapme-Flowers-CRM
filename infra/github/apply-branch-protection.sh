#!/usr/bin/env bash
# Requires GitHub Pro for this private repository; never changes visibility.
set -euo pipefail
repo=${1:-Khasan312/Tapme-Flowers-CRM}
config_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
for branch in main develop; do
    gh api --method PUT "repos/$repo/branches/$branch/protection" \
        --input "$config_dir/$branch-protection.json" --silent
    echo "GitHub protection for $repo/$branch is enabled, including administrators."
done
