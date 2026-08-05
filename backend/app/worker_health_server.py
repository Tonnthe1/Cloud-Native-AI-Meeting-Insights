#!/usr/bin/env python3
"""Health server for the background worker process."""

import os
from datetime import datetime, timezone
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Response, status

READY_FILE = Path(os.getenv("WORKER_READY_FILE", "/tmp/meeting-worker-ready"))
app = FastAPI(title="Meeting Worker Health")


@app.get("/live")
def live() -> dict[str, str]:
    return {
        "status": "live",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready(response: Response) -> dict[str, object]:
    is_ready = READY_FILE.exists()
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if is_ready else "starting",
        "worker_ready": is_ready,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
def health(response: Response) -> dict[str, object]:
    return ready(response)


if __name__ == "__main__":
    port = int(os.getenv("WORKER_HEALTH_PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
