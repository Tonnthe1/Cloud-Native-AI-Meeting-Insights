# ☁️ Cloud-Native AI Meeting Insights

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

> “From hours of talking to minutes of insight — without the boring part.”

An open-source, **self-hostable** meeting assistant that transcribes, summarizes, and organizes your meetings — powered by **FastAPI**, **PostgreSQL**, and **AI models** like `faster-whisper` and GPT.

---

## ✨ Features

- **🎙️ Multi-language Transcription**  
  Upload any audio file (`.mp3`, `.wav`, `.m4a`…), get accurate transcripts in 5+ languages.
  
- **🧠 Smart Summarization**  
  GPT-powered summaries to capture the essence of your meetings.
  
- **🔍 Search Your Meetings**  
  Full-text search across transcripts, summaries, and keywords.
  
- **📊 Auto Metadata Extraction**  
  Detects language, calculates duration, extracts top keywords.
  
- **🗑️ Easy Management**  
  View meeting history, see details, delete outdated ones.
  
- **☁️ Cloud-Native & Self-Hostable**  
  Run anywhere: locally via Docker Compose, or deploy to your favorite cloud.

---

## 🚀 Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/cloud-native-ai-meeting-insights.git
cd cloud-native-ai-meeting-insights
2. Configure environment variables
Create .env files for backend and frontend.

Backend .env:

env
Copy
Edit
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword
POSTGRES_DB=AI_Meeting
POSTGRES_HOST=db
POSTGRES_PORT=5432
API_KEY=your_api_key_here
UPLOADS_DIR=/app/app/uploads
FW_MODEL=base
Frontend .env.local:

env
Copy
Edit
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_API_KEY=your_api_key_here
3. Run with Docker Compose
bash
Copy
Edit
docker compose up --build
Backend → http://localhost:8000
Frontend → http://localhost:3000

📚 API Overview
POST /analyze-meeting
Upload an audio file, get transcription + summary + metadata.

GET /meetings
List all saved meetings.

GET /meetings/{id}
Get details for a specific meeting.

GET /search?q=keyword
Search meetings by keyword.

DELETE /meetings/{id}
Delete a meeting record.

🛠️ Tech Stack
Backend: FastAPI, SQLAlchemy, PostgreSQL, Redis (optional), Docker

AI Models: faster-whisper (speech-to-text), GPT (summarization & keywords)

Frontend: Next.js, Tailwind CSS, Axios

Infra: Docker Compose, CORS-ready, self-hostable

📦 Development Workflow

Backend only (no Docker):

bash
Copy
Edit
cd backend
uvicorn app.main:app --reload
Ensure PostgreSQL is running locally and .env points to it.

Frontend only:

bash
Copy
Edit
cd frontend
npm install
npm run dev

Full stack (recommended):

bash
Copy
Edit
docker compose up --build

🤖 Fun Facts
Built during my summer internship prep — because showing is better than telling.

Survives awkward Zoom calls and endless team syncs.

Currently listens more than most meeting attendees.

📜 License
MIT License © 2025 Your Name

💌 Contributing
Pull requests are welcome! For major changes, open an issue first to discuss what you’d like to change.

🌟 Star This Repo
If you find this project useful (or at least amusing), give it a ⭐ on GitHub — it keeps the AI awake.
