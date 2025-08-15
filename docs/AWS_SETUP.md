# AWS EKS Setup Guide

This guide walks you through setting up the Cloud-Native AI Meeting Insights platform on AWS EKS.

## Prerequisites

### Required Tools
- **AWS CLI v2**: [Installation Guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- **Terraform >= 1.6**: [Installation Guide](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
- **kubectl**: [Installation Guide](https://kubernetes.io/docs/tasks/tools/)
- **Git**: For cloning the repository

### AWS Permissions Required

Your AWS user/role needs the following permissions for EKS deployment:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "eks:*",
                "ec2:*",
                "rds:*",
                "elasticache:*",
                "iam:*",
                "secretsmanager:*",
                "ecr:*",
                "logs:*"
            ],
            "Resource": "*"
        }
    ]
}
```

**Note**: This is a broad permission set. For production, use more restrictive policies.

## Setup Steps

### 1. Configure AWS CLI

```bash
aws configure
# Enter your Access Key ID, Secret Access Key, Region (us-west-2), and output format (json)

# Verify configuration
aws sts get-caller-identity
```

### 2. Clone Repository and Setup

```bash
git clone https://github.com/yourusername/cloud-native-ai-meeting-insights.git
cd cloud-native-ai-meeting-insights
```

### 3. GitHub Actions Deployment (Recommended)

#### Set GitHub Secrets

Go to your repository → Settings → Secrets and variables → Actions, and add:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `OPENAI_API_KEY`: Your OpenAI API key
- `API_KEY`: (Optional) API security key

#### Deploy via GitHub Actions

1. Go to Actions tab in your GitHub repository
2. Select "Deploy to AWS EKS" workflow
3. Click "Run workflow"
4. Choose:
   - **Environment**: `dev` (for testing)
   - **Terraform action**: `plan` (review first, then `apply`)
5. Monitor the deployment progress

### 4. Local Terraform Deployment

If you prefer to deploy locally:

```bash
cd infra

# Check prerequisites
./deploy.sh check

# Initialize Terraform
./deploy.sh init

# Configure variables (edit terraform.tfvars)
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit the file with your preferred configuration

# Plan deployment (review resources and costs)
./deploy.sh plan

# Deploy infrastructure (10-20 minutes)
./deploy.sh apply

# Configure kubectl
./deploy.sh kubectl

# Get cluster information
./deploy.sh info
```

## Post-Deployment

### Access Your Application

After deployment, get the LoadBalancer URLs:

```bash
# API service
kubectl get svc meeting-insights-api-lb -n meeting-insights

# Frontend service
kubectl get svc meeting-insights-frontend-lb -n meeting-insights
```

### Monitor Resources

```bash
# Check pod status
kubectl get pods -n meeting-insights

# Check logs
kubectl logs -f deployment/meeting-insights-api -n meeting-insights
kubectl logs -f deployment/meeting-insights-worker -n meeting-insights

# Check resource usage
kubectl top nodes
kubectl top pods -n meeting-insights
```

## Cost Management

### Monitor Costs

- Use AWS Cost Explorer to track spending
- Set up billing alerts in AWS
- Review the cost breakdown by service

### Cost Optimization

- **Auto-scaling**: Nodes scale down to minimum (1) when not in use
- **Spot instances**: Consider using spot instances for worker nodes in non-prod
- **Scheduled scaling**: Scale down during off-hours
- **Resource requests**: Pods have appropriate resource limits

### Cleanup

To avoid ongoing charges:

```bash
# Via local script
cd infra
./deploy.sh destroy

# Or via GitHub Actions
# Go to Actions → Deploy to AWS EKS → Run workflow → Choose "destroy"
```

## Troubleshooting

### Common Issues

#### 1. EKS Cluster Access Denied
```bash
# Update kubeconfig
aws eks update-kubeconfig --region us-west-2 --name your-cluster-name

# Check AWS CLI configuration
aws sts get-caller-identity
```

#### 2. Pods Stuck in Pending
```bash
# Check node capacity
kubectl describe nodes

# Check pod events
kubectl describe pod <pod-name> -n meeting-insights
```

#### 3. Database Connection Issues
```bash
# Check RDS security groups
aws rds describe-db-instances --db-instance-identifier meeting-insights-postgres

# Check secrets
kubectl get secrets -n meeting-insights
```

#### 4. Load Balancer Not Creating
```bash
# Check AWS Load Balancer Controller
kubectl get deployment -n kube-system aws-load-balancer-controller

# Check ingress events
kubectl describe ingress -n meeting-insights
```

### Getting Help

1. Check CloudWatch logs for detailed error messages
2. Review AWS EKS cluster status in AWS Console
3. Use `kubectl describe` for resource-specific issues
4. Check GitHub Actions logs for deployment failures

## Production Considerations

### Security Hardening

- Enable EKS cluster logging
- Configure network policies
- Use AWS Secrets Manager for sensitive data
- Enable encryption at rest and in transit
- Regular security patching

### High Availability

- Deploy across multiple AZs
- Use multiple NAT gateways
- Configure RDS Multi-AZ
- Use Redis clustering

### Monitoring

- Set up CloudWatch monitoring
- Configure alerts for resource usage
- Monitor application performance
- Track cost metrics

### Backup Strategy

- RDS automated backups
- EKS etcd backups
- Application data backup procedures
- Disaster recovery testing