# Cloud-Native AI Meeting Insights

A privacy-first, self-hostable meeting-to-action platform. Upload meeting audio, transcribe it with faster-whisper, extract structured outcomes, and review the results from a Next.js interface.

> The project is under active development. The core application builds and its unit tests pass, but a real AWS deployment and published performance benchmark are not yet claimed as validated.

## What is implemented

- Audio upload through a FastAPI API
- Asynchronous Redis-backed processing with retry limits and queue backpressure
- faster-whisper transcription
- Privacy-aware insight routing:
  - deterministic local extraction by default
  - OpenAI-compatible local model endpoint when configured
  - OpenAI only after explicitly setting `AI_PROVIDER=openai`
- Structured meeting outcomes:
  - overview
  - key points
  - decisions
  - action items
  - risks and blockers
  - open questions
- PostgreSQL persistence and meeting search
- Next.js dashboard, upload flow, meeting details, and job-status polling
- S3-compatible object storage shared by the API and workers
- MinIO-backed Docker Compose development environment
- Terraform definitions for EKS, RDS, ElastiCache, private S3 storage, encryption, retention, and IRSA
- CI checks for backend lint/tests, API and worker images, frontend production build, Terraform validation, and Compose topology

## Architecture

```text
Browser
  │
  ▼
Next.js frontend
  │
  ▼
FastAPI API ───────► PostgreSQL
  │
  ├────► S3 / MinIO object storage
  │
  └────► Redis job queue
             │
             ▼
       Python worker
             │
             ├────► faster-whisper
             └────► local or explicitly configured insight provider
```

The queue contains an object key rather than a Pod-local file path. This allows independently scaled API and worker Pods to access the same audio through S3-compatible storage.

## Privacy model

The default configuration is:

```env
AI_PROVIDER=local
```

With this setting, the application does not intentionally send transcripts to OpenAI. It uses a configured OpenAI-compatible local endpoint or deterministic local extraction.

To explicitly permit OpenAI processing:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
```

Self-hosting alone does not guarantee compliance. Operators are still responsible for network controls, access policy, encryption, retention, consent, and applicable regulations.

## Local development

### Requirements

- Docker with Docker Compose
- Enough memory to run PostgreSQL, Redis, MinIO, the API, the worker, and faster-whisper

### Start the application

```bash
git clone https://github.com/Tonnthe1/Cloud-Native-AI-Meeting-Insights.git
cd Cloud-Native-AI-Meeting-Insights
cp .env.example .env
docker compose up --build
```

Default local services:

| Service | Address |
|---|---|
| Frontend | `http://localhost:3000` |
| API documentation | `http://localhost:8000/docs` |
| Worker health | `http://localhost:8001/health` |
| MinIO API | `http://localhost:9000` |
| MinIO console | `http://localhost:9001` |
| PostgreSQL | `localhost:5433` |
| Redis | `localhost:6379` |

Docker Compose configures both the API and worker to use the same MinIO bucket. For a single-process filesystem setup, use:

```env
STORAGE_BACKEND=local
STORAGE_LOCAL_DIR=/app/uploads
```

## Important environment variables

```env
# AI routing
AI_PROVIDER=local
LOCAL_LLM_BASE_URL=
LOCAL_LLM_MODEL=meeting-insights
OPENAI_API_KEY=

# Transcription
FW_MODEL=small
FW_DEVICE=cpu
FW_COMPUTE_TYPE=int8
WHISPER_LANGUAGE=

# Shared storage
STORAGE_BACKEND=s3
S3_BUCKET=meeting-insights
S3_ENDPOINT_URL=http://minio:9000
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=change-me-minio

# Queue behavior
MAX_QUEUE_SIZE=100
MAX_JOB_ATTEMPTS=3
JOB_TTL_SECONDS=86400
```

Use a multilingual faster-whisper model such as `small`, `medium`, or `large-v3` when processing non-English meetings.

## Validation

GitHub Actions currently checks:

```text
flake8
pytest
API Docker build
worker Docker build
Next.js production build
terraform fmt
terraform init -backend=false
terraform validate
docker compose config
bash syntax for infra/deploy.sh
```

Run the main local checks with:

```bash
cd backend
python -m pytest -q
cd ../frontend
npm ci
npm run build
```

## AWS infrastructure

Terraform provisions:

- VPC with public and private subnets
- EKS cluster and managed node group
- RDS PostgreSQL
- ElastiCache Redis
- private S3 bucket for uploaded meeting audio
- server-side encryption and configurable audio expiration
- least-privilege IAM policy
- IRSA-enabled API and worker service accounts
- Kubernetes database credential secret

The deployment helper uses Terraform outputs instead of modifying source manifests in place:

```bash
cd infra
./deploy.sh check
./deploy.sh plan
./deploy.sh apply
./deploy.sh build
./deploy.sh deploy
```

Or run the complete sequence:

```bash
cd infra
./deploy.sh all
```

An AWS deployment has not yet been executed and benchmarked as part of this repository's automated validation. Review AWS cost, Terraform state management, DNS, TLS, and production security settings before applying.

## Current limitations

- No published real-audio end-to-end benchmark yet
- No verified throughput, p95 latency, uptime, or cache-hit-rate claims
- Human editing of extracted outcomes is not implemented yet
- User accounts, workspaces, RBAC, and audit logs are not implemented yet
- GitHub, Jira, Slack, and Confluence exports are planned rather than complete
- Ray and Triton assets are experimental and are not part of the default processing path
- The default local heuristic extractor is intentionally simpler than an LLM

See [`docs/PRODUCT_BLUEPRINT.md`](docs/PRODUCT_BLUEPRINT.md) for the product direction and implementation priorities.

## Development roadmap

1. Real audio integration test covering API → object storage → Redis → worker → database
2. Human review and editing for decisions and action items
3. Authentication, workspaces, RBAC, retention controls, and audit events
4. GitHub/Jira/Slack/Confluence exports
5. Reproducible multilingual and load benchmarks
6. Distributed inference only after profiling demonstrates a real bottleneck

## License

MIT
