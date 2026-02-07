variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "agentguard"
}

variable "monthly_limit" {
  description = "Monthly budget limit in USD"
  type        = number
}

variable "alert_emails" {
  description = "Email addresses for budget alerts"
  type        = list(string)
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}
