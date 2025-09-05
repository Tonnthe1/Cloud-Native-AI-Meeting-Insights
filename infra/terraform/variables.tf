variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "cluster_name_override" {
  description = "Override the auto-generated cluster name (leave empty for auto-generation)"
  type        = string
  default     = ""
}

# Generate a random suffix to make cluster names unique
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Local values for computed names
locals {
  cluster_name = var.cluster_name_override != "" ? var.cluster_name_override : "meeting-insights-${random_string.suffix.result}"
}

variable "cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.28"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "node_instance_types" {
  description = "Instance types for EKS worker nodes"
  type        = list(string)
  default     = ["t3.medium"]  # Cost-effective for testing
}

variable "node_desired_capacity" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

variable "node_max_capacity" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 4
}

variable "node_min_capacity" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"  # Free tier eligible
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20  # Minimum for gp2
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "meeting_insights"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "meetinguser"
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"  # Cost-effective for testing
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default = {
    Owner = "DevOps"
    Purpose = "Meeting Insights Demo"
  }
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access EKS cluster API"
  type        = list(string)
  default     = []  # Leave empty to allow all (0.0.0.0/0), or specify your IPs
}