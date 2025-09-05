# 🚀 One-Click AWS EKS Deployment

Deploy a complete cloud-native AI meeting insights platform with a single command!

## Quick Start

1. **Prerequisites** (one-time setup):
   ```bash
   # Install AWS CLI and configure credentials
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip && sudo ./aws/install
   aws configure  # Enter your AWS credentials
   ```

2. **Deploy everything**:
   ```bash
   cd infra
   ./one-click-deploy.sh
   ```

That's it! ☕ Grab some coffee while it deploys (~15-20 minutes).

## What Gets Deployed

- ✅ **EKS Kubernetes Cluster** - Fully managed Kubernetes
- ✅ **PostgreSQL Database** - RDS with automated backups
- ✅ **Redis Cache** - ElastiCache for session storage  
- ✅ **Load Balancers** - AWS Application Load Balancer
- ✅ **Container Registry** - ECR with your app images
- ✅ **Networking** - VPC with public/private subnets
- ✅ **Security** - IAM roles, security groups, encrypted storage

## Zero Configuration Required

- ✨ **Auto-detects** your AWS region and account
- ✨ **Generates** unique cluster names automatically  
- ✨ **Builds and pushes** Docker images to ECR
- ✨ **Configures** all Kubernetes manifests dynamically
- ✨ **Sets up** kubectl access automatically

## Cost

Estimated monthly cost: **$50-100** for development usage

## Cleanup

To remove everything and stop charges:
```bash
cd infra/terraform
terraform destroy
```

## Advanced Usage

If you want more control, you can still use the individual commands:
```bash
cd infra
./deploy.sh check    # Check prerequisites  
./deploy.sh init     # Initialize Terraform
./deploy.sh plan     # Plan deployment
./deploy.sh apply    # Deploy infrastructure
```

## Architecture

```
Internet → AWS ALB → EKS Cluster → FastAPI Pods → RDS PostgreSQL
                                              → ElastiCache Redis
```

Your application runs in a highly available, auto-scaling Kubernetes cluster with managed databases and automatic SSL termination.