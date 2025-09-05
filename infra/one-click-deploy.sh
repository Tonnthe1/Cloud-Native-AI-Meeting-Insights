#!/bin/bash

# ONE-CLICK AWS EKS DEPLOYMENT FOR MEETING INSIGHTS
# This script deploys everything automatically with zero manual configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
TERRAFORM_DIR="terraform"

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

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

print_banner() {
    echo -e "${PURPLE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              🚀 Meeting Insights One-Click Deploy           ║"
    echo "║                                                              ║"
    echo "║  This will automatically deploy a complete cloud-native     ║"
    echo "║  AI meeting insights platform on AWS EKS.                   ║"
    echo "║                                                              ║"
    echo "║  What gets deployed:                                         ║"
    echo "║  • EKS Kubernetes Cluster                                    ║"
    echo "║  • PostgreSQL Database (RDS)                                ║"
    echo "║  • Redis Cache (ElastiCache)                                ║"
    echo "║  • Load Balancers & Networking                               ║"
    echo "║  • Container Registry (ECR)                                  ║"
    echo "║                                                              ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_prerequisites() {
    log_step "1/8: Checking prerequisites..."
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first:"
        echo "  curl \"https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip\" -o \"awscliv2.zip\""
        echo "  unzip awscliv2.zip && sudo ./aws/install"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Run:"
        echo "  aws configure"
        echo "Then provide your AWS Access Key ID and Secret Access Key"
        exit 1
    fi
    
    # Check Terraform
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Installing automatically..."
        install_terraform
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first:"
        echo "  curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh"
        exit 1
    fi
    
    # Install kubectl if missing
    if ! command -v kubectl &> /dev/null; then
        log_info "Installing kubectl..."
        install_kubectl
    fi
    
    log_success "All prerequisites satisfied"
}

install_terraform() {
    log_info "Installing Terraform..."
    curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
    sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
    sudo apt-get update && sudo apt-get install terraform
    log_success "Terraform installed"
}

install_kubectl() {
    KUBECTL_VERSION="v1.28.0"
    curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
    sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
    rm kubectl
    log_success "kubectl installed"
}

auto_detect_config() {
    log_step "2/8: Auto-detecting AWS configuration..."
    
    # Get AWS account ID
    export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    log_info "AWS Account ID: $AWS_ACCOUNT_ID"
    
    # Get AWS region
    export AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-west-2")
    log_info "AWS Region: $AWS_REGION"
    
    # Generate unique cluster name
    export CLUSTER_SUFFIX=$(date +%s | tail -c 7)
    export CLUSTER_NAME="meeting-insights-$CLUSTER_SUFFIX"
    log_info "Cluster Name: $CLUSTER_NAME"
    
    # Set ECR repository URI
    export ECR_REPOSITORY_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/meeting-insights-api"
    log_info "ECR Repository: $ECR_REPOSITORY_URI"
    
    # Check for OpenAI API key
    if [ -z "$OPENAI_API_KEY" ]; then
        log_warning "OpenAI API key not found in environment"
        echo "You can set it later in the Kubernetes secret or skip AI summaries"
        read -p "Continue without OpenAI API key? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Please set OPENAI_API_KEY environment variable and re-run"
            exit 1
        fi
    else
        log_success "OpenAI API key detected"
    fi
    
    log_success "Configuration auto-detected"
}

deploy_infrastructure() {
    log_step "3/8: Deploying infrastructure with Terraform..."
    
    cd $TERRAFORM_DIR
    
    # Initialize Terraform
    log_info "Initializing Terraform..."
    terraform init
    
    # Plan deployment
    log_info "Planning infrastructure deployment..."
    terraform plan \
        -var="aws_region=$AWS_REGION" \
        -var="cluster_name_override=$CLUSTER_NAME" \
        -out=tfplan
    
    # Apply deployment
    log_info "Creating AWS infrastructure (this takes ~15-20 minutes)..."
    echo "☕ Grab some coffee while AWS provisions your cluster..."
    terraform apply tfplan
    
    cd ..
    log_success "Infrastructure deployed successfully"
}

create_ecr_and_build() {
    log_step "4/8: Setting up container registry and building images..."
    
    # Create ECR repository
    log_info "Creating ECR repository..."
    aws ecr create-repository --repository-name meeting-insights-api --region $AWS_REGION 2>/dev/null || {
        log_info "ECR repository already exists"
    }
    
    # Build Docker image
    log_info "Building Docker image..."
    cd ../backend
    docker build -t meeting-insights-api .
    
    # Login to ECR
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REPOSITORY_URI
    
    # Tag and push image
    log_info "Pushing image to ECR..."
    docker tag meeting-insights-api:latest $ECR_REPOSITORY_URI:latest
    docker push $ECR_REPOSITORY_URI:latest
    
    cd ../infra
    log_success "Container image built and pushed"
}

configure_kubectl() {
    log_step "5/8: Configuring kubectl..."
    
    cd $TERRAFORM_DIR
    aws eks update-kubeconfig --region $AWS_REGION --name $CLUSTER_NAME
    cd ..
    
    # Test connection
    kubectl cluster-info
    log_success "kubectl configured successfully"
}

get_terraform_outputs() {
    log_step "6/8: Retrieving infrastructure information..."
    
    cd $TERRAFORM_DIR
    export RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
    export REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
    cd ..
    
    log_info "RDS Endpoint: $RDS_ENDPOINT"
    log_info "Redis Endpoint: $REDIS_ENDPOINT"
    log_success "Infrastructure info retrieved"
}

deploy_application() {
    log_step "7/8: Deploying application to Kubernetes..."
    
    # Process templates and create actual manifests
    log_info "Processing Kubernetes manifests..."
    
    # Process ConfigMap
    sed -e "s|{{RDS_ENDPOINT}}|$RDS_ENDPOINT|g" \
        -e "s|{{REDIS_ENDPOINT}}|$REDIS_ENDPOINT|g" \
        -e "s|{{AWS_REGION}}|$AWS_REGION|g" \
        k8s/configmap.template.yaml > k8s/configmap-generated.yaml
    
    # Process API Deployment
    sed -e "s|{{ECR_REPOSITORY_URI}}|$ECR_REPOSITORY_URI|g" \
        k8s/api-deployment.template.yaml > k8s/api-deployment-generated.yaml
    
    # Deploy to Kubernetes
    log_info "Applying Kubernetes manifests..."
    kubectl apply -f k8s/namespace.yaml
    kubectl apply -f k8s/configmap-generated.yaml
    kubectl apply -f k8s/secret.yaml
    kubectl apply -f k8s/api-deployment-generated.yaml
    
    # Wait for pods to be ready
    log_info "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app=meeting-insights-api -n meeting-insights --timeout=300s
    
    log_success "Application deployed successfully"
}

show_final_info() {
    log_step "8/8: Deployment complete! 🎉"
    
    echo ""
    log_success "Your Meeting Insights platform is now running!"
    echo ""
    echo "📊 Cluster Information:"
    echo "  • Cluster Name: $CLUSTER_NAME"
    echo "  • AWS Region: $AWS_REGION"
    echo "  • ECR Repository: $ECR_REPOSITORY_URI"
    echo ""
    echo "🔧 Useful Commands:"
    echo "  • View pods: kubectl get pods -n meeting-insights"
    echo "  • View logs: kubectl logs -f -l app=meeting-insights-api -n meeting-insights"
    echo "  • Port forward: kubectl port-forward svc/meeting-insights-api 8000:80 -n meeting-insights"
    echo ""
    echo "🌐 Access your API:"
    echo "  • Run: kubectl port-forward svc/meeting-insights-api 8000:80 -n meeting-insights"
    echo "  • Then visit: http://localhost:8000/docs"
    echo ""
    echo "💰 Cost Management:"
    echo "  • To destroy everything: cd infra/terraform && terraform destroy"
    echo ""
    echo "✅ Setup complete! Your cloud-native AI platform is ready to use."
}

# Main execution
main() {
    print_banner
    
    # Confirm before proceeding
    echo "This will create AWS resources that may incur charges."
    echo "Estimated monthly cost: ~$50-100 for development usage"
    echo ""
    read -p "Do you want to proceed? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy]([Ee][Ss])?$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
    
    check_prerequisites
    auto_detect_config
    deploy_infrastructure
    create_ecr_and_build
    configure_kubectl
    get_terraform_outputs
    deploy_application
    show_final_info
}

# Run the deployment
main "$@"