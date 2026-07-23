# Private object storage for uploaded meeting audio.
resource "aws_s3_bucket" "meeting_audio" {
  bucket        = lower("${local.cluster_name}-audio-${data.aws_caller_identity.current.account_id}")
  force_destroy = var.environment != "prod"

  tags = merge(var.tags, {
    Name        = "${local.cluster_name}-meeting-audio"
    Environment = var.environment
  })
}

resource "aws_s3_bucket_public_access_block" "meeting_audio" {
  bucket = aws_s3_bucket.meeting_audio.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "meeting_audio" {
  bucket = aws_s3_bucket.meeting_audio.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "meeting_audio" {
  bucket = aws_s3_bucket.meeting_audio.id

  rule {
    id     = "expire-meeting-audio"
    status = "Enabled"

    expiration {
      days = var.audio_retention_days
    }
  }
}

resource "aws_iam_policy" "object_storage" {
  name        = "${local.cluster_name}-object-storage"
  description = "Least-privilege access to meeting audio in S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetBucketLocation",
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.meeting_audio.arn
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.meeting_audio.arn}/meetings/*"
      }
    ]
  })

  tags = var.tags
}

# Terraform creates the namespace and IRSA-enabled service accounts so pods never
# need static AWS access keys. Applying namespace.yaml later remains idempotent.
resource "kubernetes_namespace_v1" "meeting_insights" {
  metadata {
    name = "meeting-insights"
    labels = {
      "app.kubernetes.io/name" = "meeting-insights"
    }
  }

  depends_on = [module.eks]
}

resource "kubernetes_service_account_v1" "api" {
  metadata {
    name      = "meeting-insights-api"
    namespace = kubernetes_namespace_v1.meeting_insights.metadata[0].name
    annotations = {
      "eks.amazonaws.com/role-arn" = module.secrets_manager_irsa_role.iam_role_arn
    }
  }
}

resource "kubernetes_service_account_v1" "worker" {
  metadata {
    name      = "meeting-insights-worker"
    namespace = kubernetes_namespace_v1.meeting_insights.metadata[0].name
    annotations = {
      "eks.amazonaws.com/role-arn" = module.secrets_manager_irsa_role.iam_role_arn
    }
  }
}
