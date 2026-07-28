#!/usr/bin/env python3
"""Background worker for durable meeting transcription and insight extraction."""

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from faster_whisper import WhisperModel

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db import SessionLocal  # noqa: E402
from app.insights import generate_insights  # noqa: E402
from app.models import Meeting  # noqa: E402
from app.redis_client import TaskQueue, get_redis_client  # noqa: E402
from app.storage import (  # noqa: E402
    ObjectStore,
    get_object_store,
    should_delete_audio_after_processing,
)
from app.util import extract_keywords, get_audio_duration_seconds  # noqa: E402

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

READY_FILE = Path(os.getenv("WORKER_READY_FILE", "/tmp/meeting-worker-ready"))
_fw_model: Optional[WhisperModel] = None
_task_queue: Optional[TaskQueue] = None
_object_store: Optional[ObjectStore] = None
_worker_running = False
_worker_thread: Optional[threading.Thread] = None


def load_whisper_model() -> None:
    global _fw_model
    model_name = os.getenv("FW_MODEL", "small")
    compute_type = os.getenv("FW_COMPUTE_TYPE", "int8")
    device = os.getenv("FW_DEVICE", "cpu")
    logger.info("Loading faster-whisper model=%s device=%s", model_name, device)
    _fw_model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
    )


def initialize_services() -> None:
    global _task_queue, _object_store
    client = get_redis_client()
    client.ping()
    _task_queue = TaskQueue(client)
    _object_store = get_object_store()


def _to_wav_16k_mono(src: Path) -> Path:
    wav = src.with_name(f"{src.stem}-{int(time.time())}.wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(wav)],
        check=True,
        capture_output=True,
    )
    return wav


def transcribe_audio(file_path: str) -> tuple[str, Optional[str]]:
    if _fw_model is None:
        raise RuntimeError("faster-whisper model not loaded")
    source = Path(file_path)
    if not source.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    wav_path = _to_wav_16k_mono(source)
    try:
        segments, info = _fw_model.transcribe(
            str(wav_path),
            beam_size=int(os.getenv("WHISPER_BEAM_SIZE", "5")),
            vad_filter=True,
            language=os.getenv("WHISPER_LANGUAGE") or None,
        )
        transcript = " ".join(segment.text.strip() for segment in segments).strip()
        return transcript, getattr(info, "language", None)
    finally:
        wav_path.unlink(missing_ok=True)


def _set_status(meeting_id: int, status: str) -> None:
    db = SessionLocal()
    try:
        meeting = db.get(Meeting, meeting_id)
        if meeting:
            meeting.processing_status = status
            db.commit()
    finally:
        db.close()


def update_meeting_record(
    meeting_id: int,
    transcript: str,
    language: Optional[str],
    duration: Optional[float],
    keywords: Optional[str],
    insights: Dict[str, Any],
) -> None:
    db = SessionLocal()
    try:
        meeting = db.get(Meeting, meeting_id)
        if not meeting:
            raise RuntimeError(f"Meeting {meeting_id} not found")
        meeting.transcript = transcript
        meeting.summary = insights.get("overview", "")
        meeting.insights_json = json.dumps(insights, ensure_ascii=False)
        meeting.insight_provider = insights.get("provider")
        meeting.processing_status = "completed"
        meeting.language = language or meeting.language
        meeting.duration_seconds = duration
        meeting.keywords = keywords
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _delete_source_after_success(meeting_id: int, object_key: str) -> bool:
    if not should_delete_audio_after_processing() or _object_store is None:
        return False

    try:
        _object_store.delete(object_key)
    except Exception as exc:
        logger.warning("Raw audio cleanup failed for %s: %s", object_key, exc)
        return False

    db = SessionLocal()
    try:
        meeting = db.get(Meeting, meeting_id)
        if meeting and meeting.audio_object_key == object_key:
            meeting.audio_object_key = None
            db.commit()
        return True
    except Exception as exc:
        db.rollback()
        logger.warning(
            "Raw audio was deleted but database cleanup failed for meeting %s: %s",
            meeting_id,
            exc,
        )
        return False
    finally:
        db.close()


def process_meeting_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    meeting_id = int(job_data["meeting_id"])
    object_key = job_data.get("object_key")
    if not object_key:
        raise ValueError("Queued meeting job is missing object_key")
    if _object_store is None:
        raise RuntimeError("Object storage unavailable")

    _set_status(meeting_id, "processing")
    try:
        with _object_store.materialize(object_key) as source_path:
            transcript, language = transcribe_audio(str(source_path))
            insights = generate_insights(transcript).to_dict()
            keywords_list = extract_keywords(transcript, top_k=8)
            duration = get_audio_duration_seconds(str(source_path))
        update_meeting_record(
            meeting_id=meeting_id,
            transcript=transcript,
            language=language,
            duration=duration,
            keywords=",".join(keywords_list) or None,
            insights=insights,
        )
        source_deleted = _delete_source_after_success(meeting_id, object_key)
        return {
            "meeting_id": meeting_id,
            "transcript_length": len(transcript),
            "language": language,
            "duration_seconds": duration,
            "insight_provider": insights.get("provider"),
            "action_items": len(insights.get("action_items", [])),
            "raw_audio_deleted": source_deleted,
        }
    except Exception:
        _set_status(meeting_id, "failed")
        raise


def worker_loop() -> None:
    logger.info("Worker loop started")
    while _worker_running:
        try:
            if _task_queue is None:
                raise RuntimeError("Task queue unavailable")
            job_data = _task_queue.get_next_job()
            if job_data is None:
                continue
            job_id = job_data["id"]
            try:
                result = process_meeting_job(job_data)
                _task_queue.complete_job(job_id, result)
            except Exception as exc:
                logger.error("Job %s failed: %s", job_id, exc)
                logger.debug(traceback.format_exc())
                _task_queue.fail_job(job_id, str(exc), retry=True)
        except Exception as exc:
            logger.error("Worker loop error: %s", exc)
            time.sleep(5)


def start_worker() -> None:
    global _worker_running, _worker_thread
    if _worker_running:
        return
    _worker_running = True
    _worker_thread = threading.Thread(target=worker_loop, daemon=True)
    _worker_thread.start()


def stop_worker() -> None:
    global _worker_running
    _worker_running = False
    READY_FILE.unlink(missing_ok=True)
    if _worker_thread:
        _worker_thread.join(timeout=30)


def signal_handler(signum, _frame) -> None:
    logger.info("Received signal %s", signum)
    stop_worker()
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    READY_FILE.unlink(missing_ok=True)
    try:
        initialize_services()
        load_whisper_model()
        start_worker()
        READY_FILE.write_text("ready\n", encoding="utf-8")
        logger.info("Worker is ready")
        while _worker_running:
            time.sleep(1)
    except Exception as exc:
        logger.error("Worker initialization failed: %s", exc)
        logger.debug(traceback.format_exc())
        sys.exit(1)
    finally:
        stop_worker()


if __name__ == "__main__":
    main()
