#!/bin/sh
set -eu
cd "$(dirname "$0")"

create_env() {
    file=$1
    key=$2
    if [ -f "$file" ]; then return; fi
    umask 077
    tmp=$(mktemp "$file.XXXXXX")
    trap 'rm -f "$tmp"' EXIT
    password=$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')
    [ "${#password}" -eq 64 ]
    printf '%s=%s\n' "$key" "$password" > "$tmp"
    if [ "$file" = .env.vps ]; then printf 'VPS_PORT=80\n' >> "$tmp"; fi
    # Publish a complete file even if two deployments start together.
    ln "$tmp" "$file" || [ -f "$file" ]
    rm -f "$tmp"
    trap - EXIT
}

create_env .env.vps POSTGRES_PASSWORD
create_env .env.vps.demo VPS_DEMO_PASSWORD

if [ "$#" -eq 0 ]; then
    set -- up --build -d --wait frontend
fi
exec docker compose --env-file .env.vps -f compose.yaml -f compose.vps.yaml "$@"
