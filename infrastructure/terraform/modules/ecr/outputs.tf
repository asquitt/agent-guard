# ECR Repositories Module Outputs

output "api_repo_url" {
  description = "API repository URL"
  value       = aws_ecr_repository.api.repository_url
}

output "api_repo_arn" {
  description = "API repository ARN"
  value       = aws_ecr_repository.api.arn
}

output "api_repo_name" {
  description = "API repository name"
  value       = aws_ecr_repository.api.name
}

output "worker_repo_url" {
  description = "Worker repository URL"
  value       = aws_ecr_repository.worker.repository_url
}

output "worker_repo_arn" {
  description = "Worker repository ARN"
  value       = aws_ecr_repository.worker.arn
}

output "worker_repo_name" {
  description = "Worker repository name"
  value       = aws_ecr_repository.worker.name
}

output "frontend_repo_url" {
  description = "Frontend repository URL"
  value       = aws_ecr_repository.frontend.repository_url
}

output "frontend_repo_arn" {
  description = "Frontend repository ARN"
  value       = aws_ecr_repository.frontend.arn
}

output "frontend_repo_name" {
  description = "Frontend repository name"
  value       = aws_ecr_repository.frontend.name
}
