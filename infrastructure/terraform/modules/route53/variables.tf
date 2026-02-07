variable "domain_name" {
  description = "Domain name for the hosted zone"
  type        = string
}

variable "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  type        = string
}

variable "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "create_api_subdomain" {
  description = "Create api subdomain pointing to ALB"
  type        = bool
  default     = true
}

variable "create_www_subdomain" {
  description = "Create www subdomain pointing to ALB"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
