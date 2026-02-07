# --------------------------------------------------------------------------
# Networking
# --------------------------------------------------------------------------

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

# --------------------------------------------------------------------------
# EKS
# --------------------------------------------------------------------------

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "EKS API endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_kubeconfig_command" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.aws_region}"
}

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

output "rds_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = module.rds.db_endpoint
}

output "rds_connection_string" {
  description = "Full PostgreSQL connection string"
  value       = module.rds.connection_string
  sensitive   = true
}

# --------------------------------------------------------------------------
# Redis
# --------------------------------------------------------------------------

output "redis_endpoint" {
  description = "Redis primary endpoint"
  value       = module.elasticache.redis_endpoint
}

# --------------------------------------------------------------------------
# ECR
# --------------------------------------------------------------------------

output "ecr_api_repo_url" {
  description = "ECR repository URL for API image"
  value       = module.ecr.api_repo_url
}

output "ecr_worker_repo_url" {
  description = "ECR repository URL for Worker image"
  value       = module.ecr.worker_repo_url
}

output "ecr_frontend_repo_url" {
  description = "ECR repository URL for Frontend image"
  value       = module.ecr.frontend_repo_url
}

# --------------------------------------------------------------------------
# Load Balancer
# --------------------------------------------------------------------------

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.alb_dns_name
}

# --------------------------------------------------------------------------
# DNS
# --------------------------------------------------------------------------

output "name_servers" {
  description = "Name servers for the hosted zone (set at registrar)"
  value       = module.route53.name_servers
}

output "domain_name" {
  description = "Domain name"
  value       = var.domain_name
}

# --------------------------------------------------------------------------
# Secrets
# --------------------------------------------------------------------------

output "db_secret_arn" {
  description = "ARN of database credentials secret"
  value       = module.secrets.db_secret_arn
}

output "app_secret_arn" {
  description = "ARN of application secrets"
  value       = module.secrets.app_secret_arn
}
