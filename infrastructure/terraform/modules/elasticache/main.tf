# ElastiCache Redis Module

# Random password for Redis auth token
resource "random_password" "redis_auth_token" {
  length  = 32
  special = false
}

# Subnet group for ElastiCache
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.project_name}-${var.environment}-redis-subnet"
  subnet_ids = var.private_subnet_ids
  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-redis-subnet"
      Environment = var.environment
    }
  )
}

# Security group for ElastiCache Redis
resource "aws_security_group" "redis" {
  name_prefix = "${var.project_name}-${var.environment}-redis-"
  description = "Security group for ElastiCache Redis cluster"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from EKS cluster"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [var.eks_security_group_id]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-redis-sg"
      Environment = var.environment
    }
  )

  lifecycle {
    create_before_destroy = true
  }
}

# Parameter group for Redis
resource "aws_elasticache_parameter_group" "redis" {
  name   = "${var.project_name}-${var.environment}-redis-params"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-redis-params"
      Environment = var.environment
    }
  )
}

# ElastiCache Redis Replication Group
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${var.project_name}-${var.environment}-redis"
  description          = "Redis cluster for ${var.project_name} ${var.environment}"

  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_nodes
  parameter_group_name = aws_elasticache_parameter_group.redis.name
  port                 = 6379

  subnet_group_name  = aws_elasticache_subnet_group.redis.name
  security_group_ids = [aws_security_group.redis.id]

  # Auth token for encryption in transit
  auth_token                  = random_password.redis_auth_token.result
  transit_encryption_enabled  = true
  at_rest_encryption_enabled  = true

  # Automatic failover (only for multi-node clusters)
  automatic_failover_enabled = var.num_cache_nodes > 1 ? true : false
  multi_az_enabled           = var.num_cache_nodes > 1 ? true : false

  # Snapshot configuration
  snapshot_retention_limit = var.environment == "production" ? 7 : 1
  snapshot_window          = "03:00-05:00"
  maintenance_window       = "sun:05:00-sun:07:00"

  # Auto minor version upgrades
  auto_minor_version_upgrade = true

  # Notification topic (optional, can be added later)
  # notification_topic_arn = var.sns_topic_arn

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-redis"
      Environment = var.environment
    }
  )
}
