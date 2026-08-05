#!/bin/bash

set -euo pipefail

# Start the health check server in the background
python -m app.worker_health_server &

# Wait a moment for health server to start
sleep 2

# Start the main worker process (this will run in foreground)
exec python -m app.worker
