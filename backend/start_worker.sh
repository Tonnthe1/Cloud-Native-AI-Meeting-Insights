#!/bin/bash
# The worker serves its health endpoint (WORKER_HEALTH_PORT, default 8001)
# from the same process, so a single command starts everything.
exec python -m app.worker
