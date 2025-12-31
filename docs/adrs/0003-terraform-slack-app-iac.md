---
date: 2025-12-31
status: Accepted
---

# 0003: Terraform for Slack App Infrastructure as Code

## Context

Initially, Slack app setup for Wingman required manual configuration through the Slack web interface:
- Creating the app from scratch
- Configuring scopes and permissions
- Setting up event subscriptions
- Managing tokens and credentials
- Updating configuration across environments (dev, staging, prod)

This manual process was:
- **Error-prone**: Easy to miss required scopes or misconfigure event subscriptions
- **Non-reproducible**: Different team members might create apps with slightly different configurations
- **Hard to maintain**: Difficult to audit what settings were applied and why
- **Token management burden**: Manual token rotation and environment synchronization
- **Not scalable**: Creating multiple Slack apps for different environments required repeating manual steps

## Decision

We adopted **Terraform with the `terraform-provider-slackapp`** to manage Slack app infrastructure as code.

This means:
- All Slack app configuration (scopes, events, display settings) is defined in `terraform/main.tf`, `variables.tf`, and `outputs.tf`
- The provider uses Slack's app manifest API to create apps programmatically
- Terraform Cloud is used as the remote backend for state management and secrets
- Token rotation is automated via `mise run tf-sync-vars` script using the Slack `tooling.tokens.rotate` API
- Environment variables (managed via `.env`) are used for sensitive credentials, with automatic loading by mise

## Alternatives Considered

1. **Manual web UI setup**
   - ✗ Error-prone and non-reproducible
   - ✗ No audit trail of changes
   - ✗ Token rotation requires manual intervention

2. **Slack Bolt scaffolding + manual JSON config**
   - ✗ Requires custom Python/Node.js code to parse and apply config
   - ✗ No state tracking or drift detection
   - ✗ Still requires manual token management

3. **CDK for Slack (AWS CDK-like approach)**
   - ✗ Slack CDK library is immature and limited in scope
   - ✗ Requires TypeScript/JavaScript infrastructure expertise
   - ✗ Less portable across organizations

4. **Pulumi**
   - ✗ Larger learning curve (requires Pulumi concepts)
   - ✗ Fewer examples and community resources
   - ✗ Terraform already widely adopted in DevOps

## Consequences

### Positive

- **Version-controlled infrastructure**: All app configuration lives in git
- **Reproducible deployments**: Same Terraform code creates identical apps across environments
- **Drift detection**: `mise run tf-plan` shows if actual app config differs from desired state
- **Automated token rotation**: `mise run tf-sync-vars` handles 12-hour token expiry automatically
- **Encrypted secrets management**: Terraform Cloud stores and encrypts sensitive variables
- **Team scalability**: New team members run `mise run tf-apply` instead of manually configuring
- **Audit trail**: Git history shows all changes to app configuration

### Negative

- **Added operational complexity**: Team must learn Terraform basics
- **Terraform Cloud dependency**: Requires external SaaS for state management (though local state is an option)
- **Provider maturity**: `terraform-provider-slackapp` is community-maintained, not official Slack
- **Token management still manual initially**: First token setup still requires manual steps via Slack API
- **Vendor lock-in (partial)**: Switching providers later would require rewriting configuration

### Mitigation

- Comprehensive documentation in `docs/terraform.md` with quick-start guide
- `mise` tasks automate common Terraform operations (no CLI knowledge required)
- `tf-sync-vars` script abstracts token management complexity
- Local `.tfstate` option available if Terraform Cloud not desired
- Provider code is open-source; community can maintain if needed

## References

- **Implementation**: [terraform/](../../terraform/) directory with `main.tf`, `variables.tf`, `outputs.tf`, `backend.tf`
- **Scripts**: [scripts/sync_tf_vars.py](../../scripts/sync_tf_vars.py) - automated token rotation
- **Documentation**: [docs/terraform.md](../terraform.md) - complete usage guide
- **Provider**: [terraform-provider-slackapp](https://github.com/yumemi-inc/terraform-provider-slackapp) (v0.2.7)
- **Related ADR**: [0001-technology-stack-and-rag-architecture.md](0001-technology-stack-and-rag-architecture.md)
