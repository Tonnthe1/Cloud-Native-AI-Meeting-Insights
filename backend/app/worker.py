#!/usr/bin/env python3
"""
Meeting Processing Worker Service

This worker service:
- Pulls tasks from a Redis queue
- Runs faster-whisper transcription, summarization and keyword extraction
- Records the meeting's status (processing/completed/failed) and results in
  the Postgres DB record
- Has retry logic, logging, and a health check endpoint (served from the
  same process so it reflects the worker's real state)

Run from the backend directory with: python -m app.worker
"""

import os
import sys
import logging
import signal
import threading
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import FastAPI

# Make the backend root importable when run as a script (python app/worker.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(
    __file__))))

from app import processing  # noqa: E402
from app.cache import invalidate_meeting_caches  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Meeting, MeetingStatus  # noqa: E402
from app.redis_client import get_redis_client, TaskQueue  # noqa: E402


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
_task_queue: Optional[TaskQueue] = None
_worker_running = False
_worker_thread: Optional[threading.Thread] = None

# FastAPI app for health checks
app = FastAPI(title="Meeting Processing Worker")


def initialize_services():
    """Initialize Redis and other services."""
    global _task_queue

    logger.info("Initializing Redis connection...")
    redis_client = get_redis_client()
    _task_queue = TaskQueue(redis_client)

    # Test Redis connection
    try:
        redis_client.ping()
        logger.info("Redis ping successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise


def _update_meeting(meeting_id: int, update) -> bool:
    """Apply update(meeting) and commit. Returns False if the meeting no
    longer exists (e.g. it was deleted while queued)."""
    db = SessionLocal()
    try:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None:
            return False
        update(meeting)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def set_meeting_status(meeting_id: int, status: str,
                       error_message: Optional[str] = None) -> bool:
    def update(meeting: Meeting):
        meeting.status = status
        meeting.error_message = error_message

    return _update_meeting(meeting_id, update)


def _invalidate_caches():
    if _task_queue is not None:
        invalidate_meeting_caches(_task_queue.redis)


def process_meeting_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single meeting job."""
    job_id = job_data["id"]
    meeting_id = job_data["meeting_id"]
    file_path = job_data["file_path"]

    logger.info(f"Processing job {job_id} for meeting {meeting_id}")

    if not set_meeting_status(meeting_id, MeetingStatus.PROCESSING):
        logger.warning(f"Meeting {meeting_id} no longer exists; "
                       f"skipping job {job_id}")
        return {"skipped": "meeting deleted"}
    _invalidate_caches()

    result = processing.process_audio(file_path)

    if not _update_meeting(meeting_id,
                           lambda m: processing.apply_result(m, result)):
        logger.warning(f"Meeting {meeting_id} was deleted during "
                       f"processing; discarding results of job {job_id}")
        return {"skipped": "meeting deleted"}
    _invalidate_caches()

    logger.info(f"Job {job_id} completed successfully")
    return {
        "transcript_length": len(result.transcript),
        "language": result.language,
        "summary_length": len(result.summary),
        "keywords_count": len(result.keywords),
        "duration_seconds": result.duration_seconds,
    }


def handle_job_failure(job_data: Dict[str, Any], error: Exception) -> None:
    """Record a failed attempt: re-queue the job if it has attempts left,
    and mirror that on the meeting's status."""
    job_id = job_data["id"]
    error_msg = str(error) or error.__class__.__name__
    new_status = _task_queue.fail_job(job_id, error_msg, retry=True)

    retrying = new_status == "queued"
    logger.error(f"Job {job_id} failed "
                 f"({'will retry' if retrying else 'giving up'}): "
                 f"{error_msg}")
    try:
        set_meeting_status(
            job_data["meeting_id"],
            MeetingStatus.QUEUED if retrying else MeetingStatus.FAILED,
            error_message=error_msg,
        )
        _invalidate_caches()
    except Exception:
        logger.exception(f"Could not record failure of job {job_id}")


def worker_loop():
    """Main worker loop that processes jobs from the queue."""

    logger.info("Worker loop started")

    while _worker_running:
        try:
            # Get next job (blocking with timeout)
            job_data = _task_queue.get_next_job()

            if job_data is None:
                # Timeout - continue loop
                continue

            job_id = job_data["id"]
            logger.info(f"Picked up job: {job_id}")

            try:
                result = process_meeting_job(job_data)
                _task_queue.complete_job(job_id, result)
                logger.info(f"Job {job_id} marked as completed")

            except Exception as e:
                logger.exception(f"Job {job_id} raised an error")
                handle_job_failure(job_data, e)

        except Exception:
            logger.exception("Worker loop error")
            # Sleep briefly before retrying
            time.sleep(5)

    logger.info("Worker loop stopped")


def start_worker():
    """Start the worker in a separate thread."""
    global _worker_running, _worker_thread

    if _worker_running:
        logger.warning("Worker already running")
        return

    _worker_running = True
    _worker_thread = threading.Thread(target=worker_loop, daemon=True)
    _worker_thread.start()
    logger.info("Worker thread started")


def stop_worker():
    """Stop the worker thread."""
    global _worker_running

    if not _worker_running:
        return

    logger.info("Stopping worker...")
    _worker_running = False

    if _worker_thread:
        _worker_thread.join(timeout=30)
        if _worker_thread.is_alive():
            logger.warning("Worker thread did not stop gracefully")
        else:
            logger.info("Worker stopped successfully")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    stop_worker()
    sys.exit(0)


# Health check endpoints
@app.get("/health")
def health_check():
    """Health check endpoint."""

    status = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "worker_running": _worker_running,
        "model_loaded": processing.is_model_loaded(),
        "redis_connected": False,
        "queue_length": 0,
        "processing_count": 0
    }

    # Check Redis connection
    try:
        if _task_queue:
            _task_queue.redis.ping()
            status["redis_connected"] = True
            status["queue_length"] = _task_queue.get_queue_length()
            status["processing_count"] = _task_queue.get_processing_count()
    except Exception as e:
        status["redis_error"] = str(e)
        status["status"] = "unhealthy"

    return status


@app.get("/stats")
def get_stats():
    """Get worker statistics."""
    if not _task_queue:
        return {"error": "Queue not initialized"}

    return {
        "queue_length": _task_queue.get_queue_length(),
        "processing_count": _task_queue.get_processing_count(),
        "worker_running": _worker_running,
        "model_loaded": processing.is_model_loaded()
    }


def start_health_server():
    """Serve the health endpoints from a background thread."""
    import uvicorn

    port = int(os.getenv("WORKER_HEALTH_PORT", "8001"))
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=port,
                                           log_level="warning"))
    threading.Thread(target=server.run, name="health-server",
                     daemon=True).start()
    logger.info(f"Health server listening on port {port}")


def main():
    """Main entry point for the worker service."""
    logger.info("Starting Meeting Processing Worker")

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not set - summaries will be "
                           "extractive instead of AI-generated")

        start_health_server()

        # Initialize services
        initialize_services()
        processing.get_whisper_model()

        # Start the worker
        start_worker()

        logger.info("Worker service ready")

        # Keep the main thread alive
        while _worker_running:
            time.sleep(1)

    except Exception:
        logger.exception("Worker initialization failed")
        sys.exit(1)
    finally:
        stop_worker()


if __name__ == "__main__":
    main()
