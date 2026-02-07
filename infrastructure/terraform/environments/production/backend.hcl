bucket         = "agentguard-terraform-state"
key            = "production/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "agentguard-terraform-locks"
encrypt        = true
