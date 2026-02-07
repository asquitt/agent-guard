# AgentGuard Staging Environment
environment  = "staging"
aws_region   = "us-east-1"
project_name = "agentguard"
domain_name  = "staging.agentguard.app"

# VPC
vpc_cidr = "10.0.0.0/16"

# EKS — smaller for staging
eks_node_instance_types = ["t3.medium"]
eks_node_desired_size   = 2
eks_node_min_size       = 1
eks_node_max_size       = 3

# RDS — smaller for staging
rds_instance_class    = "db.t3.medium"
rds_allocated_storage = 50

# Redis — minimal for staging
redis_node_type       = "cache.t3.micro"
redis_num_cache_nodes = 1

# Budget — lower limit for staging
monthly_budget_limit = 300
budget_alert_emails  = ["alerts@agentguard.app"]

tags = {
  Team = "engineering"
}
