from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
import openai

app = FastAPI(title="AI Meeting Insights")

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

UPLOAD_DIR = "app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Meeting Insights"}

@app.post("/upload-audio")
async def upload_audio(file: UploadFile = File(...)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())
    return JSONResponse(content={"filename": file_location, "msg": "Upload successful"})

@app.post("/transcribe-audio")
async def transcribe_audio(file: UploadFile = File(...)):
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
async def summarize_transcript(transcript: str):
    summary = summarize_meeting_transcript(transcript)
    return {"summary": summary}

@app.post("/analyze-meeting")
async def analyze_meeting(file: UploadFile = File(...)):
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
    return {
        "filename": file_location,
        "transcript": transcript,
        "summary": summary
    }