# AWS EKS deployment

The Terraform, Kubernetes, and deployment entrypoints in this directory are definition-validated. They have not been live-applied for this project.

## Quick Start

1. **Prerequisites** (one-time setup):
   ```bash
   # Install AWS CLI and configure credentials
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip && sudo ./aws/install
   aws configure  # Enter your AWS credentials
   ```

2. **Validate and review the plan**:
   ```bash
   cd infra
   ./deploy.sh init
   ./deploy.sh plan
   ```

3. **Apply only after reviewing the plan and account-level cost/security controls**:
   ```bash
   CONFIRM_DEPLOY=yes ./one-click-deploy.sh
   ```

## What Gets Deployed

- ✅ **EKS Kubernetes Cluster** - Fully managed Kubernetes
- ✅ **PostgreSQL Database** - RDS with automated backups
- ✅ **Redis Cache** - ElastiCache for session storage  
- ✅ **Load Balancers** - AWS Application Load Balancer
- ✅ **Container Registry** - ECR with your app images
- ✅ **Networking** - VPC with public/private subnets
- ✅ **Security** - IAM roles, security groups, encrypted storage

## Automated configuration

- ✨ **Auto-detects** your AWS region and account
- ✨ **Generates** unique cluster names automatically  
- ✨ **Builds and pushes** Docker images to ECR
- ✨ **Configures** all Kubernetes manifests dynamically
- ✨ **Sets up** kubectl access automatically

## Cost

This stack creates billable EKS, EC2, NAT Gateway, RDS, ElastiCache, S3, load-balancer, and related resources. No monthly cost estimate has been validated; calculate it for the target region and account before applying.

## Cleanup

To remove everything and stop charges:
```bash
cd infra
CONFIRM_DESTROY=yes ./deploy.sh destroy
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

The checked-in development defaults use a managed EKS node group, one RDS instance, one Redis node, and one NAT Gateway. DNS, TLS, high availability, backup/restore, scaling, and rollback behavior require an owner-operated deployment review.
