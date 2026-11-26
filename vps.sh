#!/bin/sh
set -eu
cd "$(dirname "$0")"

if [ ! -f .env.vps ]; then
    umask 077
    tmp=$(mktemp .env.vps.XXXXXX)
    trap 'rm -f "$tmp"' EXIT
    password=$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')
    [ "${#password}" -eq 64 ]
    printf 'POSTGRES_PASSWORD=%s\nVPS_PORT=80\n' "$password" > "$tmp"
    # Publish a complete file even if two deployments start together.
    ln "$tmp" .env.vps || [ -f .env.vps ]
    rm -f "$tmp"
    trap - EXIT
fi

if [ "$#" -eq 0 ]; then
    set -- up --build -d --wait frontend
fi
exec docker compose --env-file .env.vps -f compose.yaml -f compose.vps.yaml "$@"
