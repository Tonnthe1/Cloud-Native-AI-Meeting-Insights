# EKS Cluster
module "eks" {
  source = "terraform-aws-modules/eks/aws"
  version = "~> 19.15"

  cluster_name    = local.cluster_name
  cluster_version = var.cluster_version

  # Networking
  vpc_id                          = module.vpc.vpc_id
  subnet_ids                      = module.vpc.private_subnets
  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  # Control plane logging
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    main = {
      name = "${local.cluster_name}-nodes"

      instance_types = var.node_instance_types
      capacity_type  = "ON_DEMAND"  # Can be changed to SPOT for cost savings

      min_size     = var.node_min_capacity
      max_size     = var.node_max_capacity
      desired_size = var.node_desired_capacity

      # Node group configuration
      ami_type       = "AL2_x86_64"
      disk_size      = 20  # GB - minimum recommended
      
      # Labels and taints
      labels = {
        Environment = var.environment
        NodeGroup   = "main"
      }

      # Instance configuration
      remote_access = {
        ec2_ssh_key = null  # Set to your key pair name if needed
        source_security_group_ids = []
      }

      # Update configuration
      update_config = {
        max_unavailable_percentage = 25
      }
    }
  }

  # aws-auth configmap
  manage_aws_auth_configmap = true
  aws_auth_roles = [
    # Add additional IAM roles here if needed
  ]
  aws_auth_users = [
    # Add IAM users here if needed
  ]

  tags = merge(var.tags, {
    Environment = var.environment
  })
}

# Additional security group rules for the cluster
resource "aws_security_group_rule" "cluster_ingress_workstation_https" {
  count       = length(var.allowed_cidr_blocks) > 0 ? 1 : 0
  description = "Allow workstation to communicate with the cluster API Server"
  type        = "ingress"
  from_port   = 443
  to_port     = 443
  protocol    = "tcp"
  cidr_blocks = var.allowed_cidr_blocks

  security_group_id = module.eks.cluster_security_group_id
}

# IAM role for EKS service account (for AWS Load Balancer Controller)
module "load_balancer_controller_irsa_role" {
  source = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${local.cluster_name}-load-balancer-controller"

  attach_load_balancer_controller_policy = true

  oidc_providers = {
    ex = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }

  tags = var.tags
}

# EBS CSI Driver IRSA role
module "ebs_csi_irsa_role" {
  source = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${local.cluster_name}-ebs-csi-driver"

  attach_ebs_csi_policy = true

  oidc_providers = {
    ex = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["kube-system:ebs-csi-controller-sa"]
    }
  }

  tags = var.tags
}