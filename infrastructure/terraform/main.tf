# AgentGuard Infrastructure — Root Module
# Composes all child modules into a complete AWS deployment.

locals {
  cluster_name = "${var.project_name}-${var.environment}"
  common_tags = merge(var.tags, {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  })
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

# --------------------------------------------------------------------------
# Networking
# --------------------------------------------------------------------------

module "vpc" {
  source = "./modules/vpc"

  environment  = var.environment
  project_name = var.project_name
  cluster_name = local.cluster_name
  vpc_cidr     = var.vpc_cidr
  tags         = local.common_tags
}

# --------------------------------------------------------------------------
# DNS & TLS
# --------------------------------------------------------------------------

module "route53" {
  source = "./modules/route53"

  domain_name  = var.domain_name
  alb_dns_name = module.alb.alb_dns_name
  alb_zone_id  = module.alb.alb_zone_id
  environment  = var.environment
  tags         = local.common_tags
}

module "acm" {
  source = "./modules/acm"

  domain_name = var.domain_name
  zone_id     = module.route53.zone_id
  tags        = local.common_tags
}

# --------------------------------------------------------------------------
# Compute — EKS
# --------------------------------------------------------------------------

module "eks" {
  source = "./modules/eks"

  cluster_name        = local.cluster_name
  environment         = var.environment
  project_name        = var.project_name
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  node_instance_types = var.eks_node_instance_types
  node_desired_size   = var.eks_node_desired_size
  node_min_size       = var.eks_node_min_size
  node_max_size       = var.eks_node_max_size
  tags                = local.common_tags
}

# --------------------------------------------------------------------------
# Data — RDS PostgreSQL
# --------------------------------------------------------------------------

module "rds" {
  source = "./modules/rds"

  environment           = var.environment
  project_name          = var.project_name
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  eks_security_group_id = module.eks.cluster_security_group_id
  instance_class        = var.rds_instance_class
  allocated_storage     = var.rds_allocated_storage
  tags                  = local.common_tags
}

# --------------------------------------------------------------------------
# Data — ElastiCache Redis
# --------------------------------------------------------------------------

module "elasticache" {
  source = "./modules/elasticache"

  environment           = var.environment
  project_name          = var.project_name
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  eks_security_group_id = module.eks.cluster_security_group_id
  node_type             = var.redis_node_type
  num_cache_nodes       = var.redis_num_cache_nodes
  tags                  = local.common_tags
}

# --------------------------------------------------------------------------
# Storage — S3 & ECR
# --------------------------------------------------------------------------

module "s3" {
  source = "./modules/s3"

  environment  = var.environment
  project_name = var.project_name
  tags         = local.common_tags
}

module "ecr" {
  source = "./modules/ecr"

  environment  = var.environment
  project_name = var.project_name
  tags         = local.common_tags
}

# --------------------------------------------------------------------------
# Load Balancing — ALB + WAF
# --------------------------------------------------------------------------

module "alb" {
  source = "./modules/alb"

  environment       = var.environment
  project_name      = var.project_name
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  certificate_arn   = module.acm.certificate_arn
  tags              = local.common_tags
}

# --------------------------------------------------------------------------
# Secrets Management
# --------------------------------------------------------------------------

module "secrets" {
  source = "./modules/secrets"

  environment      = var.environment
  project_name     = var.project_name
  db_endpoint      = module.rds.db_endpoint
  db_port          = module.rds.db_port
  db_name          = module.rds.db_name
  db_username      = module.rds.db_username
  db_password      = module.rds.db_password
  redis_endpoint   = module.elasticache.redis_endpoint
  redis_auth_token = module.elasticache.redis_auth_token
  tags             = local.common_tags
}

# --------------------------------------------------------------------------
# Cost Management
# --------------------------------------------------------------------------

module "budgets" {
  source = "./modules/budgets"

  environment   = var.environment
  project_name  = var.project_name
  monthly_limit = var.monthly_budget_limit
  alert_emails  = var.budget_alert_emails
  tags          = local.common_tags
}
