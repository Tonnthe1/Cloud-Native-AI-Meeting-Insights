from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db import SessionLocal, engine, Base
from typing import List
from dotenv import load_dotenv
from app.models import Meeting
from typing import List, Optional
from app.schemas import MeetingListItem, MeetingDetail
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from app.util import get_audio_duration_seconds, extract_keywords
from app.redis_client import get_redis_client, TaskQueue
from app.cache import CacheService, cached_endpoint, invalidate_meeting_caches
from pathlib import Path
import shutil
import os
import subprocess
import uuid
import openai
from faster_whisper import WhisperModel
import httpx

load_dotenv()  # Load .env
load_dotenv(".env.local", override=True)  # Load .env.local with override
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
host = os.getenv("POSTGRES_HOST", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
db = os.getenv("POSTGRES_DB")
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"

@asynccontextmanager
async def lifespan(_: FastAPI):
    global _fw_model, _task_queue, _cache_service
    # Only load model if we're not using the worker service
    use_worker = os.getenv("USE_WORKER_SERVICE", "true").lower() == "true"
    if not use_worker:
        _fw_model = WhisperModel(FW_MODEL, device="cpu", compute_type=FW_COMPUTE_TYPE)
    
    # Initialize Redis task queue and cache service
    try:
        redis_client = get_redis_client()
        _task_queue = TaskQueue(redis_client)
        _cache_service = CacheService(redis_client)
        print("Redis connected: Task queue and cache service initialized")
    except Exception as e:
        print(f"Warning: Could not connect to Redis: {e}")
        _task_queue = None
        _cache_service = None
    
    # Run database migrations
    try:
        from app.migrations.migrate import run_migrations
        run_migrations()
        print("Database migrations completed")
    except Exception as e:
        print(f"Warning: Migration failed: {e}")
    
    yield
    _fw_model = None
    _task_queue = None
    _cache_service = None

app = FastAPI(title="AI Meeting Insights", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

openai.api_key = os.getenv("OPENAI_API_KEY")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FW_MODEL = os.getenv("FW_MODEL", "base.en")
FW_COMPUTE_TYPE = os.getenv("FW_COMPUTE_TYPE", "float32")
_fw_model: WhisperModel | None = None
_task_queue: TaskQueue | None = None
_cache_service: CacheService | None = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_api_key(request: Request):
    api_key = os.getenv("API_KEY")
    if not api_key:
        return
    header_key = request.headers.get("x-api-key")
    if header_key != api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

def api_key_dependency(request: Request):
    return verify_api_key(request)

def optional_api_key_dependency(request: Request):
    try:
        return verify_api_key(request)
    except HTTPException:
        api_key = os.getenv("API_KEY")
        if api_key:
            raise
        return None

def get_cache_service() -> CacheService:
    """Dependency to get cache service."""
    if _cache_service is None:
        raise HTTPException(status_code=503, detail="Cache service not available")
    return _cache_service

def _split_keywords(s: Optional[str]) -> Optional[List[str]]:
    ks = [k.strip() for k in (s or "").split(",") if k.strip()]
    return ks or None

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    import traceback
    error_detail = str(exc) if os.getenv("DEBUG") else "Internal Server Error"
    if os.getenv("DEBUG"):
        print(f"Exception: {exc}")
        print(f"Traceback: {traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": error_detail}
    )

@app.get("/health")
def health_check():
    return {"status": "ok", "model": FW_MODEL}

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Meeting Insights"}

def _save_upload(file: UploadFile) -> Path:
    """
    Save incoming UploadFile to UPLOAD_DIR with a safe filename.
    """
    safe_name = os.path.basename(file.filename or f"{uuid.uuid4().hex}.m4a")
    dst = UPLOAD_DIR / safe_name
    with dst.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return dst

def _to_wav_16k_mono(src: Path) -> Path:
    wav = src.with_suffix(".wav")
    cmd = ["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(wav)]
    subprocess.run(cmd, check=True, capture_output=True)
    return wav

def transcribe_with_faster_whisper(src_path: Path) -> tuple[str, str | None]:
    if _fw_model is None:
        raise RuntimeError("faster-whisper model not loaded")

    wav = _to_wav_16k_mono(src_path)
    segments, info = _fw_model.transcribe(
        str(wav),
        beam_size=5,
        vad_filter=True,
    )
    parts = [seg.text for seg in segments]
    return " ".join(parts).strip(), getattr(info, "language", None)

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...), _: None = Depends(api_key_dependency)):
    dst = _save_upload(file)
    return JSONResponse(content={"filename": str(dst), "msg": "Upload successful"})

@app.post("/transcribe-audio")
async def transcribe_audio(file: UploadFile = File(...), _: None = Depends(api_key_dependency)):
    try:
        dst = _save_upload(file)
        transcript = transcribe_with_faster_whisper(dst)
        return JSONResponse(content={
            "filename": str(dst),
            "transcript": transcript
        })
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr.decode("utf-8", "ignore"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def summarize_meeting_transcript(transcript: str) -> str:
    prompt = (
        "Summarize the following meeting transcript in bullet points, "
        "highlight action items, key decisions, and follow-up tasks. "
        "Use clear English. Transcript:\n"
        + transcript
    )
    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a meeting assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=512
    )
    return completion.choices[0].message.content or ""

@app.post("/summarize")
async def summarize_transcript(transcript: str, _: None = Depends(api_key_dependency)):
    summary = summarize_meeting_transcript(transcript) if transcript else ""
    return {"summary": summary}

@app.post("/analyze-meeting")
async def analyze_meeting(file: UploadFile = File(...), db: Session = Depends(get_db), _: None = Depends(api_key_dependency),):
    """
    Queue a meeting for async processing.
    Returns immediately with status 'queued' and meeting_id.
    """
    use_worker = os.getenv("USE_WORKER_SERVICE", "true").lower() == "true"
    
    # Save uploaded file
    dst = _save_upload(file)
    
    # Create meeting record with initial state
    m = Meeting(
        filename=os.path.basename(file.filename or "unknown.wav"),
        transcript="",  # Will be filled by worker
        summary="",     # Will be filled by worker
        created_at=datetime.now(timezone.utc),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    
    if use_worker and _task_queue:
        # Queue the job for async processing
        try:
            job_id = _task_queue.enqueue_meeting_job(
                meeting_id=m.id,
                file_path=str(dst),
                filename=m.filename
            )
            
            # Invalidate meeting caches since we added a new meeting
            if _cache_service:
                await invalidate_meeting_caches(_cache_service)
            
            return {
                "status": "queued",
                "meeting_id": m.id,
                "job_id": job_id,
                "message": "Meeting queued for processing"
            }
        except Exception as e:
            # If queueing fails, fall back to sync processing
            print(f"Queue failed, falling back to sync processing: {e}")
    
    # Fallback: synchronous processing (if worker disabled or queue unavailable)
    try:
        transcript, lang = transcribe_with_faster_whisper(dst)
        summary = summarize_meeting_transcript(transcript) if transcript else ""
        duration = get_audio_duration_seconds(str(dst))
        kw_list = extract_keywords(transcript, top_k=8) 
        kw_str = ",".join(kw_list) if kw_list else None
        
        # Update meeting record
        m.transcript = transcript
        m.summary = summary
        if lang:
            m.language = lang
        if duration is not None:
            m.duration_seconds = duration
        if kw_str:
            m.keywords = kw_str
            
        db.commit()
        db.refresh(m)
        
        return {
            "status": "completed",
            "meeting_id": m.id,
            "filename": m.filename,
            "summary": m.summary,
            "language": getattr(m, "language", None),
            "duration_seconds": getattr(m, "duration_seconds", None),
            "keywords": kw_list or None,
        }
        
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr.decode("utf-8", "ignore"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

@app.get("/job-status/{job_id}")
def get_job_status(job_id: str, _: None = Depends(optional_api_key_dependency)):
    """Get the status of a processing job."""
    if not _task_queue:
        raise HTTPException(status_code=503, detail="Task queue not available")
    
    job_status = _task_queue.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job_status

@app.get("/queue-stats")
def get_queue_stats(_: None = Depends(optional_api_key_dependency)):
    """Get current queue statistics."""
    if not _task_queue:
        return {"error": "Task queue not available"}
    
    return {
        "queue_length": _task_queue.get_queue_length(),
        "processing_count": _task_queue.get_processing_count(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/meetings", response_model=List[MeetingListItem])
@cached_endpoint(ttl=60, key_prefix="api")
async def list_meetings(
    request: Request,
    db: Session = Depends(get_db), 
    cache: CacheService = Depends(get_cache_service),
    _: None = Depends(optional_api_key_dependency)
):
    """List meetings with Redis caching for performance."""
    rows = (
        db.query(Meeting)
        .order_by(Meeting.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        MeetingListItem(
            id=r.id,
            filename=r.filename,
            created_at=r.created_at,
            summary=r.summary,
            language=getattr(r, "language", None),
            duration_seconds=getattr(r, "duration_seconds", None),
            keywords=_split_keywords(getattr(r, "keywords", None)),
        )
        for r in rows
    ]

@app.post("/ray-summary")
async def ray_summary(
    request: dict,
    _: None = Depends(optional_api_key_dependency)
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
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "service": "ray-serve",
                    "input_length": len(text),
                    "timestamp": result.get("timestamp")
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ray Serve error: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ray Serve timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ray Serve unavailable")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

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
def get_meeting(meeting_id: int, db: Session = Depends(get_db), _: None = Depends(optional_api_key_dependency)):
    r = db.get(Meeting, meeting_id)
    if not r:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return MeetingDetail(
        id=r.id,
        filename=r.filename,
        created_at=r.created_at,
        language=getattr(r, "language", None),
        duration_seconds=getattr(r, "duration_seconds", None),
        keywords=_split_keywords(getattr(r, "keywords", None)),
        transcript=r.transcript,
        summary=r.summary,
    )

@app.delete("/meetings/{meeting_id}")
def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(optional_api_key_dependency),
):
    r = db.get(Meeting, meeting_id)
    if not r:
        raise HTTPException(status_code=404, detail="Meeting not found")

    try:
        if r.filename:
            path = (UPLOAD_DIR / os.path.basename(r.filename)).resolve()
            if path.is_file():
                path.unlink()
    except Exception:
        pass

    db.delete(r)
    db.commit()
    return {"ok": True}

@app.get("/search", response_model=List[MeetingListItem])
@cached_endpoint(ttl=60, key_prefix="api")
async def search_meetings(
    request: Request,
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
    _: None = Depends(optional_api_key_dependency),
):
    """Search meetings with optimized GIN indexes and Redis caching."""
    like = f"%{q}%"

    conds = [
        Meeting.transcript.ilike(like),
        Meeting.summary.ilike(like),
        Meeting.filename.ilike(like),
    ]
    if hasattr(Meeting, "keywords"):
        conds.append(Meeting.keywords.ilike(like))

    rows = (
        db.query(Meeting)
        .filter(or_(*conds))
        .order_by(Meeting.created_at.desc())
        .limit(100)
        .all()
    )

    return [
        MeetingListItem(
            id=r.id,
            filename=r.filename,
            created_at=r.created_at,
            summary=r.summary,
            language=getattr(r, "language", None),
            duration_seconds=getattr(r, "duration_seconds", None),
            keywords=_split_keywords(getattr(r, "keywords", None)),
        )
        for r in rows
    ]

@app.post("/ray-summary")
async def ray_summary(
    request: dict,
    _: None = Depends(optional_api_key_dependency)
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
                    "processing_time_ms": result.get("processing_time_ms", 0),
                    "service": "ray-serve",
                    "input_length": len(text),
                    "timestamp": result.get("timestamp")
                }
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ray Serve error: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Ray Serve timeout")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ray Serve unavailable")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

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
