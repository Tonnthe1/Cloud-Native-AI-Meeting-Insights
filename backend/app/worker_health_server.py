#!/usr/bin/env python3
"""
Health check server for the worker service.
Runs on port 8001 to provide health endpoints.
"""

import os
import uvicorn
from worker import app

if __name__ == "__main__":
    port = int(os.getenv("WORKER_HEALTH_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")