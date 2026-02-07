# S3 Buckets Module Outputs

output "warm_bucket_id" {
  description = "Warm storage bucket ID"
  value       = aws_s3_bucket.warm_storage.id
}

output "warm_bucket_arn" {
  description = "Warm storage bucket ARN"
  value       = aws_s3_bucket.warm_storage.arn
}

output "warm_bucket_name" {
  description = "Warm storage bucket name"
  value       = aws_s3_bucket.warm_storage.bucket
}

output "cold_bucket_id" {
  description = "Cold storage bucket ID"
  value       = aws_s3_bucket.cold_storage.id
}

output "cold_bucket_arn" {
  description = "Cold storage bucket ARN"
  value       = aws_s3_bucket.cold_storage.arn
}

output "cold_bucket_name" {
  description = "Cold storage bucket name"
  value       = aws_s3_bucket.cold_storage.bucket
}

output "assets_bucket_id" {
  description = "Assets bucket ID"
  value       = aws_s3_bucket.assets.id
}

output "assets_bucket_arn" {
  description = "Assets bucket ARN"
  value       = aws_s3_bucket.assets.arn
}

output "assets_bucket_name" {
  description = "Assets bucket name"
  value       = aws_s3_bucket.assets.bucket
}
