bucket         = "agentguard-terraform-state"
key            = "staging/terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "agentguard-terraform-locks"
encrypt        = true
