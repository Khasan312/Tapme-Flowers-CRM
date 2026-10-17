#!/usr/bin/env bash
# Requires GitHub Pro for this private repository; never changes visibility.
set -euo pipefail
repo=${1:-Khasan312/Tapme-Flowers-CRM}
config_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
gh api --method PUT "repos/$repo/branches/main/protection" \
    --input "$config_dir/main-protection.json" --silent
echo "GitHub protection for $repo/main is enabled, including administrators."
