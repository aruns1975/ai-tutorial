# Sourced by other scripts — provides resolve_env().
#
# .env documents every variable the app/infra uses, but sensitive values
# are never hardcoded there. Instead they're indirected to an external
# environment variable, e.g.:
#
#   POSTGRES_APP_PASSWORD=${RAG_DEMO_PG_APP_PASSWORD:-}
#
# resolve_env() finds every such ${EXTERNAL_VAR} reference in a given
# .env file. It first loads any previously-answered values from a
# gitignored .env.local sitting next to it, then — for anything still
# unset — prompts once (masking input for anything password/secret/key
# -like), exports it, and appends it to .env.local so future runs don't
# ask again. Finally it sources the .env file so the indirected keys
# (POSTGRES_APP_PASSWORD above) resolve to the now-exported values.
resolve_env() {
    local env_file="$1"
    [ -f "$env_file" ] || return 0

    local local_file
    local_file="$(dirname "$env_file")/.env.local"

    if [ -f "$local_file" ]; then
        set -a
        # shellcheck disable=SC1090
        source "$local_file"
        set +a
    fi

    local external_vars
    external_vars=$(
        grep -vE '^\s*#' "$env_file" \
            | grep -oE '\$\{[A-Za-z_][A-Za-z0-9_]*(:-[^}]*)?\}' \
            | sed -E 's/\$\{([A-Za-z_][A-Za-z0-9_]*).*/\1/' \
            | sort -u
    )

    local var value
    for var in $external_vars; do
        if [ -z "${!var:-}" ]; then
            if [[ "$var" == *PASSWORD* || "$var" == *SECRET* || "$var" == *KEY* ]]; then
                read -r -s -p "Enter value for $var (not set, will be saved to .env.local): " value
                echo
            else
                read -r -p "Enter value for $var (not set, will be saved to .env.local): " value
            fi
            export "$var=$value"
            printf '%s=%s\n' "$var" "$value" >> "$local_file"
        fi
    done

    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
}
