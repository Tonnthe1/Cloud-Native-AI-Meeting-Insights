# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cloud-native AI meeting insights: upload a meeting recording, get a transcript (faster-whisper), summary (OpenAI, with an extractive fallback) and keywords. FastAPI API + Redis-queued worker + Next.js frontend, with Docker Compose for local use and Terraform/Kubernetes configs for AWS EKS.

## Architecture

- **API** (`backend/app/main.py`): uploads, meeting CRUD/search, job queueing. Processes synchronously when the worker is disabled (`USE_WORKER_SERVICE=false`) or Redis is unreachable.
- **Worker** (`backend/app/worker.py`, run with `python -m app.worker`): pops jobs from Redis, runs the pipeline, retries up to 3 times, serves `/health` on port 8001 from the same process.
- **Pipeline** (`backend/app/processing.py`): shared by API and worker. faster-whisper decodes audio itself via PyAV (no ffmpeg step); the model loads lazily.
- **Meeting status** (`backend/app/models.py`): `queued` → `processing` → `completed`/`failed` (+ `error_message`). The frontend polls this instead of job IDs.
- **Cache** (`backend/app/cache.py`): read-through Redis cache for `/meetings` and `/search`, invalidated by bumping a generation counter (works from the worker's sync client too). All endpoints work without Redis.
- **DB**: PostgreSQL via sync SQLAlchemy. Schema changes go in `backend/app/migrations/NNN_*.sql` (applied at API startup, Postgres only); also update `models.py` so `create_all` matches for fresh DBs.
- **Frontend** (`frontend/`): Next.js 15 App Router + Tailwind v4. API client in `src/lib/api.ts` (`NEXT_PUBLIC_API_URL` is baked in at build time).
- **Infra**: `docker-compose.yml` (Ray/Triton demo services are behind `--profile extras`), `infra/terraform`, `infra/k8s`.

## Development Commands

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
python -m app.worker

# Backend checks (tests use SQLite + fakeredis; no services needed)
flake8 .
pytest

# Frontend
cd frontend
npm ci
npm run dev
npm run lint && npm run build   # build fails on lint/type errors

# Everything via Docker
cp .env.example .env
docker compose up --build
```

## Notes

- Python 3.11 backend; flake8 (79-char lines) runs in CI.
- API docs at `/docs` and `/redoc`; health check at `/health`.
- The root `.gitignore` has broad patterns (`*key*`, `*token*`, `*secret*`, `*password*`); avoid those substrings in new filenames or they won't be committed.
- Keep `ALLOWED_AUDIO_EXTENSIONS` (backend `main.py`) and `AUDIO_EXTENSIONS` (frontend `src/lib/format.ts`) in sync.
