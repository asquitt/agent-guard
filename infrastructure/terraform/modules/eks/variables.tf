variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string

  validation {
    condition     = length(var.cluster_name) <= 100 && can(regex("^[0-9A-Za-z][A-Za-z0-9\\-_]*$", var.cluster_name))
    error_message = "Cluster name must be alphanumeric with hyphens/underscores, max 100 characters."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "project_name" {
  description = "Project name for resource tagging"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where EKS cluster will be deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for EKS cluster and nodes"
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_ids) >= 2
    error_message = "At least 2 private subnets are required for HA."
  }
}

variable "node_instance_types" {
  description = "List of instance types for EKS node group"
  type        = list(string)
  default     = ["t3.medium"]

  validation {
    condition     = length(var.node_instance_types) > 0
    error_message = "At least one instance type must be specified."
  }
}

variable "node_desired_size" {
  description = "Desired number of nodes in the node group"
  type        = number
  default     = 2

  validation {
    condition     = var.node_desired_size >= 1
    error_message = "Desired size must be at least 1."
  }
}

variable "node_min_size" {
  description = "Minimum number of nodes in the node group"
  type        = number
  default     = 1

  validation {
    condition     = var.node_min_size >= 1
    error_message = "Minimum size must be at least 1."
  }
}

variable "node_max_size" {
  description = "Maximum number of nodes in the node group"
  type        = number
  default     = 4

  validation {
    condition     = var.node_max_size >= 1
    error_message = "Maximum size must be at least 1."
  }
}

variable "tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
