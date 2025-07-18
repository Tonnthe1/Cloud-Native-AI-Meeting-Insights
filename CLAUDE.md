# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cloud-native AI meeting insights application with a FastAPI backend and planned frontend. The project is containerized and designed for cloud deployment.

## Architecture

- **Backend**: FastAPI application (`backend/app/main.py`) with Python 3.11
- **Frontend**: Directory exists but currently empty
- **Infrastructure**: Directory exists for deployment configs
- **Containerization**: Docker setup for the backend service

## Development Commands

### Backend Development

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server (with auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or use the provided start script
./start.sh
```

### Docker Commands

```bash
# Build backend container
cd backend
docker build -t ai-meeting-insights .

# Run container
docker run -p 8000:8000 ai-meeting-insights
```

## Key Technical Details

- **FastAPI App**: Located at `backend/app/main.py`
- **Dependencies**: Standard FastAPI stack with uvicorn, pydantic, and development tools
- **Port**: Backend runs on port 8000
- **Health Check**: Available at `/health` endpoint
- **API Documentation**: Available at `/docs` (Swagger UI) and `/redoc` when running

## Project Structure

```
├── backend/           # FastAPI backend service
│   ├── app/
│   │   └── main.py   # Main FastAPI application
│   ├── Dockerfile    # Container definition
│   ├── requirements.txt
│   └── start.sh      # Development start script
├── frontend/         # Frontend (placeholder)
├── infra/           # Infrastructure configs
└── LICENSE
```

## Development Notes

- The project uses Python 3.11 for the backend
- FastAPI provides automatic API documentation
- Virtual environment is expected to be created in `backend/.venv`
- The start script assumes virtual environment activation