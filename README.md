# Cloud-Native AI Meeting Insights

A privacy-first, self-hostable meeting-to-action platform. Upload meeting audio, transcribe it with faster-whisper, extract structured outcomes, and review results from a Next.js interface.

> The project is under active development. Clean builds, unit tests, a real PostgreSQL/Redis/MinIO pipeline test, and infrastructure validation run in CI. A live AWS deployment and published performance benchmark are not yet claimed as validated.

## What is implemented

- FastAPI audio upload API
- Redis-backed jobs with retry limits and queue backpressure
- faster-whisper transcription
- Privacy-aware insight routing:
  - deterministic local extraction by default
  - OpenAI-compatible local model endpoint when configured
  - OpenAI only after explicitly setting `AI_PROVIDER=openai`
- Structured outcomes:
  - overview
  - key points
  - decisions
  - action items
  - risks and blockers
  - open questions
- PostgreSQL persistence and meeting search
- Next.js dashboard, upload flow, job polling, and meeting details
- Same-origin Next.js API proxy so backend addresses and API credentials remain server-side
- Shared S3-compatible object storage for independently scaled API and worker processes
- Raw recording deletion after successful processing by default
- MinIO-backed Docker Compose development environment
- Terraform definitions for EKS, RDS, ElastiCache, private S3 storage, encryption, retention, IAM, and IRSA
- GitHub OIDC deployment workflow with encrypted remote Terraform state and locking

## Architecture

```text
Browser
  │ same-origin /api
  ▼
Next.js frontend and runtime proxy
  │
  ▼
FastAPI API ─────────────► PostgreSQL
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

Redis contains an object key rather than a Pod-local path. API and worker Pods can therefore scale independently while reading the same audio from S3-compatible storage.

## Privacy model

The default configuration is:

```env
AI_PROVIDER=local
DELETE_AUDIO_AFTER_PROCESSING=true
```

With this configuration, the application does not intentionally send transcripts to OpenAI and removes the raw recording after the worker successfully persists the transcript and structured outcomes. Set `DELETE_AUDIO_AFTER_PROCESSING=false` when raw recording retention is explicitly required; the S3 lifecycle policy remains a secondary expiration control.

To explicitly permit OpenAI processing:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
```

Self-hosting alone does not establish compliance. Operators remain responsible for consent, access controls, network policy, retention, encryption, auditing, and applicable regulations.

## Local development

### Requirements

- Docker with Docker Compose
- Enough memory for PostgreSQL, Redis, MinIO, the API, the worker, and faster-whisper

### Start

```bash
git clone https://github.com/Tonnthe1/Cloud-Native-AI-Meeting-Insights.git
cd Cloud-Native-AI-Meeting-Insights
cp .env.example .env
docker compose up --build
```

| Service | Address |
|---|---|
| Frontend | `http://localhost:3000` |
| API documentation | `http://localhost:8000/docs` |
| Worker health | `http://localhost:8001/health` |
| MinIO API | `http://localhost:9000` |
| MinIO console | `http://localhost:9001` |
| PostgreSQL | `localhost:5433` |
| Redis | `localhost:6379` |

Docker Compose configures API and worker to use the same MinIO bucket. For a single-process filesystem setup:

```env
STORAGE_BACKEND=local
STORAGE_LOCAL_DIR=/app/uploads
```

When running the frontend outside Compose, point its runtime proxy at the API:

```env
INTERNAL_API_URL=http://localhost:8000
```

## Important configuration

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
DELETE_AUDIO_AFTER_PROCESSING=true

# Queue behavior
MAX_QUEUE_SIZE=100
MAX_JOB_ATTEMPTS=3
JOB_TTL_SECONDS=86400
```

Use a multilingual faster-whisper model such as `small`, `medium`, or `large-v3` for non-English meetings.

## Validation

GitHub Actions checks:

```text
flake8
backend unit tests
PostgreSQL + Redis + MinIO pipeline integration test
real MinIO object round trip
API Docker image build
worker Docker image build
Next.js production build
terraform fmt
terraform init -backend=false
terraform validate
docker compose config
deployment shell syntax
```

The pipeline integration test covers:

```text
FastAPI upload
  → MinIO object
  → Redis queue
  → worker processing
  → structured insights
  → PostgreSQL persistence
  → raw audio cleanup
```

Whisper is replaced with a deterministic transcription fixture in that CI test so it does not download a model. A real-audio Whisper benchmark remains separate work.

## AWS infrastructure

Terraform defines:

- VPC with public and private subnets
- EKS cluster and managed node group
- RDS PostgreSQL
- ElastiCache Redis
- private encrypted S3 bucket with public access blocked
- configurable S3 lifecycle expiration
- least-privilege runtime and controller IAM policies
- Secrets Manager database credentials

`infra/deploy.sh` additionally:

- bootstraps an encrypted, versioned S3 Terraform-state bucket
- creates a DynamoDB state lock table
- creates and annotates API/worker service accounts for IRSA after EKS exists
- retrieves database credentials without committing them to manifests
- installs the AWS Load Balancer Controller
- builds and pushes API, worker, and frontend images
- renders manifests from Terraform outputs without editing tracked files
- deploys one same-origin frontend ingress while the API remains internal

```bash
cd infra
./deploy.sh check
./deploy.sh plan
./deploy.sh apply
./deploy.sh build
./deploy.sh deploy
```

Complete sequence:

```bash
cd infra
./deploy.sh all
```

The guarded convenience wrapper requires explicit cost confirmation:

```bash
cd infra
CONFIRM_DEPLOY=yes ./one-click-deploy.sh
```

### GitHub deployment

The manual `Deploy to AWS EKS` workflow uses GitHub OIDC rather than stored AWS access keys. Configure environment secrets:

- `AWS_DEPLOY_ROLE_ARN` — role trusted by the repository's GitHub OIDC subject
- `TF_STATE_BUCKET` — optional preselected state bucket; a deterministic private bucket is otherwise bootstrapped
- `API_KEY` — optional application API key
- `OPENAI_API_KEY` — only when `AI_PROVIDER=openai` is intentionally enabled

Use protected GitHub environments for staging and production approvals.

A live AWS apply has not yet been executed by CI. Review account permissions, cost, DNS, TLS, scaling, backup, and production security settings before applying.

## Current limitations

- No published real-audio Whisper benchmark yet
- No verified throughput, p95 latency, uptime, or cache-hit-rate claims
- Human editing of extracted outcomes is not implemented yet
- User accounts, workspaces, RBAC, and audit logs are not implemented yet
- GitHub, Jira, Slack, and Confluence exports are planned rather than complete
- Ray and Triton assets are experimental and are not part of the default path
- The deterministic local extractor is intentionally simpler than an LLM

See [`docs/PRODUCT_BLUEPRINT.md`](docs/PRODUCT_BLUEPRINT.md) for product direction and implementation priorities.

## Roadmap

1. Real speech fixtures and reproducible Whisper quality/latency benchmarks
2. Human review and editing for decisions and action items
3. Authentication, workspaces, RBAC, retention controls, and audit events
4. GitHub/Jira/Slack/Confluence exports
5. Multilingual and load benchmarks with published methodology
6. Distributed inference only after profiling demonstrates a real bottleneck

## License

MIT
