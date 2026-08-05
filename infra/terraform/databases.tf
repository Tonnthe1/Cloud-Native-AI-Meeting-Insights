# Generate random password for RDS
resource "random_password" "db_password" {
  length  = 16
  special = true
}

# RDS PostgreSQL Database
resource "aws_db_instance" "postgresql" {
  identifier     = "${local.cluster_name}-postgres"
  engine         = "postgres"
  engine_version = "15"
  instance_class = var.db_instance_class

  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  publicly_accessible    = false

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  performance_insights_enabled = false
  monitoring_interval          = 0

  deletion_protection = false
  skip_final_snapshot = true

  auto_minor_version_upgrade = true

  tags = merge(var.tags, {
    Name        = "${local.cluster_name}-postgres"
    Environment = var.environment
  })
}

# ElastiCache Redis Cluster
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${local.cluster_name}-redis"
  description          = "Redis cluster for Meeting Insights"

  node_type            = var.redis_node_type
  port                 = 6379
  parameter_group_name = "default.redis7"

  num_cache_clusters = 1

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  snapshot_retention_limit = 1
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:09:00"

  at_rest_encryption_enabled = true
  transit_encryption_enabled = false

  automatic_failover_enabled = false

  tags = merge(var.tags, {
    Name        = "${local.cluster_name}-redis"
    Environment = var.environment
  })
}

# Store database password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name        = "${local.cluster_name}-db-password"
  description = "Database password for Meeting Insights PostgreSQL"

  tags = merge(var.tags, {
    Environment = var.environment
  })
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id = aws_secretsmanager_secret.db_password.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
    hostname = aws_db_instance.postgresql.endpoint
    port     = aws_db_instance.postgresql.port
    dbname   = var.db_name
  })
}

# Shared runtime role for the API and worker. Service accounts are created in
# storage.tf and annotated with this role through IRSA.
module "secrets_manager_irsa_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${local.cluster_name}-app-runtime"

  role_policy_arns = {
    secrets = aws_iam_policy.secrets_manager.arn
    storage = aws_iam_policy.object_storage.arn
  }

  oidc_providers = {
    ex = {
      provider_arn = module.eks.oidc_provider_arn
      namespace_service_accounts = [
        "meeting-insights:meeting-insights-api",
        "meeting-insights:meeting-insights-worker"
      ]
    }
  }

  tags = var.tags
}

resource "aws_iam_policy" "secrets_manager" {
  name        = "${local.cluster_name}-secrets-manager"
  description = "Policy for accessing secrets from EKS"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn
        ]
      }
    ]
  })

  tags = var.tags
}
