from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db import SessionLocal, engine, Base
from typing import List
from dotenv import load_dotenv
from app.models import Meeting
from app.schemas import MeetingOut
import os
import openai

load_dotenv()
user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
host = os.getenv("POSTGRES_HOST", "localhost")
port = os.getenv("POSTGRES_PORT", "5432")
db = os.getenv("POSTGRES_DB")
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"

app = FastAPI(title="AI Meeting Insights")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

openai.api_key = os.getenv("OPENAI_API_KEY")

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Meeting Insights"}

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...), _: None = Depends(api_key_dependency)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    return JSONResponse(content={"filename": file_location, "msg": "Upload successful"})

@app.post("/transcribe-audio")
async def transcribe_audio(file: UploadFile = File(...), _: None = Depends(api_key_dependency)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    with open(file_location, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return JSONResponse(content={
        "filename": file_location,
        "transcript": transcript
    })

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
async def analyze_meeting(file: UploadFile = File(...), _: None = Depends(api_key_dependency)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    with open(file_location, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    summary = summarize_meeting_transcript(transcript)

    db = SessionLocal()
    meeting = Meeting(filename=file.filename, transcript=transcript, summary=summary)
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    db.close()
    
    return {
        "id": meeting.id,
        "transcript": transcript,
        "summary": summary,
        "filename": file.filename
    }

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

