#!/usr/bin/env bash
set -euo pipefail

echo "=================================="
echo "Model Forge - Week 1 Test Script"
echo "=================================="
echo ""

# Check prerequisites
echo "==> Checking prerequisites..."

# Check Python
if ! command -v python &> /dev/null; then
    echo "❌ Python is required but not found"
    exit 1
fi
echo "✅ Python: $(python --version)"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not found"
    exit 1
fi
echo "✅ Docker: $(docker --version)"

# Check pip packages
echo ""
echo "==> Installing Python dependencies..."
pip install -r requirements.txt
pip install dbt-duckdb

# Start DataHub
echo ""
echo "==> Starting DataHub (this may take 1-2 minutes)..."
datahub docker quickstart

# Wait for DataHub to be ready
echo "==> Waiting for DataHub to be ready..."
until curl -s http://localhost:8080/health > /dev/null 2>&1; do
    echo "   Waiting..."
    sleep 5
done
echo "✅ DataHub is ready at http://localhost:8080"

# Seed warehouse
echo ""
echo "==> Seeding warehouse..."
cd warehouse
dbt seed
echo "✅ Seeds loaded into DuckDB"

dbt run
echo "✅ Staging models materialized"

dbt docs generate
echo "✅ dbt docs generated (manifest.json + catalog.json)"

cd ..

# Ingest into DataHub
echo ""
echo "==> Ingesting metadata into DataHub..."
datahub ingest -c recipes/ingest.yml
echo "✅ Metadata ingested"

# Test MCP client
echo ""
echo "==> Testing MCP client..."
python -c "
from agent.mcp_client import MCPClient

client = MCPClient()
print('Starting MCP server...')
client.start()
print('Initialization: OK')

print('Listing tools...')
tools = client.list_tools()
print(f'Available tools: {[t[\"name\"] for t in tools]}')

print('Searching for customers...')
result = client.run_tool('search', {'query': 'customers'})
print(f'Search result: {result[:500]}...')

client.stop()
print('✅ MCP client works!')
"

echo ""
echo "=================================="
echo "✅ All Week 1 tests passed!"
echo "=================================="
echo ""
echo "DataHub UI: http://localhost:9002"
echo "DataHub API: http://localhost:8080"
echo ""
echo "You can now test the agent with:"
echo "  python cli.py generate 'Build a customer LTV mart'"
