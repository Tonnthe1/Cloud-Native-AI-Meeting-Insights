#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

cat <<'EOF'
Meeting Insights AWS deployment

This command will plan and apply AWS infrastructure, build and push three
container images, configure EKS runtime identities, and deploy the application.
It can create billable AWS resources. Review infra/terraform and run
`./deploy.sh plan` first when operating a production account.
EOF

if [[ "${CONFIRM_DEPLOY:-}" != "yes" ]]; then
  printf '\nSet CONFIRM_DEPLOY=yes to continue.\n' >&2
  exit 1
fi

exec "${SCRIPT_DIR}/deploy.sh" all
