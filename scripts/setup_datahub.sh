#!/usr/bin/env bash
set -euo pipefail

echo "==> Starting DataHub..."
datahub docker quickstart

echo "==> Seeding warehouse..."
cd ../warehouse
dbt seed
dbt run
dbt docs generate

echo "==> Ingesting into DataHub..."
datahub ingest -c ../recipes/ingest.yml

echo "==> Done. DataHub is running at http://localhost:9002"
