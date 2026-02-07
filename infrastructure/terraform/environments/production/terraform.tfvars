# AgentGuard Production Environment
environment  = "production"
aws_region   = "us-east-1"
project_name = "agentguard"
domain_name  = "agentguard.app"

# VPC
vpc_cidr = "10.1.0.0/16"

# EKS — production-grade
eks_node_instance_types = ["t3.large"]
eks_node_desired_size   = 3
eks_node_min_size       = 2
eks_node_max_size       = 8

# RDS — Multi-AZ production
rds_instance_class    = "db.r6g.large"
rds_allocated_storage = 100

# Redis — production with replica
redis_node_type       = "cache.r6g.large"
redis_num_cache_nodes = 2

# Budget
monthly_budget_limit = 1500
budget_alert_emails  = ["alerts@agentguard.app"]

tags = {
  Team = "engineering"
}
