# Terraform Module Management Skill

## Purpose
Guide for creating, organizing, and managing Terraform modules with environment variable configuration and mise integration.

## Module Structure

### Standard Layout
```
terraform/
├── backend.tf          # Backend configuration (local/cloud)
├── main.tf            # Provider and resource definitions
├── variables.tf       # Input variable declarations
├── outputs.tf         # Output values
├── .gitignore         # Ignore state files, secrets
├── backend.tfbackend.example  # Backend config template (optional)
└── terraform.tfvars.example   # Variable values template (optional)
```

## Configuration Patterns

### 1. Environment Variables Over Terraform Variables

**Prefer environment variables for sensitive data:**

```hcl
# main.tf - Provider reads from env vars directly
provider "example" {
  # Reads EXAMPLE_API_KEY from environment
  # No variable declaration needed
}
```

**Use Terraform variables only for:**
- Non-sensitive configuration (names, regions, sizes)
- Values that change between environments
- Values that need validation or defaults

```hcl
# variables.tf
variable "app_name" {
  description = "Name of the application"
  type        = string
  default     = "myapp"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod"
  }
}
```

### 2. Backend Configuration

**Local State (Development):**
```hcl
# backend.tf
terraform {
  # No backend block = local state in terraform.tfstate
}
```

**Terraform Cloud (Team/Production):**
```hcl
# backend.tf
terraform {
  cloud {
    organization = "your-org"
    
    workspaces {
      name = "your-workspace"
    }
  }
}
```

**S3 Backend (AWS):**
```hcl
# backend.tf
terraform {
  backend "s3" {
    # Configure via backend.tfbackend file or -backend-config flags
  }
}

# backend.tfbackend (gitignored)
bucket         = "my-terraform-state"
key            = "project/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "terraform-lock"
```

### 3. Provider Configuration

**Environment variables are preferred:**
```hcl
provider "aws" {
  # Reads AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
  # from environment automatically
}

provider "custom" {
  # If provider doesn't auto-detect, explicitly reference
  # but still use env vars via mise
}
```

## Mise Integration

### Environment Variable Loading

**Configure mise.toml:**
```toml
[env]
_.file = ".env"  # Auto-load .env for all tasks

[tools]
terraform = "1.12"
```

### Standard Terraform Tasks

```toml
[tasks.tf-init]
description = "Initialize Terraform"
run = "cd terraform && terraform init"

[tasks.tf-plan]
description = "Plan Terraform changes"
run = "cd terraform && terraform plan"

[tasks.tf-apply]
description = "Apply Terraform changes"
run = "cd terraform && terraform apply"

[tasks.tf-destroy]
description = "Destroy Terraform resources"
run = "cd terraform && terraform destroy"

[tasks.tf-output]
description = "Show Terraform outputs"
run = "cd terraform && terraform output"

[tasks.tf-fmt]
description = "Format Terraform files"
run = "cd terraform && terraform fmt -recursive"

[tasks.tf-validate]
description = "Validate Terraform configuration"
run = "cd terraform && terraform validate"
```

### Advanced Tasks

```toml
[tasks.tf-state-list]
description = "List resources in state"
run = "cd terraform && terraform state list"

[tasks.tf-import]
description = "Import existing resource into state"
run = """
cd terraform
if [ -z "$RESOURCE_ID" ]; then
  echo "Usage: RESOURCE_ID=<id> RESOURCE_ADDRESS=<address> mise run tf-import"
  exit 1
fi
terraform import "$RESOURCE_ADDRESS" "$RESOURCE_ID"
"""

[tasks.tf-taint]
description = "Mark resource for recreation"
run = """
cd terraform
if [ -z "$RESOURCE_ADDRESS" ]; then
  echo "Usage: RESOURCE_ADDRESS=<address> mise run tf-taint"
  exit 1
fi
terraform taint "$RESOURCE_ADDRESS"
"""
```

## Security Best Practices

### .gitignore Requirements
```gitignore
# Terraform
.terraform/
.terraform.lock.hcl  # Lock file can be committed for consistency
*.tfstate
*.tfstate.*
*.tfvars           # Never commit variable values
*.tfvars.json
*.tfbackend        # Never commit backend config with secrets
crash.log
override.tf
override.tf.json
*_override.tf
*_override.tf.json
```

### Environment Variables
```bash
# .env (gitignored)
# Provider credentials
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
TF_TOKEN_app_terraform_io=xxx

# Custom provider tokens
CUSTOM_API_KEY=xxx
CUSTOM_API_SECRET=xxx

# Terraform Cloud (if using)
TF_CLOUD_ORGANIZATION=myorg
TF_WORKSPACE=myworkspace
```

### .env.example Template
```bash
# .env.example (committed to git)
# Copy to .env and fill in your values

# Provider Credentials
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1

# Terraform Cloud
TF_CLOUD_ORGANIZATION=
TF_WORKSPACE=
TF_TOKEN_app_terraform_io=
```

## Module Organization

### Single Module
```
terraform/
├── main.tf
├── variables.tf
├── outputs.tf
└── backend.tf
```

### Multiple Modules
```
terraform/
├── modules/
│   ├── network/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── compute/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── database/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── main.tf          # Calls modules
├── variables.tf
├── outputs.tf
└── backend.tf
```

### Using Modules
```hcl
# main.tf
module "network" {
  source = "./modules/network"
  
  vpc_cidr = var.vpc_cidr
  environment = var.environment
}

module "compute" {
  source = "./modules/compute"
  
  vpc_id = module.network.vpc_id
  subnet_ids = module.network.private_subnet_ids
}
```

## Provider Discovery

### Inspect Provider Schema
```bash
# Get provider schema
terraform providers schema -json | jq

# Extract specific provider attributes
terraform providers schema -json | \
  python3 -c "import json, sys; \
  data=json.load(sys.stdin); \
  print(json.dumps(data['provider_schemas']['registry.terraform.io/owner/provider'], indent=2))"
```

## Common Workflows

### Initial Setup
```bash
# 1. Create module structure
mkdir -p terraform
cd terraform

# 2. Initialize configuration files
touch main.tf variables.tf outputs.tf backend.tf

# 3. Add to .env
echo "TF_VAR_environment=dev" >> ../.env

# 4. Initialize
mise run tf-init
```

### Development Workflow
```bash
# 1. Make changes to .tf files
vim terraform/main.tf

# 2. Format code
mise run tf-fmt

# 3. Validate configuration
mise run tf-validate

# 4. Preview changes
mise run tf-plan

# 5. Apply if approved
mise run tf-apply
```

### Migrating Backends
```bash
# 1. Update backend.tf with new backend
vim terraform/backend.tf

# 2. Reinitialize (will prompt to migrate)
mise run tf-init

# 3. Confirm migration when prompted
```

## Troubleshooting

### State Lock Issues
```bash
# Force unlock (use with caution)
cd terraform && terraform force-unlock <lock-id>
```

### Provider Version Conflicts
```bash
# Upgrade providers to latest allowed versions
cd terraform && terraform init -upgrade

# Lock to specific version
# In main.tf:
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # Lock to major version
    }
  }
}
```

### Environment Variable Not Loaded
```bash
# Verify mise loads .env
mise run tf-plan --verbose

# Manually export if needed (testing)
export $(cat .env | xargs) && cd terraform && terraform plan
```

## Output Management

### Structured Outputs
```hcl
# outputs.tf
output "database_connection" {
  description = "Database connection details"
  value = {
    host     = aws_db_instance.main.endpoint
    port     = aws_db_instance.main.port
    database = aws_db_instance.main.db_name
  }
  sensitive = true
}

output "api_endpoints" {
  description = "API endpoint URLs"
  value = {
    public  = aws_api_gateway_deployment.main.invoke_url
    private = aws_vpc_endpoint.api.dns_entry[0].dns_name
  }
}
```

### Extract Outputs to .env
```toml
# mise.toml
[tasks.tf-export-outputs]
description = "Export Terraform outputs to .env"
run = """
cd terraform
echo "# Auto-generated from Terraform outputs" >> ../.env.terraform
terraform output -json | \
  python3 -c "import sys, json; \
  data=json.load(sys.stdin); \
  [print(f'{k.upper()}={v[\"value\"]}') for k,v in data.items() if not v.get('sensitive')]" \
  >> ../.env.terraform
echo "✅ Outputs exported to .env.terraform"
"""
```

## Anti-Patterns to Avoid

❌ **Don't store secrets in variables:**
```hcl
# Bad
variable "api_key" {
  type = string
}
```

✅ **Use environment variables:**
```hcl
# Good - provider reads from env
provider "example" {
  # Reads EXAMPLE_API_KEY automatically
}
```

❌ **Don't commit .tfvars files with secrets**

❌ **Don't use string interpolation for sensitive values**

❌ **Don't skip state locking**

❌ **Don't manually edit state files**

## References

- [Terraform Best Practices](https://www.terraform-best-practices.com/)
- [Terraform CLI Documentation](https://developer.hashicorp.com/terraform/cli)
- [mise Environment Variables](https://mise.jdx.dev/configuration.html#env)
