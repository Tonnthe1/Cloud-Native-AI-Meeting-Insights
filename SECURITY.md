# Security Policy

Meeting Insights processes potentially sensitive recordings and transcripts. Please report security issues privately rather than opening a public issue.

## Reporting

Use GitHub's private vulnerability reporting feature for this repository when available. Include:

- affected version or commit
- deployment mode (Docker Compose or AWS/EKS)
- reproduction steps
- expected and observed impact
- suggested remediation, when known

Do not include real meeting recordings, transcripts, credentials, tokens, or personal data in a report. Use synthetic examples.

## Supported versions

Security fixes target the current `main` branch and the most recent tagged release. Older unmaintained tags may not receive fixes.

## Security defaults

The self-hosted installer:

- binds local services to `127.0.0.1`
- generates database, object-storage, and API secrets
- uses local insight extraction by default
- deletes raw recordings after successful processing by default
- keeps backend credentials behind the Next.js server-side proxy

Operators remain responsible for:

- TLS and DNS when exposing the service
- authentication and authorization at the network or application layer
- backups and disaster recovery
- key rotation
- meeting consent
- retention policy
- audit requirements
- cloud account and Kubernetes hardening

## Known limitations

The project does not yet include user accounts, workspace isolation, RBAC, or a complete audit log. Do not expose the default self-hosted deployment directly to the public internet. Place it behind an authenticated reverse proxy or private network until application-level access control is implemented.
