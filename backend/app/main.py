import json
import logging
import os
import subprocess
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.cache import CacheService, cached_endpoint, invalidate_meeting_caches
from app.db import Base, SessionLocal, engine
from app.insights import generate_insights
from app.models import Meeting
from app.redis_client import (
    QueueFullError,
    TaskQueue,
    get_async_redis_client,
    get_redis_client,
)
from app.schemas import MeetingDetail, MeetingListItem, StructuredInsights
from app.storage import (
    ObjectStore,
    build_object_key,
    get_object_store,
    should_delete_audio_after_processing,
)
from app.util import extract_keywords, get_audio_duration_seconds

load_dotenv()
load_dotenv(".env.local", override=True)

logger = logging.getLogger(__name__)
_task_queue: Optional[TaskQueue] = None
_cache_service: Optional[CacheService] = None
_object_store: Optional[ObjectStore] = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _task_queue, _cache_service, _object_store
    Base.metadata.create_all(bind=engine)
    try:
        from app.migrations.migrate import run_migrations
        run_migrations()
    except Exception as exc:
        logger.warning("Database migration failed: %s", exc)

    _object_store = get_object_store()

    try:
        queue_client = get_redis_client()
        queue_client.ping()
        _task_queue = TaskQueue(queue_client)
        cache_client = get_async_redis_client()
        await cache_client.ping()
        _cache_service = CacheService(cache_client)
    except Exception as exc:
        logger.warning("Redis unavailable: %s", exc)
        _task_queue = None
        _cache_service = None

    yield

    if _cache_service:
        await _cache_service.redis.aclose()
    _task_queue = None
    _cache_service = None
    _object_store = None


app = FastAPI(title="Cloud-Native AI Meeting Insights", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(request: Request) -> None:
    api_key = os.getenv("API_KEY")
    if api_key and request.headers.get("x-api-key") != api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


def optional_api_key(request: Request) -> None:
    verify_api_key(request)


def get_cache_service() -> CacheService:
    if _cache_service is None:
        raise HTTPException(status_code=503, detail="Cache service unavailable")
    return _cache_service


def _require_object_store() -> ObjectStore:
    if _object_store is None:
        raise HTTPException(status_code=503, detail="Object storage unavailable")
    return _object_store


def _store_upload(file: UploadFile) -> str:
    object_key = build_object_key(file.filename or "meeting-audio")
    _require_object_store().put_fileobj(file.file, object_key, file.content_type)
    return object_key


def _delete_audio_after_success(meeting: Meeting, db: Session) -> None:
    object_key = meeting.audio_object_key
    if not object_key or not should_delete_audio_after_processing():
        return
    try:
        _require_object_store().delete(object_key)
        meeting.audio_object_key = None
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning(
            "Meeting %s completed but raw audio cleanup failed for %s: %s",
            meeting.id,
            object_key,
            exc,
        )


def _mark_upload_failed(meeting: Meeting, object_key: str, db: Session) -> None:
    try:
        _require_object_store().delete(object_key)
        meeting.audio_object_key = None
    except Exception as exc:
        logger.warning("Failed to clean rejected upload %s: %s", object_key, exc)
    meeting.processing_status = "failed"
    db.commit()


def _split_keywords(value: Optional[str]) -> Optional[List[str]]:
    values = [item.strip() for item in (value or "").split(",") if item.strip()]
    return values or None


def _parse_insights(meeting: Meeting) -> Optional[StructuredInsights]:
    if not meeting.insights_json:
        return None
    try:
        return StructuredInsights.model_validate(json.loads(meeting.insights_json))
    except (json.JSONDecodeError, ValueError):
        return None


def _meeting_list_item(meeting: Meeting) -> MeetingListItem:
    return MeetingListItem(
        id=meeting.id,
        filename=meeting.filename,
        created_at=meeting.created_at,
        summary=meeting.summary,
        language=meeting.language,
        duration_seconds=meeting.duration_seconds,
        keywords=_split_keywords(meeting.keywords),
        status=meeting.processing_status,
    )


def _process_synchronously(meeting: Meeting, object_key: str, db: Session) -> None:
    from faster_whisper import WhisperModel

    model = WhisperModel(
        os.getenv("FW_MODEL", "small"),
        device=os.getenv("FW_DEVICE", "cpu"),
        compute_type=os.getenv("FW_COMPUTE_TYPE", "int8"),
    )
    store = _require_object_store()
    with store.materialize(object_key) as file_path:
        wav_path = file_path.with_name(f"{file_path.stem}-{uuid.uuid4().hex}.wav")
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(file_path),
                    "-ar",
                    "16000",
                    "-ac",
                    "1",
                    str(wav_path),
                ],
                check=True,
                capture_output=True,
            )
            segments, info = model.transcribe(str(wav_path), vad_filter=True)
            transcript = " ".join(segment.text.strip() for segment in segments).strip()
            insights = generate_insights(transcript).to_dict()
            meeting.transcript = transcript
            meeting.summary = insights["overview"]
            meeting.insights_json = json.dumps(insights, ensure_ascii=False)
            meeting.insight_provider = insights.get("provider")
            meeting.processing_status = "completed"
            meeting.language = getattr(info, "language", None)
            meeting.duration_seconds = get_audio_duration_seconds(str(file_path))
            meeting.keywords = ",".join(extract_keywords(transcript, top_k=8)) or None
            db.commit()
            _delete_audio_after_success(meeting, db)
        except Exception:
            meeting.processing_status = "failed"
            db.commit()
            raise
        finally:
            wav_path.unlink(missing_ok=True)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "queue_available": _task_queue is not None,
        "cache_available": _cache_service is not None,
        "storage_available": _object_store is not None,
        "storage_backend": os.getenv("STORAGE_BACKEND", "local"),
        "delete_audio_after_processing": should_delete_audio_after_processing(),
        "ai_provider": os.getenv("AI_PROVIDER", "local"),
    }


@app.post("/analyze-meeting")
async def analyze_meeting(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    content_type = file.content_type or ""
    if content_type and not content_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail="Only audio files are supported")

    object_key = _store_upload(file)
    meeting = Meeting(
        filename=os.path.basename(file.filename or Path(object_key).name),
        audio_object_key=object_key,
        transcript="",
        summary="",
        processing_status="queued",
        created_at=datetime.now(timezone.utc),
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    if _task_queue is not None:
        try:
            job_id = _task_queue.enqueue_meeting_job(
                meeting_id=meeting.id,
                object_key=object_key,
                filename=meeting.filename,
            )
            if _cache_service:
                await invalidate_meeting_caches(_cache_service)
            return {
                "status": "queued",
                "meeting_id": meeting.id,
                "job_id": job_id,
                "message": "Meeting queued for processing",
            }
        except QueueFullError as exc:
            _mark_upload_failed(meeting, object_key, db)
            raise HTTPException(status_code=429, detail=str(exc)) from exc

    if os.getenv("ALLOW_SYNC_FALLBACK", "false").lower() != "true":
        _mark_upload_failed(meeting, object_key, db)
        raise HTTPException(
            status_code=503,
            detail="Worker queue unavailable and synchronous fallback is disabled",
        )

    try:
        _process_synchronously(meeting, object_key, db)
        return {"status": "completed", "meeting_id": meeting.id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc


@app.get("/job-status/{job_id}")
def get_job_status(job_id: str, _: None = Depends(optional_api_key)):
    if _task_queue is None:
        raise HTTPException(status_code=503, detail="Task queue unavailable")
    job = _task_queue.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/queue-stats")
def queue_stats(_: None = Depends(optional_api_key)):
    if _task_queue is None:
        raise HTTPException(status_code=503, detail="Task queue unavailable")
    return {
        "queue_length": _task_queue.get_queue_length(),
        "processing_count": _task_queue.get_processing_count(),
        "max_queue_size": _task_queue.max_queue_size,
    }


@app.get("/meetings", response_model=List[MeetingListItem])
@cached_endpoint(ttl=60, key_prefix="api")
async def list_meetings(
    request: Request,
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
    _: None = Depends(optional_api_key),
):
    rows = db.query(Meeting).order_by(Meeting.created_at.desc()).limit(100).all()
    return [_meeting_list_item(row) for row in rows]


@app.get("/meetings/{meeting_id}", response_model=MeetingDetail)
def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(optional_api_key),
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return MeetingDetail(
        id=meeting.id,
        filename=meeting.filename,
        created_at=meeting.created_at,
        language=meeting.language,
        duration_seconds=meeting.duration_seconds,
        keywords=_split_keywords(meeting.keywords),
        transcript=meeting.transcript,
        summary=meeting.summary,
        insights=_parse_insights(meeting),
        status=meeting.processing_status,
    )


@app.delete("/meetings/{meeting_id}")
async def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(optional_api_key),
):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.audio_object_key:
        try:
            _require_object_store().delete(meeting.audio_object_key)
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="Unable to delete stored meeting audio",
            ) from exc

    db.delete(meeting)
    db.commit()
    if _cache_service:
        await invalidate_meeting_caches(_cache_service)
    return {"ok": True}


@app.get("/search", response_model=List[MeetingListItem])
@cached_endpoint(ttl=60, key_prefix="api")
async def search_meetings(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200),
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
    _: None = Depends(optional_api_key),
):
    like = f"%{q}%"
    rows = (
        db.query(Meeting)
        .filter(or_(
            Meeting.transcript.ilike(like),
            Meeting.summary.ilike(like),
            Meeting.filename.ilike(like),
            Meeting.keywords.ilike(like),
        ))
        .order_by(Meeting.created_at.desc())
        .limit(100)
        .all()
    )
    return [_meeting_list_item(row) for row in rows]
