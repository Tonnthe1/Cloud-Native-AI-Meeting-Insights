#!/bin/bash

# AWS EKS Deployment Script for Meeting Insights
# This script provides a simple interface for deploying the infrastructure

set -e

# Configuration
TERRAFORM_DIR="terraform"
KUBECTL_VERSION="v1.28.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    
    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_warning "kubectl is not installed. Installing..."
        install_kubectl
    fi
    
    log_success "Prerequisites check passed"
}

install_kubectl() {
    log_info "Installing kubectl..."
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl
    log_success "kubectl installed"
}

terraform_init() {
    log_info "Initializing Terraform..."
    cd $TERRAFORM_DIR
    terraform init
    cd ..
    log_success "Terraform initialized"
}

terraform_plan() {
    log_info "Running Terraform plan..."
    cd $TERRAFORM_DIR
    
    # Auto-detect AWS region if not set
    AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-west-2")
    log_info "Using AWS region: $AWS_REGION"
    
    # Run plan with auto-detected values
    terraform plan -var="aws_region=$AWS_REGION" -out=tfplan
    cd ..
    log_success "Terraform plan completed"
}

terraform_apply() {
    log_info "Applying Terraform configuration..."
    cd $TERRAFORM_DIR
    
    if [ ! -f "tfplan" ]; then
        log_error "No Terraform plan found. Run 'plan' first."
        exit 1
    fi
    
    terraform apply tfplan
    cd ..
    log_success "Infrastructure deployed successfully"
}

terraform_destroy() {
    log_warning "This will destroy ALL infrastructure. Are you sure? (yes/no)"
    read -r response
    if [[ "$response" != "yes" ]]; then
        log_info "Destroy cancelled"
        exit 0
    fi
    
    log_info "Destroying Terraform infrastructure..."
    cd $TERRAFORM_DIR
    terraform destroy -auto-approve
    cd ..
    log_success "Infrastructure destroyed"
}

configure_kubectl() {
    log_info "Configuring kubectl..."
    cd $TERRAFORM_DIR
    
    CLUSTER_NAME=$(terraform output -raw cluster_name 2>/dev/null || echo "")
    AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || grep 'aws_region' terraform.tfvars | cut -d'"' -f2)
    
    if [ -z "$CLUSTER_NAME" ]; then
        log_error "Could not get cluster name from Terraform output"
        exit 1
    fi
    
    aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
    cd ..
    log_success "kubectl configured for cluster: $CLUSTER_NAME"
}

deploy_application() {
    log_info "Deploying application to Kubernetes..."
    
    # First configure kubectl
    configure_kubectl
    
    cd $TERRAFORM_DIR
    
    # Get outputs
    RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
    REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
    SECRETS_ROLE_ARN=$(terraform output -raw secrets_manager_role_arn)
    
    cd ..
    
    # Update ConfigMap with actual endpoints
    log_info "Updating Kubernetes manifests..."
    sed -i.bak "s/REPLACE_WITH_RDS_ENDPOINT/$RDS_ENDPOINT/g" k8s/configmap.yaml
    sed -i.bak "s/REPLACE_WITH_REDIS_ENDPOINT/$REDIS_ENDPOINT/g" k8s/configmap.yaml
    sed -i.bak "s/REPLACE_WITH_SECRETS_MANAGER_ROLE_ARN/$SECRETS_ROLE_ARN/g" k8s/secret.yaml
    
    # Apply manifests
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secret.yaml
    
    # Note: In a real deployment, you would build and push Docker images to ECR first
    log_warning "Note: You need to build and push Docker images to ECR before deploying pods"
    log_info "Application manifests applied. Update image references in deployment files."
    
    # Show instructions for next steps
    echo ""
    log_info "Next Steps to Complete Deployment:"
    echo "1. Build your Docker image: cd ../backend && docker build -t meeting-insights-api ."
    echo "2. Get your ECR repository URL from AWS Console or run: aws ecr describe-repositories --repository-names meeting-insights-api"
    echo "3. Tag your image: docker tag meeting-insights-api:latest <ECR-URL>:latest"
    echo "4. Push to ECR: docker push <ECR-URL>:latest"
    echo "5. Update k8s/api-deployment.yaml with the actual ECR image URL"
    echo "6. Apply the deployments: kubectl apply -f k8s/api-deployment.yaml"
    
    log_success "Application deployment completed"
}

get_cluster_info() {
    cd $TERRAFORM_DIR
    
    if [ ! -f "terraform.tfstate" ]; then
        log_error "No Terraform state found. Deploy infrastructure first."
        exit 1
    fi
    
    log_info "Cluster Information:"
    echo "===================="
    echo "Cluster Name: $(terraform output -raw cluster_name 2>/dev/null || echo 'N/A')"
    echo "Cluster Endpoint: $(terraform output -raw cluster_endpoint 2>/dev/null || echo 'N/A')"
    echo "RDS Endpoint: $(terraform output -raw rds_endpoint 2>/dev/null || echo 'N/A')"
    echo "Redis Endpoint: $(terraform output -raw redis_endpoint 2>/dev/null || echo 'N/A')"
    echo "===================="
    
    cd ..
}

create_ecr_repo() {
    log_info "Creating ECR repository for your Docker images..."
    
    # Check if repository already exists
    if aws ecr describe-repositories --repository-names meeting-insights-api &> /dev/null; then
        log_info "ECR repository 'meeting-insights-api' already exists"
    else
        log_info "Creating ECR repository 'meeting-insights-api'..."
        aws ecr create-repository --repository-name meeting-insights-api
        log_success "ECR repository created"
    fi
    
    # Get the repository URI
    ECR_URI=$(aws ecr describe-repositories --repository-names meeting-insights-api --query 'repositories[0].repositoryUri' --output text)
    log_success "ECR Repository URI: $ECR_URI"
    
    echo ""
    log_info "Docker commands to build and push your image:"
    echo "1. cd ../backend"
    echo "2. docker build -t meeting-insights-api ."
    echo "3. aws ecr get-login-password --region $(aws configure get region) | docker login --username AWS --password-stdin $ECR_URI"
    echo "4. docker tag meeting-insights-api:latest $ECR_URI:latest"
    echo "5. docker push $ECR_URI:latest"
}

show_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  check       - Check prerequisites"
    echo "  init        - Initialize Terraform"
    echo "  plan        - Run Terraform plan"
    echo "  apply       - Apply Terraform configuration"
    echo "  destroy     - Destroy infrastructure"
    echo "  kubectl     - Configure kubectl for the cluster"
    echo "  deploy-app  - Deploy application to Kubernetes"
    echo "  create-ecr  - Create ECR repository and show push commands"
    echo "  info        - Show cluster information"
    echo "  help        - Show this help message"
    echo ""
    echo "Example workflow:"
    echo "  $0 check"
    echo "  $0 init"
    echo "  $0 plan"
    echo "  $0 apply"
    echo "  $0 deploy-app"
}

# Main script logic
case $1 in
    check)
        check_prerequisites
        ;;
    init)
        check_prerequisites
        terraform_init
        ;;
    plan)
        check_prerequisites
        terraform_plan
        ;;
    apply)
        check_prerequisites
        terraform_apply
        ;;
    destroy)
        terraform_destroy
        ;;
    kubectl)
        configure_kubectl
        ;;
    deploy-app)
        deploy_application
        ;;
    create-ecr)
        create_ecr_repo
        ;;
    info)
        get_cluster_info
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        log_error "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac