#!/usr/bin/env bash
# A single staging environment. Production resources are never referenced here.
set -Eeuo pipefail
umask 077

sha=${1:?Usage: deploy.sh FULL_DEVELOP_COMMIT_SHA}
[[ $sha =~ ^[0-9a-f]{40}$ ]] || { echo 'Expected a full commit SHA.' >&2; exit 2; }
export TAPME_STAGING_ROOT=${TAPME_STAGING_ROOT:-$HOME/apps/flower-crm-staging}
export TAPME_STAGING_IMAGE_PREFIX=${TAPME_STAGING_IMAGE_PREFIX:-ghcr.io/khasan312/tapme-flowers-crm}
root=$TAPME_STAGING_ROOT
env_file=$root/.env.staging
[[ -f $root/.deploy-enabled ]] || { echo 'Staging deployment is disabled.' >&2; exit 2; }
[[ -r $env_file && $(stat -c '%a' "$env_file") == 600 ]] || { echo 'Staging env must exist with mode 600.' >&2; exit 2; }
export PUBLIC_DOMAIN
PUBLIC_DOMAIN=$(sed -n 's/^PUBLIC_DOMAIN=//p' "$env_file" | tr -d '\r')
[[ $PUBLIC_DOMAIN =~ ^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$ ]] || { echo 'Invalid staging hostname.' >&2; exit 2; }

mkdir -p "$root/state" "$root/backups" "$root/releases/$sha/staging"
exec 9>"$root/state/deploy.lock"
flock -n 9 || { echo 'Another staging deployment is running.' >&2; exit 1; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
release=$root/releases/$sha/staging
for file in compose.yaml Caddyfile deploy.sh; do
    [[ $source_dir == "$release" ]] || install -m 644 "$source_dir/$file" "$release/$file"
done

app() {
    IMAGE_TAG=$sha docker compose --env-file "$env_file" -p flower-crm-staging -f "$release/compose.yaml" "$@"
}
app config --quiet
scratch=$(mktemp -d "$root/.deploy.XXXXXX")
trap 'rm -rf -- "$scratch"' EXIT
if [[ ${TAPME_STAGING_LOCAL_IMAGES:-false} == true ]]; then
    docker image inspect "${TAPME_STAGING_IMAGE_PREFIX}-api:$sha" "${TAPME_STAGING_IMAGE_PREFIX}-web:$sha" >/dev/null
else
    [[ -n ${GHCR_TOKEN:-} ]] || { echo 'Missing registry token.' >&2; exit 2; }
    export DOCKER_CONFIG=$scratch/docker
    mkdir -m 700 "$DOCKER_CONFIG"
    printf '%s' "$GHCR_TOKEN" | docker login ghcr.io --username "${GITHUB_ACTOR:-Khasan312}" --password-stdin >/dev/null
    unset GHCR_TOKEN
    app pull api web
fi

# Pull/validation errors leave the existing application running.
app up -d --wait --wait-timeout 180 postgres redis
backup=$root/backups/$(date -u +%Y%m%dT%H%M%SZ)-$sha.dump
# shellcheck disable=SC2016
app exec -T postgres sh -c 'pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$backup"
[[ -s $backup ]] || { echo 'Database backup is empty.' >&2; exit 1; }

# Staging allows a short maintenance window. No volumes are removed, and
# migrations are never reversed automatically. Keep the backup on any failure.
app stop beat worker web api
app run --rm -T --no-deps api python manage.py migrate --noinput
app run --rm -T --no-deps api python manage.py collectstatic --noinput
app run --rm -T --no-deps api python manage.py bootstrap_business --name 'Flower CRM — тестовый стенд' --username owner
app --profile init run --rm -T --no-deps assets
app up -d --wait --wait-timeout 180 api web worker beat
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8090/health/ \
    | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "ok"'
curl --fail --silent --show-error --max-time 10 -o /dev/null http://127.0.0.1:8090/crm-flowers/
if [[ -f $root/state/current ]]; then
    cp "$root/state/current" "$root/state/previous"
fi
printf '%s\n' "$sha" > "$root/state/current.next"
mv "$root/state/current.next" "$root/state/current"
printf '%s\n' "$TAPME_STAGING_IMAGE_PREFIX" > "$root/state/image-prefix"
echo "Deployed develop commit $sha to staging."
