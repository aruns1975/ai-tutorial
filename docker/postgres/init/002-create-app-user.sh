#!/bin/bash
# Runs automatically on first container start (docker-entrypoint-initdb.d
# scripts, unlike .sql files, can read environment variables). Creates the
# least-privilege role the application connects with, separate from the
# POSTGRES_USER superuser used only to bootstrap the container.
set -euo pipefail

if [ -z "${POSTGRES_APP_USER:-}" ] || [ -z "${POSTGRES_APP_PASSWORD:-}" ]; then
    echo "POSTGRES_APP_USER/POSTGRES_APP_PASSWORD not set — skipping app user creation." >&2
    exit 0
fi

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$POSTGRES_APP_USER') THEN
            CREATE ROLE "$POSTGRES_APP_USER" LOGIN PASSWORD '$POSTGRES_APP_PASSWORD';
        END IF;
    END
    \$\$;

    GRANT ALL PRIVILEGES ON DATABASE "$POSTGRES_DB" TO "$POSTGRES_APP_USER";
    GRANT ALL ON SCHEMA public TO "$POSTGRES_APP_USER";
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "$POSTGRES_APP_USER";
EOSQL
