---
name: github-actions-workflows
description: Create and maintain GitHub Actions workflows in .github/workflows
---

# GitHub Actions Workflow Skill (.github/workflows)

Use this skill when creating or maintaining CI/CD automation via GitHub Actions workflows.

## Definition: "When to use this skill"

Create or modify a workflow if you need to:

- run automated tests, linting, or code quality checks
- build and publish Docker images or application artifacts
- deploy changes to staging/production environments
- validate pull requests before merging
- publish releases or create deployment artifacts

## Where workflows live

All workflows live in `.github/workflows/`.

- Each workflow is a single `.yml` file in this directory
- Workflows are triggered by GitHub events (push, pull_request, release, etc.)

## Naming conventions

Use descriptive, kebab-case names:

- `lint.yml` — linting and code quality
- `test.yml` — unit/integration tests
- `build.yml` — build and publish artifacts/images
- `deploy.yml` — deployment workflows
- `release.yml` — release automation

## Pinning action versions

**Always pin GitHub Actions to specific commit SHAs**, not floating tags (`v3`, `v4`).

### How to pin actions

1. Find the action in GitHub Marketplace or on GitHub
2. Use `git ls-remote --tags <repo-url> refs/tags/<version>` to get the commit SHA
3. Pin as: `uses: owner/action@<commit-sha> # <version>`

Example:
```yaml
- uses: docker/setup-buildx-action@8d2750c68a42422c14e847fe6c8ac0403b4cbd6f # v3.12.0
```

Benefits:
- Prevents unexpected behavior from action updates
- Makes dependencies explicit and auditable
- Improves security and reproducibility

### Updating pinned actions

When updating actions:

1. Check for the latest release tag: `git ls-remote --tags <repo-url> refs/tags`
2. Get the commit SHA for that tag
3. Update both the SHA and the version comment
4. Document the update in commit message

## Workflow structure best practices

### Permissions

Be explicit about what the workflow needs:

```yaml
permissions:
  contents: read           # read source code
  packages: write          # push to GHCR
  pull-requests: write     # comment on PRs
```

### Triggers (on:)

Define what events trigger the workflow:

```yaml
on:
  pull_request:            # on every PR
  push:
    branches:
      - main               # on push to main only
```

### Concurrency

Cancel in-progress runs when a new one is triggered:

```yaml
concurrency:
  group: build-${{ github.ref }}
  cancel-in-progress: true
```

### Jobs structure

- Use `runs-on: ubuntu-latest` for most jobs (or specific runners if needed)
- Use `needs: [job1, job2]` to sequence jobs
- Use `strategy.matrix` for parallel variations (e.g., multiple services, platforms)

### Common steps pattern

```yaml
steps:
  - uses: actions/checkout@v4  # Get code
  - name: Setup tools
    uses: setup-tool-action@sha  # Install/configure dependencies
  - name: Run command
    run: some command
  - name: Upload artifacts
    uses: actions/upload-artifact@v4
    if: always()  # Always upload even if previous steps failed
```

## Matrix builds

Use matrix strategy for building multiple variants:

```yaml
strategy:
  fail-fast: false          # Don't cancel if one fails
  matrix:
    service: [backend, frontend]
    include:                # Add custom env per matrix item
      - service: backend
        docker-file: backend/Dockerfile
```

Access matrix values in steps:
```yaml
- run: build
  env:
    SERVICE: ${{ matrix.service }}
```

## Docker image building

Best practices for `docker/build-push-action`:

1. **Use Buildx** for multi-platform builds: `docker/setup-buildx-action`
2. **Login** before pushing: `docker/login-action`
3. **Extract metadata** for tags/labels: `docker/metadata-action`
4. **Build and push**: `docker/build-push-action`
5. **Use caching** to speed up subsequent builds

Tag strategy:
```yaml
tags: |
  type=ref,event=branch           # Branch name
  type=semver,pattern={{version}} # Semantic version
  type=sha,prefix={{branch}}-     # Commit SHA
  type=raw,value=latest,enable={{is_default_branch}}  # Latest on main
```

Push only on main:
```yaml
push: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
```

## Testing and linting in workflows

Common patterns:

```yaml
- name: Run tests
  run: mise run test

- name: Run linter
  run: mise run lint

- name: Check formatting
  run: mise run format --check
```

Use `mise` commands (not direct tool invocations) for consistency with local development.

## Artifact and cache management

**Uploading artifacts:**
```yaml
- uses: actions/upload-artifact@v4
  if: always()
  with:
    name: test-results
    path: test-output/
    retention-days: 30
```

**Using caching:**
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

## Secrets and environment variables

**Never hardcode secrets:**
```yaml
- run: command
  env:
    API_KEY: ${{ secrets.API_KEY }}  # Use GitHub Secrets
```

**Set up .env files:**
```yaml
- name: Create .env
  run: |
    cp .env.example .env
    echo "API_KEY=${{ secrets.API_KEY }}" >> .env
```

## Common workflow patterns

### Lint and test on every PR and push to main
```yaml
on:
  pull_request:
  push:
    branches:
      - main
```

### Build on PR (no push), push only on main
```yaml
push: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}
```

### Run only on specific paths
```yaml
on:
  push:
    paths:
      - 'backend/**'
      - '.github/workflows/backend.yml'
```

## Repository-specific notes for Wingman

- **Monorepo structure**: Backend (FastAPI) and Frontend (Next.js) have separate build/test steps
- **Use `mise run`** for all tool invocations (install, test, lint, build)
- **Docker Buildx** is used for building multi-platform container images
- **GHCR publishing**: Images push to `ghcr.io/echohello-dev/wingman/{backend,frontend}`
- **Concurrency is important**: Cancel old builds when new ones are triggered

## "Definition of done" checklist

Before committing a workflow:

- [ ] Workflow file named descriptively (kebab-case)
- [ ] All external actions pinned to commit SHAs (not tags)
- [ ] Permissions explicitly defined
- [ ] Concurrency set up (if applicable)
- [ ] Tests/linting run before build jobs
- [ ] Build jobs use matrix strategy (if multiple targets)
- [ ] Artifacts uploaded with retention policy (if applicable)
- [ ] Secrets never hardcoded, using `${{ secrets.* }}` pattern
- [ ] Workflow tested locally or in a branch before merging
- [ ] README or docs updated if workflow is user-facing

## Useful commands

```bash
# Validate workflow syntax locally
act -l  # list workflows

# Run a workflow locally (requires act installed)
act push  # simulate a push event

# Check for workflow issues in PR
gh workflow view <workflow-name>
gh workflow list
```
