# Contributing

Thanks for helping improve Meeting Insights.

## Principles

- Keep local/private processing as the default.
- Do not add claims that are not backed by reproducible tests or benchmarks.
- Prefer a small, understandable default stack over experimental infrastructure.
- Never commit meeting recordings, transcripts, credentials, or personal data.
- Preserve compatibility with the one-command Docker Compose path.

## Development setup

```bash
git clone https://github.com/Tonnthe1/Cloud-Native-AI-Meeting-Insights.git
cd Cloud-Native-AI-Meeting-Insights
bash scripts/quickstart.sh doctor
bash scripts/quickstart.sh up
```

Windows:

```powershell
./scripts/quickstart.ps1 doctor
./scripts/quickstart.ps1 up
```

To run the frontend and backend directly, copy `.env.example` to `.env` and use the commands documented in the repository.

## Tests

Backend:

```bash
cd backend
python -m pytest -q
flake8 app tests --ignore=E501,W503
```

Frontend:

```bash
cd frontend
npm ci
npm run build
```

Infrastructure:

```bash
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
docker compose config --quiet
```

## Pull requests

Keep pull requests focused. Include:

- the problem being solved
- the product or privacy impact
- tests performed
- screenshots for user-interface changes
- migration and rollback notes when data or deployment behavior changes

A pull request should not claim performance, reliability, language quality, or production readiness unless the evidence is included and reproducible.

## Architecture changes

Before introducing a new queue, database, inference framework, or cloud service, explain why the existing components cannot meet the measured requirement. Ray and Triton remain experimental until profiling demonstrates a production bottleneck.

## Data and fixtures

Use synthetic, self-recorded, or permissively licensed audio fixtures. Do not upload confidential meetings or copyrighted recordings. Integration tests should remain deterministic and should not require paid APIs.
