# RDS PostgreSQL Instance Module

# Generate random password for RDS master user
resource "random_password" "master_password" {
  length  = 32
  special = true
  # Exclude characters that might cause issues in connection strings
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# KMS key for RDS encryption
resource "aws_kms_key" "rds" {
  description             = "${var.project_name}-${var.environment}-rds-encryption-key"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-rds-kms"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

resource "aws_kms_alias" "rds" {
  name          = "alias/${var.project_name}-${var.environment}-rds"
  target_key_id = aws_kms_key.rds.key_id
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-db-subnet-group"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for RDS PostgreSQL instance"
  vpc_id      = var.vpc_id

  # Allow PostgreSQL traffic from EKS cluster
  ingress {
    description     = "PostgreSQL from EKS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.eks_security_group_id]
  }

  # Allow outbound traffic
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
      Name        = "${var.project_name}-${var.environment}-rds-sg"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

# DB Parameter Group for PostgreSQL 15
resource "aws_db_parameter_group" "postgres15" {
  name        = "${var.project_name}-${var.environment}-postgres15-params"
  family      = "postgres15"
  description = "Custom parameter group for PostgreSQL 15"

  # Performance tuning parameters
  parameter {
    name  = "shared_buffers"
    value = "{DBInstanceClassMemory/32768}" # 25% of RAM
  }

  parameter {
    name  = "work_mem"
    value = "16384" # 16MB
  }

  parameter {
    name  = "maintenance_work_mem"
    value = "524288" # 512MB
  }

  parameter {
    name  = "effective_cache_size"
    value = "{DBInstanceClassMemory/16384}" # 75% of RAM
  }

  parameter {
    name  = "random_page_cost"
    value = "1.1" # Optimized for SSD
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }

  # Logging configuration
  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log queries > 1 second
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_lock_waits"
    value = "1"
  }

  # Auto-vacuum tuning
  parameter {
    name  = "autovacuum_max_workers"
    value = "3"
  }

  parameter {
    name  = "autovacuum_naptime"
    value = "30" # 30 seconds
  }

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-postgres15-params"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-${var.environment}-postgres"

  # Engine configuration
  engine               = "postgres"
  engine_version       = "15.5"
  instance_class       = var.instance_class
  allocated_storage    = var.allocated_storage
  storage_type         = "gp3"
  storage_encrypted    = true
  kms_key_id           = aws_kms_key.rds.arn
  max_allocated_storage = var.allocated_storage * 2 # Auto-scaling up to 2x

  # Database configuration
  db_name  = var.db_name
  username = "agentguard_admin"
  password = random_password.master_password.result
  port     = 5432

  # High availability
  multi_az               = var.environment == "production" ? true : false
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Backup configuration
  backup_retention_period = var.environment == "production" ? 30 : 7
  backup_window           = "03:00-04:00" # UTC
  maintenance_window      = "sun:04:00-sun:05:00" # UTC
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.project_name}-${var.environment}-final-snapshot-${formatdate("YYYY-MM-DD-hhmm", timestamp())}"
  copy_tags_to_snapshot   = true

  # Deletion protection
  deletion_protection = var.environment == "production" ? true : false

  # Performance Insights
  performance_insights_enabled    = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn
  performance_insights_retention_period = var.environment == "production" ? 731 : 7 # 2 years for prod, 7 days for staging

  # IAM database authentication
  iam_database_authentication_enabled = true

  # Enhanced monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval             = 60 # Enhanced monitoring every 60 seconds
  monitoring_role_arn             = aws_iam_role.rds_monitoring.arn

  # Parameter and option groups
  parameter_group_name = aws_db_parameter_group.postgres15.name

  # Auto minor version upgrade
  auto_minor_version_upgrade = var.environment == "production" ? false : true

  # Apply changes immediately for non-production
  apply_immediately = var.environment != "production"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-postgres"
      Environment = var.environment
      ManagedBy   = "terraform"
      Engine      = "PostgreSQL 15"
    }
  )

  lifecycle {
    ignore_changes = [
      final_snapshot_identifier,
      password # Ignore password changes to prevent recreation
    ]
  }
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  name = "${var.project_name}-${var.environment}-rds-monitoring-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-rds-monitoring-role"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  role       = aws_iam_role.rds_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Alarms for RDS
resource "aws_cloudwatch_metric_alarm" "cpu_utilization" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "RDS CPU utilization is too high"
  alarm_actions       = []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "free_storage_space" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 10737418240 # 10 GB in bytes
  alarm_description   = "RDS free storage space is too low"
  alarm_actions       = []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "database_connections" {
  alarm_name          = "${var.project_name}-${var.environment}-rds-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 180 # 90% of max_connections (200)
  alarm_description   = "RDS database connections are too high"
  alarm_actions       = []

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }

  tags = merge(
    var.tags,
    {
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  )
}
