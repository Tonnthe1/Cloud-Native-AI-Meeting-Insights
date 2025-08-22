#!/usr/bin/env python3
"""
Meeting Processing Worker Service

This worker service:
- Pulls tasks from a Redis queue
- Runs faster-whisper transcription
- Generates summary using OpenAI
- Updates the Postgres DB record
- Has retry logic, logging, and health check endpoint
"""

import os
import sys
import logging
import traceback
import signal
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import openai
from fastapi import FastAPI
from faster_whisper import WhisperModel
# Add the app directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal
from app.models import Meeting
from app.redis_client import get_redis_client, TaskQueue
from app.util import get_audio_duration_seconds, extract_keywords


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
_fw_model: Optional[WhisperModel] = None
_task_queue: Optional[TaskQueue] = None
_worker_running = False
_worker_thread: Optional[threading.Thread] = None

# FastAPI app for health checks
app = FastAPI(title="Meeting Processing Worker")


def load_whisper_model():
    """Load the faster-whisper model."""
    global _fw_model

    model_name = os.getenv("FW_MODEL", "base.en")
    compute_type = os.getenv("FW_COMPUTE_TYPE", "float32")

    logger.info(f"Loading faster-whisper model: {model_name}")
    _fw_model = WhisperModel(model_name, device="cpu",
                             compute_type=compute_type)
    logger.info("Model loaded successfully")


def initialize_services():
    """Initialize Redis and other services."""
    global _task_queue

    logger.info("Initializing Redis connection...")
    redis_client = get_redis_client()
    _task_queue = TaskQueue(redis_client)
    logger.info("Redis connection established")

    # Test Redis connection
    try:
        redis_client.ping()
        logger.info("Redis ping successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise


def _to_wav_16k_mono(src: Path) -> Path:
    """Convert audio file to 16kHz mono WAV format."""
    import subprocess

    wav = src.with_suffix(".wav")
    cmd = ["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1",
           str(wav)]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        logger.info(f"Converted {src} to {wav}")
        return wav
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed: {e.stderr.decode()}")
        raise


def transcribe_audio(file_path: str) -> tuple[str, Optional[str]]:
    """Transcribe audio file using faster-whisper."""
    if _fw_model is None:
        raise RuntimeError("faster-whisper model not loaded")

    src_path = Path(file_path)
    if not src_path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    logger.info(f"Starting transcription of {file_path}")

    # Convert to WAV format
    wav_path = _to_wav_16k_mono(src_path)

    try:
        # Transcribe
        segments, info = _fw_model.transcribe(
            str(wav_path),
            beam_size=5,
            vad_filter=True,
        )

        # Extract text and language
        parts = [seg.text for seg in segments]
        transcript = " ".join(parts).strip()
        language = getattr(info, "language", None)

        logger.info(f"Transcription completed. Language: {language}, "
                    f"Length: {len(transcript)} chars")
        return transcript, language

    finally:
        # Clean up temporary WAV file
        if wav_path.exists() and wav_path != src_path:
            wav_path.unlink()


def generate_summary(transcript: str) -> str:
    """Generate summary using OpenAI."""
    if not transcript.strip():
        return ""

    logger.info("Generating summary with OpenAI")

    prompt = (
        "Summarize the following meeting transcript in bullet points, "
        "highlight action items, key decisions, and follow-up tasks. "
        "Use clear English. Transcript:\n"
        + transcript
    )

    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a meeting assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=512
        )

        summary = completion.choices[0].message.content or ""
        logger.info(f"Summary generated: {len(summary)} chars")
        return summary

    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return "Summary generation failed"


def update_meeting_record(meeting_id: int, transcript: str, summary: str,
                          language: Optional[str], duration: Optional[float],
                          keywords: Optional[str]) -> bool:
    """Update the meeting record in the database."""
    db = SessionLocal()
    try:
        meeting = db.get(Meeting, meeting_id)
        if not meeting:
            logger.error(f"Meeting {meeting_id} not found in database")
            return False

        # Update fields
        meeting.transcript = transcript
        meeting.summary = summary
        if language:
            meeting.language = language
        if duration is not None:
            meeting.duration_seconds = duration
        if keywords:
            meeting.keywords = keywords

        db.commit()
        logger.info(f"Meeting {meeting_id} updated successfully")
        return True

    except Exception as e:
        logger.error(f"Database update failed for meeting {meeting_id}: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def process_meeting_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single meeting job."""
    job_id = job_data["id"]
    meeting_id = job_data["meeting_id"]
    file_path = job_data["file_path"]

    logger.info(f"Processing job {job_id} for meeting {meeting_id}")

    try:
        # Transcribe audio
        transcript, language = transcribe_audio(file_path)

        # Generate summary
        summary = generate_summary(transcript)

        # Extract keywords
        keywords_list = extract_keywords(transcript, top_k=8)
        keywords_str = ",".join(keywords_list) if keywords_list else None

        # Get audio duration
        duration = get_audio_duration_seconds(file_path)

        # Update database
        success = update_meeting_record(
            meeting_id, transcript, summary, language, duration, keywords_str
        )

        if not success:
            raise Exception("Failed to update database record")

        result = {
            "transcript_length": len(transcript),
            "language": language,
            "summary_length": len(summary),
            "keywords_count": len(keywords_list) if keywords_list else 0,
            "duration_seconds": duration
        }

        logger.info(f"Job {job_id} completed successfully")
        return result

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        logger.error(traceback.format_exc())
        raise


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
                # Process the job
                result = process_meeting_job(job_data)

                # Mark as completed
                _task_queue.complete_job(job_id, result)
                logger.info(f"Job {job_id} marked as completed")

            except Exception as e:
                # Mark as failed (with retry if attempts remaining)
                error_msg = str(e)
                _task_queue.fail_job(job_id, error_msg, retry=True)
                logger.error(f"Job {job_id} failed: {error_msg}")

        except KeyboardInterrupt:
            logger.info("Worker interrupted by user")
            break
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            logger.error(traceback.format_exc())
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
        "model_loaded": _fw_model is not None,
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
        "model_loaded": _fw_model is not None
    }


def main():
    """Main entry point for the worker service."""
    logger.info("Starting Meeting Processing Worker")

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Initialize OpenAI
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            logger.warning("OPENAI_API_KEY not set - summary generation "
                           "will fail")

        # Initialize services
        initialize_services()
        load_whisper_model()

        # Start the worker
        start_worker()

        logger.info("Worker service ready")

        # Keep the main thread alive
        while _worker_running:
            time.sleep(1)

    except Exception as e:
        logger.error(f"Worker initialization failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        stop_worker()


if __name__ == "__main__":
    main()
