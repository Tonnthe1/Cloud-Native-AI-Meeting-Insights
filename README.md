# Cloud-Native AI Meeting Insights

An MIT-licensed, privacy-first, self-hostable meeting-to-action platform. Upload meeting audio, transcribe it with faster-whisper, and turn the transcript into structured decisions, action items, risks, key points, and open questions.

> **Project status:** the core self-hosted path, container builds, PostgreSQL/Redis/MinIO integration pipeline, and infrastructure definitions are validated in CI. A live production AWS deployment and performance claims are not yet presented as validated.

## One-command self-hosting

### macOS, Linux, or WSL

```bash
curl -fsSL https://raw.githubusercontent.com/Tonnthe1/Cloud-Native-AI-Meeting-Insights/main/install.sh | bash
```

### Windows PowerShell

```powershell
irm https://raw.githubusercontent.com/Tonnthe1/Cloud-Native-AI-Meeting-Insights/main/install.ps1 | iex
```

The installer:

- checks Docker and Docker Compose
- clones or updates the project
- generates private database, MinIO, and API secrets
- prefers published GHCR images and falls back to building from source
- starts PostgreSQL, Redis, MinIO, FastAPI, the worker, and Next.js
- waits for API, frontend, and Whisper worker readiness
- binds services to `127.0.0.1` by default

Open `http://localhost:3000` after startup.

The first worker startup downloads the configured faster-whisper model. Its cache is persisted in a Docker volume, so later starts reuse it.

### Existing checkout

```bash
bash scripts/quickstart.sh up
# or
make up
```

Windows:

```powershell
./scripts/quickstart.ps1 up
```

Useful operations:

```bash
bash scripts/quickstart.sh status
bash scripts/quickstart.sh logs
bash scripts/quickstart.sh down
CONFIRM_RESET=yes bash scripts/quickstart.sh reset
```

PowerShell uses the same command names.

To force a source build instead of published images:

```bash
MEETING_INSIGHTS_PREBUILT=false bash scripts/quickstart.sh up
```

## What works today

- audio upload from the Next.js interface
- asynchronous Redis-backed jobs with queue backpressure and retry limits
- faster-whisper transcription using multilingual model names such as `small`
- local deterministic insight extraction by default
- optional OpenAI-compatible local model endpoint
- explicit opt-in OpenAI processing through `AI_PROVIDER=openai`
- structured overview, key points, decisions, action items, risks, and questions
- PostgreSQL history and search
- S3-compatible object storage shared by API and worker processes
- MinIO for local self-hosting
- raw audio deletion after successful processing by default
- same-origin frontend API proxy that keeps backend credentials server-side
- Docker Compose, EKS manifests, and Terraform infrastructure
- public container-image publishing workflow for `main` and version tags

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

Redis jobs contain object keys rather than Pod-local file paths. API and worker instances can therefore scale independently while reading the same recording from S3-compatible storage.

Ray and Triton are experimental and do not start in the default Compose profile. Enable them only for development experiments:

```bash
docker compose --profile experimental up
```

## Privacy defaults

The generated configuration uses:

```env
AI_PROVIDER=local
DELETE_AUDIO_AFTER_PROCESSING=true
BIND_ADDRESS=127.0.0.1
```

With these defaults, transcripts are not intentionally sent to OpenAI, raw recordings are removed after successful processing, and local ports are not exposed to the network.

To explicitly allow OpenAI processing:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4o-mini
```

To retain original recordings:

```env
DELETE_AUDIO_AFTER_PROCESSING=false
```

Self-hosting alone does not establish regulatory compliance. Operators remain responsible for meeting consent, access policy, retention, encryption, auditing, backups, and applicable law.

## Services

| Service | Local address |
|---|---|
| Application | `http://localhost:3000` |
| API documentation | `http://localhost:8000/docs` |
| Worker readiness | `http://localhost:8001/ready` |
| MinIO API | `http://localhost:9000` |
| MinIO console | `http://localhost:9001` |
| PostgreSQL | `localhost:5433` |
| Redis | `localhost:6379` |

## Configuration

The installers generate `.env` without overwriting an existing file. Important values include:

```env
# Transcription
FW_MODEL=small
FW_DEVICE=cpu
FW_COMPUTE_TYPE=int8
WHISPER_LANGUAGE=

# Insight routing
AI_PROVIDER=local
LOCAL_LLM_BASE_URL=
LOCAL_LLM_MODEL=meeting-insights
OPENAI_API_KEY=

# Queue
MAX_QUEUE_SIZE=100
MAX_JOB_ATTEMPTS=3
JOB_TTL_SECONDS=86400

# Storage
STORAGE_BACKEND=s3
S3_BUCKET=meeting-insights
S3_ENDPOINT_URL=http://minio:9000
DELETE_AUDIO_AFTER_PROCESSING=true
```

For a single-process filesystem setup:

```env
STORAGE_BACKEND=local
STORAGE_LOCAL_DIR=/app/uploads
```

For Chinese and other non-English meetings, use a multilingual model such as `small`, `medium`, or `large-v3`, not an `.en` model.

## Validation

CI runs:

```text
flake8
backend unit tests
real PostgreSQL + Redis + MinIO pipeline integration test
MinIO object upload/download/delete round trip
API image build
worker image build
frontend production build and image build
Terraform format/init/validate
Bash and PowerShell installer validation
Docker Compose topology validation
```

The integration pipeline covers:

```text
FastAPI upload
  → MinIO object
  → Redis queue
  → worker processing
  → structured insights
  → PostgreSQL persistence
  → raw audio cleanup
```

The integration test substitutes a deterministic transcript for Whisper inference. It validates service orchestration, not speech quality or latency.

## AWS deployment

The Terraform stack defines:

- VPC with public/private subnets
- EKS and a managed node group
- RDS PostgreSQL
- ElastiCache Redis
- private encrypted S3 audio storage with lifecycle expiration
- Secrets Manager database credentials
- least-privilege runtime IAM and IRSA
- AWS Load Balancer Controller role

After configuring AWS credentials and the required CLI tools:

```bash
cd infra
CONFIRM_DEPLOY=yes bash one-click-deploy.sh
```

This creates billable resources. The script bootstraps encrypted/versioned remote Terraform state, creates state locking, builds and pushes images, configures EKS identities, and applies the application manifests.

A manual GitHub Actions deployment is also included. It uses GitHub OIDC and expects an `AWS_DEPLOY_ROLE_ARN` environment secret.

A live AWS apply has not yet been executed as part of automated validation. DNS, TLS, backups, scaling, account permissions, and cost controls still need an owner-operated deployment test before calling the AWS path production-ready.

## Public images and releases

Pushes to `main` and tags matching `v*` publish:

```text
ghcr.io/tonnthe1/meeting-insights-api
ghcr.io/tonnthe1/meeting-insights-worker
ghcr.io/tonnthe1/meeting-insights-frontend
```

For the first publication, the repository owner must confirm that the GHCR packages are publicly visible. The installer automatically falls back to a source build when images cannot be pulled.

## Open-source development

- License: [MIT](LICENSE)
- Contribution guide: [CONTRIBUTING.md](CONTRIBUTING.md)
- Security policy: [SECURITY.md](SECURITY.md)
- Product direction: [docs/PRODUCT_BLUEPRINT.md](docs/PRODUCT_BLUEPRINT.md)

## Current limitations

- no published real-audio Whisper quality or latency benchmark
- no verified throughput, p95/p99 latency, uptime, or cache-hit-rate claims
- no user accounts, workspaces, RBAC, or audit log yet
- no human editing of extracted decisions and action items yet
- GitHub, Jira, Slack, and Confluence exports are not implemented yet
- the deterministic local extractor is intentionally simpler than an LLM
- the AWS path is definition-validated but not yet live-deployment-validated

## Next milestones

1. Run and document a real installation smoke test on macOS, Windows, and Linux.
2. Add human review/editing for decisions and action items.
3. Add authentication, workspaces, RBAC, and audit events.
4. Add the first export integration.
5. Publish reproducible real-audio and load benchmarks.

## License

MIT
