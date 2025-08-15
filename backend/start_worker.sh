#!/bin/bash

# Start the health check server in the background
python app/worker_health_server.py &

# Wait a moment for health server to start
sleep 2

# Start the main worker process (this will run in foreground)
exec python app/worker.py