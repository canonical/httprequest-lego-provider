#!/bin/bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

: "${GITHUB_ENV:?This script requires the GitHub Actions environment file}"

container_id=$(docker run --detach --rm \
    --publish 127.0.0.1::5432 \
    --env POSTGRES_USER=lego \
    --env POSTGRES_PASSWORD=local-test-only \
    --env POSTGRES_DB=lego \
    postgres:14)

for ((attempt = 0; attempt < 30; attempt++)); do
    if docker exec "$container_id" pg_isready -h 127.0.0.1 -U lego -d lego; then
        address=$(docker port "$container_id" 5432/tcp)
        echo "POSTGRESQL_DB_CONNECT_STRING=postgresql://lego:local-test-only@${address}/lego" \
            >> "$GITHUB_ENV"
        exit 0
    fi
    sleep 2
done

echo "PostgreSQL 14 did not become ready within 60 seconds." >&2
docker logs "$container_id"
exit 1
