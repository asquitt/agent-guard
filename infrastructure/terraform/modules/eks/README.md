# EKS Terraform Module

Production-ready Amazon EKS cluster module with security best practices.

## Features

- **EKS Cluster**: Kubernetes 1.29 with configurable node groups
- **Security**: KMS encryption, private subnets, least-privilege IAM roles
- **IRSA**: OIDC provider for IAM Roles for Service Accounts
- **Addons**: vpc-cni, coredns, kube-proxy, ebs-csi-driver
- **Logging**: CloudWatch logs for audit, api, and controllerManager
- **High Availability**: Multi-AZ deployment in private subnets

## Usage

```hcl
module "eks" {
  source = "./modules/eks"

  cluster_name       = "agentguard-prod"
  environment        = "prod"
  project_name       = "agentguard"
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  node_instance_types = ["t3.medium", "t3.large"]
  node_desired_size   = 3
  node_min_size       = 2
  node_max_size       = 6

  tags = {
    Environment = "prod"
    Project     = "agentguard"
    ManagedBy   = "terraform"
  }
}
```

## Security Features

### Encryption
- Secrets encrypted at rest using KMS
- KMS key rotation enabled
- Dedicated KMS key per cluster

### Network Security
- Nodes in private subnets only
- Security groups with least-privilege rules
- Public + private API endpoint access (configurable)

### IAM
- Separate IAM roles for cluster and nodes
- OIDC provider for IRSA (service account authentication)
- Minimal required permissions

### Logging
- CloudWatch logs for:
  - API server
  - Audit logs
  - Controller Manager
- 7-day retention

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | ~> 5.0 |
| tls | ~> 4.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| cluster_name | Name of the EKS cluster | `string` | n/a | yes |
| environment | Environment name (dev, staging, prod) | `string` | n/a | yes |
| project_name | Project name for resource tagging | `string` | n/a | yes |
| vpc_id | VPC ID where EKS cluster will be deployed | `string` | n/a | yes |
| private_subnet_ids | List of private subnet IDs (min 2 for HA) | `list(string)` | n/a | yes |
| node_instance_types | Instance types for node group | `list(string)` | `["t3.medium"]` | no |
| node_desired_size | Desired number of nodes | `number` | `2` | no |
| node_min_size | Minimum number of nodes | `number` | `1` | no |
| node_max_size | Maximum number of nodes | `number` | `4` | no |
| tags | Additional tags for all resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| cluster_name | Name of the EKS cluster |
| cluster_endpoint | Endpoint for EKS control plane |
| cluster_ca_certificate | Base64 encoded certificate data (sensitive) |
| cluster_security_group_id | Security group ID for cluster |
| node_security_group_id | Security group ID for nodes |
| oidc_provider_arn | ARN of OIDC provider for IRSA |
| oidc_provider_url | URL of OIDC provider for IRSA |
| node_group_name | Name of the EKS node group |
| cluster_id | EKS cluster ID |
| cluster_arn | EKS cluster ARN |
| cluster_version | Kubernetes version |
| cluster_iam_role_arn | IAM role ARN for cluster |
| node_iam_role_arn | IAM role ARN for nodes |
| ebs_csi_driver_role_arn | IAM role ARN for EBS CSI driver |
| kms_key_id | KMS key ID for encryption |
| kms_key_arn | KMS key ARN for encryption |
| cloudwatch_log_group_name | CloudWatch log group name |

## Post-Deployment

### Configure kubectl

```bash
aws eks update-kubeconfig --region us-east-1 --name agentguard-prod
```

### Verify cluster

```bash
kubectl get nodes
kubectl get pods -A
```

### Using IRSA

Create service account with IAM role annotation:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-service-account
  namespace: default
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::ACCOUNT:role/my-role
```

## Addons Versions

| Addon | Version |
|-------|---------|
| vpc-cni | v1.16.0-eksbuild.1 |
| coredns | v1.11.1-eksbuild.4 |
| kube-proxy | v1.29.0-eksbuild.1 |
| aws-ebs-csi-driver | v1.27.0-eksbuild.1 |

## Notes

- Node group uses managed scaling (desired_size changes are ignored after creation)
- All nodes have SSM Session Manager access for troubleshooting
- EBS CSI driver required for persistent volumes
- Cluster logs retained for 7 days (adjust in main.tf if needed)
