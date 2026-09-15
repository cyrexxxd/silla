#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
mkdir -p logs
python -u -m src.sync 2>&1 | tee "logs/sync_$(date +%F_%H%M%S).log"
