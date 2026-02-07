# S3 Buckets Module Variables

variable "environment" {
  description = "Environment name (e.g., production, staging)"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "tags" {
  description = "Additional tags for resources"
  type        = map(string)
  default     = {}
}
