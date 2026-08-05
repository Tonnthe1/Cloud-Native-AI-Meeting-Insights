#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT_DIR=$(cd "${SCRIPT_DIR}/.." && pwd)
TF_DIR="${SCRIPT_DIR}/terraform"
K8S_DIR="${SCRIPT_DIR}/k8s"
ENVIRONMENT=${ENVIRONMENT:-dev}
AWS_REGION=${AWS_REGION:-us-west-2}
CLUSTER_NAME_OVERRIDE=${CLUSTER_NAME_OVERRIDE:-meeting-insights-${ENVIRONMENT}}
IMAGE_TAG=${IMAGE_TAG:-$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo latest)}
STATE_LOCK_TABLE=${STATE_LOCK_TABLE:-meeting-insights-terraform-locks}
STATE_KEY=${STATE_KEY:-meeting-insights/${ENVIRONMENT}/terraform.tfstate}

log() {
  printf '[meeting-insights] %s\n' "$*"
}

require_commands() {
  local missing=0
  for command in "$@"; do
    if ! command -v "${command}" >/dev/null 2>&1; then
      printf 'Missing required command: %s\n' "${command}" >&2
      missing=1
    fi
  done
  test "${missing}" -eq 0
}

tf() {
  terraform -chdir="${TF_DIR}" "$@"
}

check() {
  require_commands aws terraform kubectl docker helm sed jq
  aws sts get-caller-identity >/dev/null
  log "Prerequisites are available."
}

bootstrap_terraform_state() {
  local account_id bucket
  account_id=$(aws sts get-caller-identity --query Account --output text)
  bucket=${TF_STATE_BUCKET:-${account_id}-meeting-insights-tfstate-${AWS_REGION}}
  export TF_STATE_BUCKET=${bucket}

  if ! aws s3api head-bucket --bucket "${bucket}" 2>/dev/null; then
    if [[ "${AWS_REGION}" == "us-east-1" ]]; then
      aws s3api create-bucket --bucket "${bucket}" --region "${AWS_REGION}" >/dev/null
    else
      aws s3api create-bucket \
        --bucket "${bucket}" \
        --region "${AWS_REGION}" \
        --create-bucket-configuration LocationConstraint="${AWS_REGION}" >/dev/null
    fi
  fi

  aws s3api put-public-access-block \
    --bucket "${bucket}" \
    --public-access-block-configuration \
      BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-encryption \
    --bucket "${bucket}" \
    --server-side-encryption-configuration \
      '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-bucket-versioning \
    --bucket "${bucket}" \
    --versioning-configuration Status=Enabled

  if ! aws dynamodb describe-table \
    --region "${AWS_REGION}" \
    --table-name "${STATE_LOCK_TABLE}" >/dev/null 2>&1; then
    aws dynamodb create-table \
      --region "${AWS_REGION}" \
      --table-name "${STATE_LOCK_TABLE}" \
      --attribute-definitions AttributeName=LockID,AttributeType=S \
      --key-schema AttributeName=LockID,KeyType=HASH \
      --billing-mode PAY_PER_REQUEST >/dev/null
    aws dynamodb wait table-exists \
      --region "${AWS_REGION}" \
      --table-name "${STATE_LOCK_TABLE}"
  fi

  tf init -reconfigure \
    -backend-config="bucket=${bucket}" \
    -backend-config="key=${STATE_KEY}" \
    -backend-config="region=${AWS_REGION}" \
    -backend-config="dynamodb_table=${STATE_LOCK_TABLE}" \
    -backend-config="encrypt=true"
}

init() {
  check
  bootstrap_terraform_state
  tf fmt -check -recursive
  tf validate
}

plan() {
  init
  tf plan \
    -var="environment=${ENVIRONMENT}" \
    -var="aws_region=${AWS_REGION}" \
    -var="cluster_name_override=${CLUSTER_NAME_OVERRIDE}" \
    -out=tfplan
}

apply() {
  if [[ ! -f "${TF_DIR}/tfplan" ]]; then
    plan
  fi
  tf apply tfplan
}

configure_kubectl() {
  local cluster_name
  bootstrap_terraform_state
  cluster_name=$(tf output -raw cluster_name)
  AWS_REGION=$(tf output -raw aws_region)
  export AWS_REGION
  aws eks update-kubeconfig --region "${AWS_REGION}" --name "${cluster_name}"
}

ensure_ecr_repository() {
  local repository=$1
  aws ecr describe-repositories \
    --region "${AWS_REGION}" \
    --repository-names "${repository}" >/dev/null 2>&1 || \
    aws ecr create-repository \
      --region "${AWS_REGION}" \
      --repository-name "${repository}" >/dev/null
}

build_and_push() {
  check
  local account_id
  account_id=$(aws sts get-caller-identity --query Account --output text)
  ECR_REGISTRY=${ECR_REGISTRY:-${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com}
  export ECR_REGISTRY

  aws ecr get-login-password --region "${AWS_REGION}" | \
    docker login --username AWS --password-stdin "${ECR_REGISTRY}"

  ensure_ecr_repository meeting-insights-api
  ensure_ecr_repository meeting-insights-worker
  ensure_ecr_repository meeting-insights-frontend

  docker build -t "${ECR_REGISTRY}/meeting-insights-api:${IMAGE_TAG}" "${ROOT_DIR}/backend"
  docker build -f "${ROOT_DIR}/backend/Dockerfile.worker" \
    -t "${ECR_REGISTRY}/meeting-insights-worker:${IMAGE_TAG}" \
    "${ROOT_DIR}/backend"
  docker build -t "${ECR_REGISTRY}/meeting-insights-frontend:${IMAGE_TAG}" \
    "${ROOT_DIR}/frontend"

  docker push "${ECR_REGISTRY}/meeting-insights-api:${IMAGE_TAG}"
  docker push "${ECR_REGISTRY}/meeting-insights-worker:${IMAGE_TAG}"
  docker push "${ECR_REGISTRY}/meeting-insights-frontend:${IMAGE_TAG}"
}

render_manifests() {
  local output_dir=$1
  local rds_endpoint redis_endpoint s3_bucket region

  rds_endpoint=$(tf output -raw rds_endpoint)
  redis_endpoint=$(tf output -raw redis_endpoint)
  s3_bucket=$(tf output -raw meeting_audio_bucket)
  region=$(tf output -raw aws_region)

  cp "${K8S_DIR}/configmap.yaml" "${output_dir}/configmap.yaml"
  cp "${K8S_DIR}/api-deployment.yaml" "${output_dir}/api-deployment.yaml"
  cp "${K8S_DIR}/worker-deployment.yaml" "${output_dir}/worker-deployment.yaml"
  cp "${K8S_DIR}/frontend-deployment.yaml" "${output_dir}/frontend-deployment.yaml"
  cp "${K8S_DIR}/ingress.yaml" "${output_dir}/ingress.yaml"

  sed -i.bak "s/REPLACE_WITH_RDS_ENDPOINT/${rds_endpoint}/g" "${output_dir}/configmap.yaml"
  sed -i.bak "s/REPLACE_WITH_REDIS_ENDPOINT/${redis_endpoint}/g" "${output_dir}/configmap.yaml"
  sed -i.bak "s/REPLACE_WITH_S3_BUCKET/${s3_bucket}/g" "${output_dir}/configmap.yaml"
  sed -i.bak "s/REPLACE_WITH_AWS_REGION/${region}/g" "${output_dir}/configmap.yaml"

  sed -i.bak -E \
    "s|image: .*meeting-insights-api:latest.*|image: ${ECR_REGISTRY}/meeting-insights-api:${IMAGE_TAG}|" \
    "${output_dir}/api-deployment.yaml"
  sed -i.bak -E \
    "s|image: .*meeting-insights-worker:latest.*|image: ${ECR_REGISTRY}/meeting-insights-worker:${IMAGE_TAG}|" \
    "${output_dir}/worker-deployment.yaml"
  sed -i.bak -E \
    "s|image: .*meeting-insights-frontend:latest.*|image: ${ECR_REGISTRY}/meeting-insights-frontend:${IMAGE_TAG}|" \
    "${output_dir}/frontend-deployment.yaml"
  rm -f "${output_dir}"/*.bak
}

create_runtime_identity() {
  local role_arn db_secret_name db_secret db_username db_password

  role_arn=$(tf output -raw application_runtime_role_arn)
  db_secret_name=$(tf output -raw db_secret_name)

  kubectl apply -f "${K8S_DIR}/namespace.yaml"
  for service_account in meeting-insights-api meeting-insights-worker; do
    kubectl create serviceaccount "${service_account}" \
      --namespace meeting-insights \
      --dry-run=client -o yaml | kubectl apply -f -
    kubectl annotate serviceaccount "${service_account}" \
      --namespace meeting-insights \
      eks.amazonaws.com/role-arn="${role_arn}" \
      --overwrite
  done

  db_secret=$(aws secretsmanager get-secret-value \
    --region "${AWS_REGION}" \
    --secret-id "${db_secret_name}" \
    --query SecretString \
    --output text)
  db_username=$(jq -r '.username' <<<"${db_secret}")
  db_password=$(jq -r '.password' <<<"${db_secret}")

  kubectl create secret generic db-credentials \
    --namespace meeting-insights \
    --from-literal=username="${db_username}" \
    --from-literal=password="${db_password}" \
    --dry-run=client -o yaml | kubectl apply -f -
}

ensure_load_balancer_controller() {
  local chart_version role_arn cluster_name vpc_id
  chart_version=1.14.0
  role_arn=$(tf output -raw load_balancer_controller_role_arn)
  cluster_name=$(tf output -raw cluster_name)
  vpc_id=$(tf output -raw vpc_id)

  kubectl create serviceaccount aws-load-balancer-controller \
    --namespace kube-system \
    --dry-run=client -o yaml | kubectl apply -f -
  kubectl annotate serviceaccount aws-load-balancer-controller \
    --namespace kube-system \
    eks.amazonaws.com/role-arn="${role_arn}" \
    --overwrite

  helm repo add eks https://aws.github.io/eks-charts --force-update
  helm show crds eks/aws-load-balancer-controller \
    --version "${chart_version}" | kubectl apply -f -
  helm upgrade --install aws-load-balancer-controller \
    eks/aws-load-balancer-controller \
    --namespace kube-system \
    --version "${chart_version}" \
    --set clusterName="${cluster_name}" \
    --set region="${AWS_REGION}" \
    --set vpcId="${vpc_id}" \
    --set serviceAccount.create=false \
    --set serviceAccount.name=aws-load-balancer-controller \
    --wait \
    --timeout 10m
}

deploy() {
  check
  configure_kubectl

  if [[ -z "${ECR_REGISTRY:-}" ]]; then
    local account_id
    account_id=$(aws sts get-caller-identity --query Account --output text)
    ECR_REGISTRY="${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com"
    export ECR_REGISTRY
  fi

  local rendered
  rendered=$(mktemp -d)
  trap 'rm -rf "${rendered}"' RETURN
  render_manifests "${rendered}"
  create_runtime_identity
  ensure_load_balancer_controller

  kubectl apply -f "${rendered}/configmap.yaml"
  kubectl create secret generic meeting-insights-secrets \
    --namespace meeting-insights \
    --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    --from-literal=API_KEY="${API_KEY:-}" \
    --dry-run=client -o yaml | kubectl apply -f -

  kubectl apply -f "${rendered}/api-deployment.yaml"
  kubectl apply -f "${rendered}/worker-deployment.yaml"
  kubectl apply -f "${rendered}/frontend-deployment.yaml"
  kubectl apply -f "${rendered}/ingress.yaml"

  kubectl wait --for=condition=available --timeout=10m \
    deployment/meeting-insights-api -n meeting-insights
  kubectl wait --for=condition=available --timeout=10m \
    deployment/meeting-insights-worker -n meeting-insights
  kubectl wait --for=condition=available --timeout=10m \
    deployment/meeting-insights-frontend -n meeting-insights

  log "Deployment is available through the meeting-insights-ingress ALB."
  kubectl get ingress meeting-insights-ingress -n meeting-insights
}

destroy() {
  if [[ "${CONFIRM_DESTROY:-}" != "yes" ]]; then
    printf 'Set CONFIRM_DESTROY=yes to destroy the environment.\n' >&2
    exit 1
  fi
  init
  tf destroy \
    -var="environment=${ENVIRONMENT}" \
    -var="aws_region=${AWS_REGION}" \
    -var="cluster_name_override=${CLUSTER_NAME_OVERRIDE}" \
    -auto-approve
}

info() {
  check
  bootstrap_terraform_state
  tf output
}

usage() {
  cat <<'EOF'
Usage: infra/deploy.sh <command>

Commands:
  check       Verify local dependencies and AWS credentials
  init        Bootstrap remote state, initialize, and validate Terraform
  plan        Create a Terraform plan
  apply       Apply the current plan (creates one when missing)
  build       Build and push API, worker, and frontend images
  deploy      Render manifests from Terraform outputs and deploy to EKS
  all         Plan, apply, build, and deploy
  destroy     Destroy application infrastructure; requires CONFIRM_DESTROY=yes
  info        Print Terraform outputs
EOF
}

case "${1:-}" in
  check) check ;;
  init) init ;;
  plan) plan ;;
  apply) apply ;;
  build) build_and_push ;;
  deploy) deploy ;;
  all)
    plan
    apply
    build_and_push
    deploy
    ;;
  destroy) destroy ;;
  info) info ;;
  *) usage; exit 1 ;;
esac
