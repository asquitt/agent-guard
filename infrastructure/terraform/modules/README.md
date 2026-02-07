# Terraform Modules

## Available Modules

### 1. secrets
Manages AWS Secrets Manager secrets with KMS encryption.

**Resources:**
- KMS key for secret encryption (with key rotation)
- Database credentials secret (with optional 30-day rotation)
- Redis auth token secret
- Application secrets (secret_key, encryption_key, Stripe keys, Sentry DSN)

**Inputs:**
- Database: `db_endpoint`, `db_port`, `db_name`, `db_username`, `db_password`
- Redis: `redis_endpoint`, `redis_auth_token`
- App: `app_secret_key`, `app_encryption_key`, `stripe_secret_key`, `stripe_webhook_secret`, `sentry_dsn`
- Optional: `rotation_lambda_arn` for automatic secret rotation

**Outputs:**
- `db_secret_arn`, `redis_secret_arn`, `app_secret_arn`, `kms_key_arn`

---

### 2. alb
Application Load Balancer with WAF, access logging, and security groups.

**Resources:**
- ALB in public subnets
- HTTPS listener (port 443) with ACM certificate
- HTTP listener (port 80) → redirect to HTTPS
- Default target group (for EKS, target_type=ip, port 8000)
- Security group: allow 80/443 from internet, egress to VPC
- WAF v2 Web ACL with managed rule sets:
  - AWSManagedRulesCommonRuleSet
  - AWSManagedRulesKnownBadInputsRuleSet
  - AWSManagedRulesSQLiRuleSet
  - Rate limiting (2000 req/5min)
- S3 bucket for access logs (90-day lifecycle)
- Idle timeout 120s (for WebSocket connections)
- Drop invalid header fields enabled

**Inputs:**
- `vpc_id`, `public_subnet_ids`, `certificate_arn`
- `enable_deletion_protection` (default: true)

**Outputs:**
- `alb_arn`, `alb_dns_name`, `alb_zone_id`, `https_listener_arn`, `alb_security_group_id`, `target_group_arn`, `waf_web_acl_arn`

---

### 3. route53
Route 53 hosted zone with DNS records for ALB.

**Resources:**
- Hosted zone for domain
- A record alias for apex domain → ALB
- Optional: `api.domain.com` → ALB (default: enabled)
- Optional: `www.domain.com` → ALB (default: disabled)

**Inputs:**
- `domain_name`, `alb_dns_name`, `alb_zone_id`
- `create_api_subdomain` (default: true)
- `create_www_subdomain` (default: false)

**Outputs:**
- `zone_id`, `name_servers`, `domain_name`, `apex_record_fqdn`, `api_subdomain_fqdn`

---

### 4. acm
ACM certificate with DNS validation via Route 53.

**Resources:**
- ACM certificate for domain and wildcard (`*.domain.com`)
- DNS validation records in Route 53
- Waits for validation to complete

**Inputs:**
- `domain_name`, `zone_id` (Route 53 hosted zone)

**Outputs:**
- `certificate_arn`, `certificate_domain_name`, `certificate_status`, `subject_alternative_names`

---

## Usage Example

```hcl
# 1. Create Route 53 zone first
module "route53" {
  source = "./modules/route53"

  domain_name  = "agentguard.ai"
  alb_dns_name = module.alb.alb_dns_name
  alb_zone_id  = module.alb.alb_zone_id
  environment  = var.environment

  create_api_subdomain = true
  create_www_subdomain = false
}

# 2. Create ACM certificate (depends on Route 53 zone)
module "acm" {
  source = "./modules/acm"

  domain_name = "agentguard.ai"
  zone_id     = module.route53.zone_id
  environment = var.environment
}

# 3. Create ALB (depends on ACM certificate)
module "alb" {
  source = "./modules/alb"

  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  certificate_arn   = module.acm.certificate_arn
  environment       = var.environment
  project_name      = var.project_name
}

# 4. Create secrets
module "secrets" {
  source = "./modules/secrets"

  db_endpoint    = module.rds.endpoint
  db_port        = module.rds.port
  db_name        = "agentguard"
  db_username    = "agentguard_admin"
  db_password    = random_password.db_password.result

  redis_endpoint   = module.elasticache.endpoint
  redis_auth_token = random_password.redis_token.result

  app_secret_key       = random_password.app_secret_key.result
  app_encryption_key   = random_password.app_encryption_key.result
  stripe_secret_key    = var.stripe_secret_key
  stripe_webhook_secret = var.stripe_webhook_secret
  sentry_dsn           = var.sentry_dsn

  environment  = var.environment
  project_name = var.project_name
}
```

## Module Dependencies

```
route53 (standalone)
   ↓
acm (needs route53.zone_id)
   ↓
alb (needs acm.certificate_arn, vpc.vpc_id, vpc.public_subnet_ids)

secrets (needs rds.endpoint, elasticache.endpoint)
```

## Notes

- All modules follow consistent naming: `${var.project_name}-${var.environment}-resource`
- All modules support custom tags via `var.tags`
- ALB uses target_type="ip" for EKS compatibility
- Secrets module requires manual creation of rotation Lambda (ARN is optional)
- Route 53 name servers output should be configured with domain registrar
