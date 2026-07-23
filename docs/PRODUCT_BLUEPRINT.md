# Product Blueprint

## North Star

Cloud-Native AI Meeting Insights is a privacy-first, self-hostable **meeting-to-action** platform. It turns sensitive meeting audio into grounded, reviewable outcomes while keeping operators in control of storage and model routing.

The product is not complete when it produces a transcript. It is complete when a team can review decisions, assign work, and move approved outcomes into its existing workflow.

## Target Users

- Research and biomedical teams handling sensitive discussions
- Engineering teams that need decisions and action items captured reliably
- Organizations that cannot use a third-party meeting SaaS
- Platform teams that require deployment in their own cloud or network

## Canonical Pipeline

1. Audio is uploaded to operator-controlled storage.
2. A durable job is queued with backpressure and retry limits.
3. A worker performs multilingual transcription.
4. A configured local or explicitly approved external model extracts structured outcomes.
5. A human reviews decisions, tasks, owners, dates, risks, and open questions.
6. Approved outcomes can be exported to GitHub, Jira, Slack, or documentation systems.

## Privacy Contract

- `AI_PROVIDER=local` is the default.
- External model use must be an explicit operator decision.
- The UI and API expose the provider used for each result.
- Future releases must add retention policies, audit events, encryption controls, and redaction.

## Delivery Status

### Implemented

- FastAPI meeting API
- PostgreSQL meeting persistence
- Redis-backed asynchronous worker queue
- Faster-Whisper transcription
- Structured meeting outcomes
- Local deterministic fallback extraction
- Explicit OpenAI-compatible provider routing
- Next.js upload, search, meeting history, and structured detail views
- Docker Compose development environment
- Terraform and Kubernetes infrastructure scaffolding

### In Progress

- End-to-end integration tests with real audio fixtures
- Durable object storage shared by API and workers
- Reliable progress updates in the frontend
- Honest reproducible benchmarks
- Deployment validation on AWS

### Planned

- Speaker diarization and timestamped transcript segments
- Human review and editing workflow
- GitHub Issue, Jira, Slack, and Confluence integrations
- Workspace RBAC and authentication
- Retention, redaction, audit logs, and encryption policy
- OpenTelemetry traces and production metrics
- Dead-letter queue and idempotent processing
- Multilingual quality evaluation dataset

## Engineering Principles

1. A documented feature must be executable, not mocked without a label.
2. Performance claims require a reproducible test command and stored raw results.
3. Cloud-native components must solve an observed reliability or scale problem.
4. Privacy behavior must be visible and testable.
5. CI must fail when tests or builds fail.
