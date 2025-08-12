from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db import SessionLocal, engine, Base
from typing import List
from dotenv import load_dotenv
from app.models import Meeting
from app.schemas import MeetingOut
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
import shutil
import os
import subprocess
import uuid
import openai
from faster_whisper import WhisperModel

load_dotenv()
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
host = os.getenv("POSTGRES_HOST", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
db = os.getenv("POSTGRES_DB")
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"

@asynccontextmanager
async def lifespan(_: FastAPI):
    global _fw_model
    _fw_model = WhisperModel(FW_MODEL, device="cpu", compute_type=FW_COMPUTE_TYPE)
    yield
    _fw_model = None

app = FastAPI(title="AI Meeting Insights", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

openai.api_key = os.getenv("OPENAI_API_KEY")

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "app/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

FW_MODEL = os.getenv("FW_MODEL", "base.en")
FW_COMPUTE_TYPE = os.getenv("FW_COMPUTE_TYPE", "float32")
_fw_model: WhisperModel | None = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_api_key(request: Request):
    api_key = os.getenv("API_KEY")
    header_key = request.headers.get("x-api-key")
    if header_key != api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

def api_key_dependency(request: Request):
    return verify_api_key(request)

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
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
    """
    Convert any audio to 16k mono WAV for stable transcription via ffmpeg.
    """
    wav = src.with_suffix(".wav")
    cmd = ["ffmpeg", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(wav)]
    subprocess.run(cmd, check=True, capture_output=True)
    return wav

def transcribe_with_faster_whisper(src_path: Path) -> str:
    """
    Transcribe with faster-whisper using the globally loaded model.
    """
    if _fw_model is None:
        raise RuntimeError("faster-whisper model not loaded")

    # Convert to WAV to sidestep container/codec quirks
    wav = _to_wav_16k_mono(src_path)

    segments, info = _fw_model.transcribe(
        str(wav),
        beam_size=5,
        vad_filter=True,
        # language="en",  # comment out to auto-detect multi-language
    )
    parts = [seg.text for seg in segments]
    return " ".join(parts).strip()

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
    summary = summarize_meeting_transcript(transcript)
    return {"summary": summary}

@app.post("/analyze-meeting")
def analyze_meeting(file: UploadFile = File(...), ok=Depends(verify_api_key)):
    try:
        dst = _save_upload(file)
        transcript = transcribe_with_faster_whisper(dst)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=e.stderr.decode("utf-8", "ignore"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    summary = summarize_meeting_transcript(transcript)

    db = SessionLocal()
    try:
        m = Meeting(
            filename=os.path.basename(file.filename),
            transcript=transcript,
            summary=summary,
            created_at=datetime.now(timezone.utc),
        )
        db.add(m)
        db.commit()
        db.refresh(m)
    finally:
        db.close()

    return {"id": m.id, "filename": m.filename, "summary": m.summary}

@app.get("/meetings", response_model=List[MeetingOut])
def list_meetings(db: Session = Depends(get_db), _: None = Depends(api_key_dependency)):
    meetings = db.query(Meeting).order_by(Meeting.created_at.desc()).all()
    return meetings

@app.get("/meetings/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: int, db: Session = Depends(get_db), _: None = Depends(api_key_dependency)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting
