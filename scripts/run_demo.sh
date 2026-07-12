#!/usr/bin/env bash
set -euo pipefail

echo "==> Model Forge Demo"
echo ""

python cli.py generate "Build a customer LTV mart showing total spend per customer over the last 12 months" --skip-pr --skip-writeback

echo ""
echo "==> Demo complete."
