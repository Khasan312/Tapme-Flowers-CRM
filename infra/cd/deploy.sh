#!/usr/bin/env bash
# Invoked by the repository's self-hosted runner as the deploy user.
set -Eeuo pipefail
umask 077

sha=${1:?Usage: deploy.sh FULL_COMMIT_SHA}
[[ $sha =~ ^[0-9a-f]{40}$ ]] || { echo 'Expected a full commit SHA.' >&2; exit 2; }
export TAPME_DEPLOY_ROOT=${TAPME_DEPLOY_ROOT:-/srv/tapme}
root=$TAPME_DEPLOY_ROOT
env_file=$root/.env.production
[[ -f $root/.deploy-enabled ]] || { echo 'Deployment is disabled. Enable it explicitly on the server.'; exit 0; }
[[ -r $env_file ]] || { echo "Missing $env_file" >&2; exit 2; }
[[ $(stat -c '%a' "$env_file") == 600 ]] || { echo 'Production env must have mode 600.' >&2; exit 2; }
export PUBLIC_DOMAIN
PUBLIC_DOMAIN=$(sed -n 's/^PUBLIC_DOMAIN=//p' "$env_file" | tr -d '\r')
[[ $PUBLIC_DOMAIN =~ ^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$ ]] || { echo 'Invalid PUBLIC_DOMAIN.' >&2; exit 2; }
export TAPME_IMAGE_PREFIX=ghcr.io/khasan312/tapme-flowers-crm

mkdir -p "$root/state" "$root/releases" "$root/backups" "$root/gateway"
chmod 755 "$root/gateway"
exec 9>"$root/state/deploy.lock"
flock -n 9 || { echo 'Another deployment is running.' >&2; exit 1; }

old_color=''
old_sha=''
if [[ -f $root/state/current ]]; then
    read -r old_color old_sha < "$root/state/current"
    [[ $old_color =~ ^(blue|green)$ && $old_sha =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid deployment state.' >&2; exit 2; }
    [[ $old_sha != "$sha" ]] || { echo "Already deployed: $sha"; exit 0; }
fi
color=blue
[[ $old_color != blue ]] || color=green
release=$root/releases/$sha
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$release"
for file in core.yaml release.yaml frontend.Caddyfile gateway.Caddyfile check_web_routes.py; do
    install -m 644 "$source_dir/$file" "$release/$file"
done

core() {
    docker compose --env-file "$env_file" -p tapme-core -f "$release/core.yaml" "$@"
}
app() {
    local slot=$1 revision=$2
    shift 2
    COLOR=$slot IMAGE_TAG=$revision docker compose --env-file "$env_file" \
        -p "tapme-$slot" -f "$root/releases/$revision/release.yaml" "$@"
}

scratch=$(mktemp -d "$root/.deployment.XXXXXX")
export DOCKER_CONFIG=$scratch/docker
mkdir -m 700 "$DOCKER_CONFIG"
candidate_started=0 jobs_replaced=0 switched=0 committed=0
[[ ! -f $root/gateway/Caddyfile ]] || cp "$root/gateway/Caddyfile" "$scratch/Caddyfile"
[[ ! -f $root/gateway/active.caddy ]] || cp "$root/gateway/active.caddy" "$scratch/active.caddy"

finish() {
    local status=$?
    trap - EXIT
    if ((status != 0 && committed == 0)); then
        echo 'Deployment failed; preserving the previous release.' >&2
        set +e
        if ((jobs_replaced)); then
            app "$color" "$sha" --profile jobs stop beat worker
            if [[ -n $old_color ]]; then
                app "$old_color" "$old_sha" --profile jobs up -d --wait --wait-timeout 180 worker beat
            fi
        fi
        if ((switched)); then
            if [[ -f $scratch/active.caddy ]]; then
                cp "$scratch/active.caddy" "$root/gateway/active.caddy.rollback"
                mv "$root/gateway/active.caddy.rollback" "$root/gateway/active.caddy"
                cp "$scratch/Caddyfile" "$root/gateway/Caddyfile.rollback"
                mv "$root/gateway/Caddyfile.rollback" "$root/gateway/Caddyfile"
                core exec -T gateway caddy reload --config /etc/caddy/Caddyfile
            else
                core stop gateway
            fi
        fi
        if ((candidate_started)); then
            app "$color" "$sha" --profile jobs stop
        fi
    fi
    rm -rf -- "$scratch"
    exit "$status"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# The short-lived GITHUB_TOKEN is used only for this deployment and removed
# with DOCKER_CONFIG on exit. A personal SSH key is never uploaded to GitHub.
[[ -n ${GHCR_TOKEN:-} ]] || { echo 'Missing short-lived registry token.' >&2; exit 2; }
printf '%s' "$GHCR_TOKEN" | docker login ghcr.io --username "${GITHUB_ACTOR:-Khasan312}" --password-stdin >/dev/null
unset GHCR_TOKEN

echo "Preparing $color release $sha"
core config --quiet
app "$color" "$sha" config --quiet
core up -d --wait --wait-timeout 180 postgres redis
# Only the gateway uses tapme-edge in the core project. Create its container
# without starting or replacing it so Compose provisions that shared network
# before migration containers try to join it on the first deployment.
core create --no-recreate gateway
# Retire only the inactive slot. No command removes persistent volumes.
app "$color" "$sha" --profile jobs down --remove-orphans
app "$color" "$sha" pull api web

backup=$root/backups/$(date -u +%Y%m%dT%H%M%SZ)-$sha.dump
# These variables are deliberately expanded by sh inside PostgreSQL.
# shellcheck disable=SC2016
core exec -T postgres sh -c 'pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "$backup"
[[ -s $backup ]] || { echo 'Database backup is empty.' >&2; exit 1; }
app "$color" "$sha" run --rm -T --no-deps api python manage.py migrate --noinput
app "$color" "$sha" run --rm -T --no-deps api python manage.py collectstatic --noinput --clear
app "$color" "$sha" run --rm -T --no-deps api python manage.py bootstrap_business --name 'Tapme Flowers' --username owner
app "$color" "$sha" --profile init run --rm -T --no-deps assets
candidate_started=1
app "$color" "$sha" up -d --wait --wait-timeout 180 api web

# The old API keeps serving while the new API is checked. Queue workers are
# replaced gracefully, and two beat schedulers are never started together.
jobs_replaced=1
if [[ -n $old_color ]]; then
    app "$old_color" "$old_sha" --profile jobs stop beat worker
fi
app "$color" "$sha" --profile jobs up -d --wait --wait-timeout 180 worker beat

install -m 644 "$release/gateway.Caddyfile" "$root/gateway/Caddyfile.next"
printf 'reverse_proxy tapme-web-%s:80\n' "$color" > "$root/gateway/active.caddy.next"
chmod 644 "$root/gateway/active.caddy.next"
switched=1
mv "$root/gateway/Caddyfile.next" "$root/gateway/Caddyfile"
mv "$root/gateway/active.caddy.next" "$root/gateway/active.caddy"
if [[ -z $(core ps --status running -q gateway) ]]; then
    core up -d --wait --wait-timeout 90 gateway
fi
core exec -T gateway caddy reload --config /etc/caddy/Caddyfile
curl --fail --silent --show-error --retry 5 --retry-connrefused --retry-delay 2 \
    --max-time 10 -H "Host: $PUBLIC_DOMAIN" http://127.0.0.1:8080/health/ \
    | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "ok"'
curl --fail --silent --show-error --max-time 10 -o /dev/null \
    -H "Host: $PUBLIC_DOMAIN" http://127.0.0.1:8080/crm-flowers/
python3 "$release/check_web_routes.py" http://127.0.0.1:8080

if [[ -n $old_color ]]; then
    printf '%s %s\n' "$old_color" "$old_sha" > "$root/state/previous.next"
    mv "$root/state/previous.next" "$root/state/previous"
fi
printf '%s %s\n' "$color" "$sha" > "$root/state/current.next"
mv "$root/state/current.next" "$root/state/current"
committed=1
echo "Deployed $sha in slot $color. Previous web/API containers remain available for recovery."
echo "Public HTTPS also requires DNS for $PUBLIC_DOMAIN to point to this server."
