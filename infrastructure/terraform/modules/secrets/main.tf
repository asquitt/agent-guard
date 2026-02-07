# KMS key for encrypting secrets
resource "aws_kms_key" "secrets" {
  description             = "${var.project_name}-${var.environment}-secrets"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-secrets-kms"
      Environment = var.environment
    }
  )
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project_name}-${var.environment}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# Database credentials secret
resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.project_name}/${var.environment}/db-credentials"
  description             = "Database credentials for ${var.project_name} ${var.environment}"
  kms_key_id              = aws_kms_key.secrets.id
  recovery_window_in_days = 7

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-db-credentials"
      Environment = var.environment
    }
  )
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    host     = var.db_endpoint
    port     = var.db_port
    dbname   = var.db_name
    username = var.db_username
    password = var.db_password
  })
}

# Rotation configuration for DB credentials (30-day rotation)
resource "aws_secretsmanager_secret_rotation" "db_credentials" {
  secret_id           = aws_secretsmanager_secret.db_credentials.id
  rotation_lambda_arn = var.rotation_lambda_arn

  rotation_rules {
    automatically_after_days = 30
  }

  # Only enable rotation if Lambda ARN is provided
  count = var.rotation_lambda_arn != "" ? 1 : 0
}

# Redis auth token secret
resource "aws_secretsmanager_secret" "redis_auth" {
  name                    = "${var.project_name}/${var.environment}/redis-auth"
  description             = "Redis authentication token for ${var.project_name} ${var.environment}"
  kms_key_id              = aws_kms_key.secrets.id
  recovery_window_in_days = 7

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-redis-auth"
      Environment = var.environment
    }
  )
}

resource "aws_secretsmanager_secret_version" "redis_auth" {
  secret_id = aws_secretsmanager_secret.redis_auth.id
  secret_string = jsonencode({
    endpoint   = var.redis_endpoint
    auth_token = var.redis_auth_token
  })
}

# Application secrets (secret_key, encryption_key, third-party API keys)
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${var.project_name}/${var.environment}/app-secrets"
  description             = "Application secrets for ${var.project_name} ${var.environment}"
  kms_key_id              = aws_kms_key.secrets.id
  recovery_window_in_days = 7

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-app-secrets"
      Environment = var.environment
    }
  )
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    secret_key            = var.app_secret_key
    encryption_key        = var.app_encryption_key
    stripe_secret_key     = var.stripe_secret_key
    stripe_webhook_secret = var.stripe_webhook_secret
    sentry_dsn            = var.sentry_dsn
  })
}
