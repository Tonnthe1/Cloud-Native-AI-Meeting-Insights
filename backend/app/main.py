import logging
import os
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import (FastAPI, File, UploadFile, HTTPException, Depends,
                     status, Request, Query)
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import processing
from app.cache import CacheService
from app.db import SessionLocal, engine, Base
from app.models import Meeting, MeetingStatus
from app.redis_client import get_redis_client, TaskQueue
from app.schemas import MeetingListItem, MeetingDetail
from app.util import env_bool, env_list

load_dotenv()  # Load .env
load_dotenv(".env.local", override=True)  # Load .env.local with override

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "app/uploads"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))
USE_WORKER_SERVICE = env_bool("USE_WORKER_SERVICE", default=True)
DEBUG = env_bool("DEBUG")
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))
CORS_ORIGINS = env_list("CORS_ORIGINS",
                        "http://localhost:3000,http://127.0.0.1:3000")

ALLOWED_AUDIO_EXTENSIONS = {
    ".aac", ".flac", ".m4a", ".mp3", ".mp4", ".mpeg", ".mpga", ".oga",
    ".ogg", ".opus", ".wav", ".webm", ".wma",
}
_UPLOAD_CHUNK_BYTES = 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    # Run database migrations
    try:
        from app.migrations.migrate import run_migrations
        run_migrations()
    except Exception as e:
        logger.warning(f"Migration failed: {e}")

    # Short timeouts: when Redis is down, requests should fall back quickly
    # (no caching, synchronous processing) instead of hanging.
    redis_client = get_redis_client(socket_connect_timeout=1,
                                    socket_timeout=2)
    app.state.task_queue = TaskQueue(redis_client)
    app.state.cache = CacheService(redis_client,
                                   default_ttl=CACHE_TTL_SECONDS)
    try:
        redis_client.ping()
        logger.info("Redis connected: task queue and cache enabled")
    except Exception as e:
        logger.warning(f"Redis unavailable ({e}); uploads are processed "
                       "synchronously and responses are not cached until "
                       "it becomes reachable")

    if not USE_WORKER_SERVICE:
        await run_in_threadpool(processing.get_whisper_model)

    yield

    redis_client.close()


app = FastAPI(title="AI Meeting Insights", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_task_queue(request: Request) -> Optional[TaskQueue]:
    return getattr(request.app.state, "task_queue", None)


def get_cache(request: Request) -> Optional[CacheService]:
    return getattr(request.app.state, "cache", None)


def require_api_key(request: Request):
    """Require a matching X-API-Key header when API_KEY is configured."""
    api_key = os.getenv("API_KEY")
    if not api_key:
        return
    provided = request.headers.get("x-api-key") or ""
    if not secrets.compare_digest(provided.encode(), api_key.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid API Key")


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    error_detail = str(exc) if DEBUG else "Internal Server Error"
    return JSONResponse(
        status_code=500,
        content={"detail": error_detail}
    )


@app.get("/health")
def health_check():
    return {"status": "ok", "model": processing.FW_MODEL}


@app.get("/")
def read_root():
    return {"message": "Welcome to AI Meeting Insights"}


def _audio_suffix(file: UploadFile) -> str:
    """Return the upload's extension, rejecting files that aren't audio."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in ALLOWED_AUDIO_EXTENSIONS:
        return suffix
    if (file.content_type or "").startswith("audio/"):
        return ""
    allowed = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"Unsupported file type. Upload an audio file ({allowed}).",
    )


def _save_upload(file: UploadFile) -> Path:
    """
    Stream an upload into UPLOAD_DIR under a unique name.

    Names are generated rather than taken from the client so that uploads
    with the same filename can't overwrite each other.
    """
    suffix = _audio_suffix(file)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dst = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    size = 0
    try:
        with dst.open("wb") as out:
            while chunk := file.file.read(_UPLOAD_CHUNK_BYTES):
                size += len(chunk)
                if size > MAX_UPLOAD_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {MAX_UPLOAD_MB} MB limit",
                    )
                out.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400,
                                detail="Uploaded file is empty")
    except BaseException:
        dst.unlink(missing_ok=True)
        raise
    return dst


def _remove_upload(meeting: Meeting) -> None:
    """Delete a meeting's stored audio file, if it's inside UPLOAD_DIR."""
    if meeting.file_path:
        path = Path(meeting.file_path)
    elif meeting.filename:
        # Meetings created before file_path existed were stored under their
        # original filename.
        path = UPLOAD_DIR / os.path.basename(meeting.filename)
    else:
        return
    try:
        path = path.resolve()
        if path.is_relative_to(UPLOAD_DIR.resolve()) and path.is_file():
            path.unlink()
    except OSError as e:
        logger.warning(f"Could not remove upload {path}: {e}")


@app.post("/upload-audio")
def upload_audio(file: UploadFile = File(...),
                 _: None = Depends(require_api_key)):
    dst = _save_upload(file)
    return {"filename": dst.name, "msg": "Upload successful"}


@app.post("/transcribe-audio")
def transcribe_audio(file: UploadFile = File(...),
                     _: None = Depends(require_api_key)):
    dst = _save_upload(file)
    try:
        result = processing.transcribe(str(dst))
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Transcription failed: {e}")
    finally:
        dst.unlink(missing_ok=True)
    return {
        "filename": file.filename,
        "transcript": result.text,
        "language": result.language,
        "duration_seconds": result.duration_seconds,
    }


@app.post("/summarize")
def summarize_transcript(transcript: str,
                         _: None = Depends(require_api_key)):
    return {"summary": processing.summarize(transcript)}


@app.post("/analyze-meeting")
def analyze_meeting(file: UploadFile = File(...),
                    db: Session = Depends(get_db),
                    task_queue: Optional[TaskQueue] = Depends(get_task_queue),
                    cache: Optional[CacheService] = Depends(get_cache),
                    _: None = Depends(require_api_key)):
    """
    Queue a meeting for async processing.
    Returns immediately with status 'queued' and meeting_id; poll
    GET /meetings/{meeting_id} for its status. When the worker queue is
    disabled or unreachable, the meeting is processed synchronously instead.
    """
    dst = _save_upload(file)

    m = Meeting(
        filename=os.path.basename(file.filename or dst.name),
        transcript="",  # Filled in once processed
        summary="",
        status=MeetingStatus.QUEUED,
        file_path=str(dst),
        created_at=datetime.now(timezone.utc),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    if cache:
        cache.invalidate_meetings()

    if USE_WORKER_SERVICE and task_queue is not None:
        try:
            job_id = task_queue.enqueue_meeting_job(
                meeting_id=m.id,
                file_path=str(dst),
                filename=m.filename
            )
        except Exception as e:
            logger.warning(f"Queueing meeting {m.id} failed, processing "
                           f"synchronously: {e}")
        else:
            return {
                "status": MeetingStatus.QUEUED,
                "meeting_id": m.id,
                "job_id": job_id,
                "message": "Meeting queued for processing"
            }

    # Fallback: synchronous processing (worker disabled or unavailable)
    m.status = MeetingStatus.PROCESSING
    db.commit()
    try:
        result = processing.process_audio(str(dst))
    except Exception as e:
        logger.exception(f"Processing meeting {m.id} failed")
        m.status = MeetingStatus.FAILED
        m.error_message = str(e)
        db.commit()
        if cache:
            cache.invalidate_meetings()
        raise HTTPException(status_code=500,
                            detail=f"Processing failed: {e}")

    processing.apply_result(m, result)
    db.commit()
    db.refresh(m)
    if cache:
        cache.invalidate_meetings()

    return {
        "status": MeetingStatus.COMPLETED,
        "meeting_id": m.id,
        "filename": m.filename,
        "summary": m.summary,
        "language": m.language,
        "duration_seconds": m.duration_seconds,
        "keywords": result.keywords or None,
    }


@app.get("/job-status/{job_id}")
def get_job_status(job_id: str,
                   task_queue: Optional[TaskQueue] = Depends(get_task_queue),
                   _: None = Depends(require_api_key)):
    """Get the status of a processing job."""
    try:
        job_status = task_queue.get_job_status(job_id)
    except Exception:
        raise HTTPException(status_code=503,
                            detail="Task queue not available")
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    return job_status


@app.get("/queue-stats")
def get_queue_stats(task_queue: Optional[TaskQueue] = Depends(get_task_queue),
                    _: None = Depends(require_api_key)):
    """Get current queue statistics."""
    try:
        return {
            "queue_length": task_queue.get_queue_length(),
            "processing_count": task_queue.get_processing_count(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception:
        return {"error": "Task queue not available"}


@app.get("/meetings", response_model=List[MeetingListItem])
def list_meetings(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    cache: Optional[CacheService] = Depends(get_cache),
    _: None = Depends(require_api_key)
):
    """List meetings, newest first, with Redis caching for performance."""
    def load():
        rows = (
            db.query(Meeting)
            .order_by(Meeting.created_at.desc(), Meeting.id.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return [MeetingListItem.model_validate(r) for r in rows]

    if cache is None:
        return load()
    return cache.get_or_set(cache.meetings_key(request), load)


@app.post("/ray-summary")
async def ray_summary(
    request: dict,
    _: None = Depends(require_api_key)
):
    """
    Forward summarization requests to Ray Serve deployment.
    Demonstrates real-time processing with Ray.
    """
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="No text provided")

        # Forward request to Ray Serve
        ray_serve_url = os.getenv("RAY_SERVE_URL", "http://localhost:10001")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{ray_serve_url}/SummarizationService",
                json={"text": text},
                timeout=30.0
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "summary": result.get("summary", ""),
                    "processing_time_ms": result.get(
                        "processing_time_ms", 0),
                    "service": "ray-serve",
                    "input_length": len(text),
                    "timestamp": result.get("timestamp")
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ray Serve error: {response.text}"
                )

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ray Serve timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ray Serve unavailable")
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summarization failed: {str(e)}")


@app.get("/ray-health")
async def ray_health():
    """Check Ray Serve health status."""
    try:
        ray_serve_url = os.getenv("RAY_SERVE_URL", "http://localhost:10001")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{ray_serve_url}/HealthCheck",
                timeout=5.0
            )

            if response.status_code == 200:
                return {
                    "ray_serve_status": "healthy",
                    "ray_serve_response": response.json()
                }
            else:
                return {
                    "ray_serve_status": "unhealthy",
                    "status_code": response.status_code
                }

    except Exception as e:
        return {
            "ray_serve_status": "unavailable",
            "error": str(e)
        }


@app.get("/meetings/{meeting_id}", response_model=MeetingDetail)
def get_meeting(meeting_id: int, db: Session = Depends(get_db),
                _: None = Depends(require_api_key)):
    r = db.get(Meeting, meeting_id)
    if not r:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return MeetingDetail.model_validate(r)


@app.delete("/meetings/{meeting_id}")
def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    cache: Optional[CacheService] = Depends(get_cache),
    _: None = Depends(require_api_key),
):
    r = db.get(Meeting, meeting_id)
    if not r:
        raise HTTPException(status_code=404, detail="Meeting not found")

    _remove_upload(r)
    db.delete(r)
    db.commit()
    if cache:
        cache.invalidate_meetings()
    return {"ok": True}


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so they match literally."""
    return (value.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_"))


@app.get("/search", response_model=List[MeetingListItem])
def search_meetings(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    cache: Optional[CacheService] = Depends(get_cache),
    _: None = Depends(require_api_key),
):
    """Search meetings with optimized GIN indexes and Redis caching."""
    def load():
        like = f"%{_escape_like(q)}%"
        conds = [
            column.ilike(like, escape="\\")
            for column in (Meeting.transcript, Meeting.summary,
                           Meeting.filename, Meeting.keywords)
        ]
        rows = (
            db.query(Meeting)
            .filter(or_(*conds))
            .order_by(Meeting.created_at.desc(), Meeting.id.desc())
            .limit(limit)
            .all()
        )
        return [MeetingListItem.model_validate(r) for r in rows]

    if cache is None:
        return load()
    return cache.get_or_set(cache.meetings_key(request), load)
