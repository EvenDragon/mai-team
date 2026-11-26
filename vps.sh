#!/bin/sh
set -eu
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo 'Нужен файл .env в корне проекта с действующим POSTGRES_PASSWORD.' >&2
    exit 1
fi

base_compose() {
    set -- --env-file .env -f compose.yaml -f compose.vps.yaml "$@"
    if [ -f .env.https ]; then
        set -- --env-file .env.https "$@"
    fi
    docker compose "$@"
}

# Let Compose resolve quoting, interpolation and env-file precedence.
service=$(base_compose config --environment | awk '
    /^VPS_PUBLIC_IPV4=./ { https = 1 }
    END { print (https ? "https" : "frontend") }
')

compose() {
    if [ "$service" = https ]; then set -- -f compose.https.yaml "$@"; fi
    base_compose "$@"
}

case "${1:-}" in
    moderator)
        if [ "$#" -ne 2 ] || [ -z "$2" ]; then
            echo 'Использование: sudo sh vps.sh moderator email@example.com' >&2
            exit 2
        fi
        compose exec -T backend python -m app.make_moderator "$2"
        ;;
    "")
        # Older deployments initialized this volume with the password in .env.vps.
        if [ -f .env.vps ]; then
            compose up -d --wait db
            compose exec -T db sh -ec '
                export PGPASSWORD="$POSTGRES_PASSWORD"
                if psql -Xw -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -qc "SELECT 1" >/dev/null 2>&1; then
                    exit 0
                fi
                printf "%s\n%s\n" "$PGPASSWORD" "$PGPASSWORD" |
                    psql -Xw -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\password"
            '
        fi
        compose up --build -d --wait "$service"
        ;;
    *) compose "$@" ;;
esac
