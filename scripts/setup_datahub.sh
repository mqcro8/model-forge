#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting DataHub..."
echo "This will take 1-2 minutes on first run..."
datahub docker quickstart

echo "==> Waiting for DataHub to be ready..."
until curl -s http://localhost:8080/health > /dev/null 2>&1; do
    sleep 2
done
echo "DataHub is ready at http://localhost:8080"

echo "==> Installing dbt-duckdb..."
pip install dbt-duckdb

echo "==> Seeding warehouse..."
cd warehouse
dbt seed
dbt run
dbt docs generate
cd ..

echo "==> Ingesting into DataHub..."
datahub ingest -c recipes/ingest.yml

echo "==> Done!"
echo "DataHub UI: http://localhost:9002"
echo "DataHub GMS API: http://localhost:8080"
