# S3 Buckets Module

# Warm Storage Bucket (S3 Standard -> Glacier transition)
resource "aws_s3_bucket" "warm_storage" {
  bucket = "${var.project_name}-${var.environment}-warm-storage"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-warm-storage"
      Environment = var.environment
      Purpose     = "Archived proxy data (30 days - 1 year)"
    }
  )
}

resource "aws_s3_bucket_versioning" "warm_storage" {
  bucket = aws_s3_bucket.warm_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "warm_storage" {
  bucket = aws_s3_bucket.warm_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "warm_storage" {
  bucket = aws_s3_bucket.warm_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "warm_storage" {
  bucket = aws_s3_bucket.warm_storage.id

  rule {
    id     = "transition-to-glacier"
    status = "Enabled"

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 730
    }
  }
}

# Cold Storage Bucket (Glacier for long-term retention)
resource "aws_s3_bucket" "cold_storage" {
  bucket = "${var.project_name}-${var.environment}-cold-storage"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-cold-storage"
      Environment = var.environment
      Purpose     = "Long-term regulatory retention (1-7 years)"
    }
  )
}

resource "aws_s3_bucket_versioning" "cold_storage" {
  bucket = aws_s3_bucket.cold_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cold_storage" {
  bucket = aws_s3_bucket.cold_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "cold_storage" {
  bucket = aws_s3_bucket.cold_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "cold_storage" {
  bucket = aws_s3_bucket.cold_storage.id

  rule {
    id     = "glacier-and-expiration"
    status = "Enabled"

    # Immediately store in Glacier
    transition {
      days          = 0
      storage_class = "GLACIER"
    }

    # Expire after 7 years (2555 days)
    expiration {
      days = 2555
    }

    noncurrent_version_expiration {
      noncurrent_days = 2555
    }
  }
}

# Static Assets Bucket (for frontend/CDN)
resource "aws_s3_bucket" "assets" {
  bucket = "${var.project_name}-${var.environment}-assets"

  tags = merge(
    var.tags,
    {
      Name        = "${var.project_name}-${var.environment}-assets"
      Environment = var.environment
      Purpose     = "Static frontend assets"
    }
  )
}

resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# Optional: CORS configuration for assets bucket
resource "aws_s3_bucket_cors_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}
