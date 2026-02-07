# RDS Module Outputs

output "db_instance_id" {
  description = "The RDS instance ID"
  value       = aws_db_instance.main.id
}

output "db_instance_arn" {
  description = "The ARN of the RDS instance"
  value       = aws_db_instance.main.arn
}

output "db_endpoint" {
  description = "The connection endpoint for the RDS instance"
  value       = aws_db_instance.main.endpoint
}

output "db_address" {
  description = "The hostname of the RDS instance"
  value       = aws_db_instance.main.address
}

output "db_port" {
  description = "The port the database is listening on"
  value       = aws_db_instance.main.port
}

output "db_name" {
  description = "The name of the default database"
  value       = aws_db_instance.main.db_name
}

output "db_username" {
  description = "The master username for the database"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_password" {
  description = "The master password for the database"
  value       = random_password.master_password.result
  sensitive   = true
}

output "db_security_group_id" {
  description = "The security group ID attached to the RDS instance"
  value       = aws_security_group.rds.id
}

output "db_subnet_group_name" {
  description = "The DB subnet group name"
  value       = aws_db_subnet_group.main.name
}

output "kms_key_id" {
  description = "The KMS key ID used for RDS encryption"
  value       = aws_kms_key.rds.id
}

output "kms_key_arn" {
  description = "The KMS key ARN used for RDS encryption"
  value       = aws_kms_key.rds.arn
}

output "monitoring_role_arn" {
  description = "The ARN of the IAM role used for enhanced monitoring"
  value       = aws_iam_role.rds_monitoring.arn
}

output "connection_string" {
  description = "PostgreSQL connection string (without password)"
  value       = "postgresql://${aws_db_instance.main.username}@${aws_db_instance.main.endpoint}/${aws_db_instance.main.db_name}"
  sensitive   = true
}
