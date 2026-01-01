---
name: github-actions-troubleshooting
description: Troubleshoot and fix GitHub Actions workflow failures, especially CI builds after merge
---

# GitHub Actions Troubleshooting Skill

Use this skill when GitHub Actions workflows are failing and need to be debugged and fixed.

## When to use this skill

Apply this skill when:

- CI/CD workflow runs are failing after push or merge
- Docker builds or image publishes are failing in Actions
- Tests or linting fail only in CI (but work locally)
- Workflow logs show errors that need investigation
- Need to iterate on fixes until the build passes

## Troubleshooting workflow

### 1. Check the workflow YAML file first

**Always start by examining the workflow configuration:**

```bash
# Find the workflow file
ls .github/workflows/

# Read the workflow to understand what it does
cat .github/workflows/<workflow-name>.yml
```

**Key things to check:**
- Which commands are being run in each step?
- Are there environment variables or secrets being used?
- What's the context path (e.g., `./backend`, `./frontend`)?
- What triggers the workflow (push, pull_request, etc.)?

### 2. Test commands locally first

**Before diving into CI logs, reproduce the issue locally:**

If the workflow runs:
```yaml
- run: mise run test
- run: docker build -f backend/Dockerfile backend/
```

Then test locally:
```bash
# Run the exact commands from the workflow
mise run test
docker build -f backend/Dockerfile backend/

# Check for errors
echo $?  # Exit code (0 = success)
```

**Benefits:**
- Faster feedback loop (no push/wait cycle)
- Can inspect files and environment directly
- Can test fixes before committing

### 3. Get workflow run logs

**Method 1: Use GitHub CLI (preferred)**

```bash
# List recent workflow runs
gh run list --workflow="<workflow-name>" --limit 5

# View the latest run
gh run view

# View only failed jobs (most useful)
gh run view --log-failed

# View specific run by ID
gh run view <run-id> --log-failed

# Get run ID from latest run and view logs in one command
gh run list --workflow="Build" --limit 1 --json databaseId --jq '.[0].databaseId' | xargs gh run view --log-failed
```

**Method 2: Use GitHub API with curl**

```bash
# First, ensure GitHub token is available
echo $GITHUB_TOKEN  # or $GH_TOKEN

# List workflow runs
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/<owner>/<repo>/actions/runs

# Get logs for a specific run
curl -L -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/<owner>/<repo>/actions/runs/<run-id>/logs \
  > workflow-logs.zip

# Get job logs (JSON)
curl -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/<owner>/<repo>/actions/runs/<run-id>/jobs
```

**Method 3: Find API documentation**

If uncertain about API endpoints:

```bash
# Use Ref to search GitHub Actions API docs
ref_search_documentation "github actions api workflow runs logs"

# Use Context7 for GitHub API documentation
get-library-docs "/github/rest-api" --topic "workflow runs"

# Use Exa for current GitHub docs
web_search "github actions api get workflow logs"
```

### 4. Analyze the failure

**Common failure patterns to look for:**

#### Docker build failures
```
ERROR: failed to build: failed to solve: process ... did not complete successfully
```
- Check Dockerfile commands (COPY, RUN, etc.)
- Verify files exist in build context
- Check for missing dependencies or wrong paths

#### Module/file not found
```
Module not found: Can't resolve '@/lib/api'
ERROR: COPY requirements.txt .: not found
```
- Check if files are committed to git: `git ls-files <path>`
- Check .gitignore exclusions: `cat .gitignore | grep <pattern>`
- Force add if needed: `git add -f <path>`

#### Dependency conflicts
```
error: Unsupported compiler -- at least C++11 support is needed!
RuntimeError: No matching distribution found for onnxruntime
```
- Check Dockerfile system dependencies (gcc, g++, etc.)
- Verify Python/Node version compatibility
- Check package versions in requirements/package.json

#### Environment/secrets issues
```
Error: Missing environment variable API_KEY
```
- Check if secrets are configured in GitHub repo settings
- Verify secret names match workflow YAML
- Make configs optional for CI if possible

### 5. Fix iteratively

**Pattern: Fix → Commit → Push → Wait → Check**

```bash
# 1. Make a fix based on logs
edit <file>

# 2. Test locally if possible
mise run test
docker build -f backend/Dockerfile backend/

# 3. Commit with descriptive message
git add <file>
git commit -m "fix(ci): <specific issue fixed>"

# 4. Push to trigger workflow
git push

# 5. Wait for workflow to start (use sleep to avoid rate limits)
sleep 15
gh run list --workflow="Build" --limit 1

# 6. Wait for completion and check status
sleep 90  # Typical build time
gh run list --workflow="Build" --limit 1

# 7. If failed, get logs and repeat
gh run view --log-failed | grep -A 10 "ERROR:"
```

**Important: Use timeouts and sleep commands**
- Don't spam the API with rapid requests
- `sleep 15` after push (wait for workflow to trigger)
- `sleep 60-90` for builds to complete
- Use `gh run watch` for interactive monitoring (but this blocks)

### 6. Common fixes by error type

#### Fix: Missing file in build context
```bash
# Check if file is in git
git ls-files <path>

# If missing, check .gitignore
grep <pattern> .gitignore

# Force add and commit
git add -f <path>
git commit -m "fix: add <file> to git (was ignored)"
```

#### Fix: Wrong Dockerfile commands
```bash
# Update Dockerfile to match project structure
# For uv projects:
COPY pyproject.toml .
RUN uv pip install --system --no-cache .

# For bun projects:
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
```

#### Fix: Missing system dependencies
```bash
# Add to Dockerfile RUN apt-get install
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

#### Fix: Wrong base image or version
```bash
# Update FROM line in Dockerfile
FROM python:3.13-slim    # Not 3.14 (too new)
FROM oven/bun:1          # Not node:24-alpine
```

### 7. When to pause and confirm

**Pause before making these changes without confirmation:**

- Changing production deployment workflows
- Modifying security-sensitive steps (auth, secrets)
- Major refactoring of workflow structure
- Changing branch protection rules or PR requirements
- Deleting workflow files or jobs

**Safe to proceed automatically:**
- Fixing obvious errors (typos, wrong paths)
- Updating dependencies or versions
- Adding missing files or dependencies
- Fixing Docker build commands
- Adjusting timeouts or retry logic

### 8. Verification checklist

After each fix iteration:

- [ ] Workflow status is ✓ (green check)
- [ ] All jobs completed successfully
- [ ] No warnings or deprecation notices
- [ ] Build artifacts/images created (if applicable)
- [ ] Tests passed (if applicable)

View final status:
```bash
# List recent runs to see status
gh run list --workflow="Build" --limit 3

# Verify images were pushed (for Docker builds)
gh api /user/packages/container/<image-name>/versions
```

## Real-world example workflow

From actual troubleshooting session:

```bash
# 1. Check workflow failed
gh run list --workflow="Build" --limit 1
# STATUS: X (failed)

# 2. Get logs
gh run list --workflow="Build" --limit 1 --json databaseId --jq '.[0].databaseId' | xargs gh run view --log-failed 2>&1 | grep -B 5 "ERROR:"

# 3. Identified issues:
# - Backend: COPY requirements.txt not found (project uses pyproject.toml)
# - Frontend: npm ci failed (project uses bun)
# - Backend: Missing g++ compiler for chromadb
# - Frontend: Module @/lib/api not found (file not in git)

# 4. Fix backend Dockerfile
# Changed requirements.txt to pyproject.toml
# Added g++ to apt-get install

# 5. Fix frontend Dockerfile  
# Changed npm ci to bun install --frozen-lockfile
# Changed user creation commands for Debian base

# 6. Test locally
docker build -f backend/Dockerfile -t test backend/
docker build -f frontend/Dockerfile -t test frontend/
# Both succeeded!

# 7. Commit and push
git add backend/Dockerfile frontend/Dockerfile
git commit -m "fix: update Dockerfiles to match project tooling"
git push

# 8. Wait and check
sleep 15
gh run list --workflow="Build" --limit 1
# Still failed - new error!

# 9. Found missing file issue
git ls-files frontend/lib/
# (empty - not in git!)

# 10. Add missing file
git add -f frontend/lib/api.ts
git commit -m "fix: add frontend/lib/api.ts to git (was ignored)"
git push

# 11. Final verification
sleep 90
gh run list --workflow="Build" --limit 1
# STATUS: ✓ Success!
```

## Pro tips

**Efficient log searching:**
```bash
# Find errors quickly
gh run view --log-failed 2>&1 | grep -A 10 "ERROR:"

# Find specific failure point
gh run view --log-failed 2>&1 | grep -B 5 "module-not-found"

# Count errors
gh run view --log-failed 2>&1 | grep -c "ERROR:"

# Save logs for analysis
gh run view --log-failed > failure-logs.txt
```

**Monitoring status:**
```bash
# Keep checking until status changes
while true; do
  gh run list --workflow="Build" --limit 1
  sleep 30
done

# Or use watch mode (interactive)
gh run watch --interval 5
```

**Testing fixes locally first:**
```bash
# Always test Docker builds locally before pushing
docker build -f <dockerfile> <context> 2>&1 | tee build.log

# Check exit code
echo $?  # 0 = success

# Test specific commands from workflow
mise run test
mise run lint
```

## Anti-patterns to avoid

❌ **Don't:**
- Push multiple rapid fixes without waiting for workflow results
- Make changes without reading the logs first
- Guess at fixes without understanding the root cause
- Skip local testing when possible
- Make destructive changes without confirmation

✅ **Do:**
- Read logs thoroughly to understand the failure
- Test locally before pushing (when possible)
- Make incremental fixes (one issue at a time)
- Use descriptive commit messages for each fix
- Wait appropriate time between checks (use sleep)
- Document complex issues in commit messages

## Tools priority order

When getting workflow information:

1. **First choice: gh CLI** - `gh run view --log-failed`
   - Most convenient, formatted output
   - No token management needed
   
2. **Second choice: GitHub API with curl** - When gh unavailable
   - Requires GITHUB_TOKEN env var
   - More verbose but works everywhere
   
3. **Third choice: Documentation lookup** - When API endpoints unclear
   - Use `ref_search_documentation "github actions api"`
   - Use `get-library-docs "/github/rest-api"`
   - Use `web_search "github api workflows"`

## Summary checklist

When troubleshooting workflows:

- [ ] Read the workflow YAML file to understand what should happen
- [ ] Test workflow commands locally first (when possible)
- [ ] Use `gh run view --log-failed` to get detailed logs
- [ ] Identify the root cause before making fixes
- [ ] Test fixes locally (Docker builds, commands, etc.)
- [ ] Commit with clear message describing the fix
- [ ] Push and wait (use `sleep 15-90` depending on build time)
- [ ] Check status with `gh run list`
- [ ] Repeat until workflow passes (✓)
- [ ] Verify all jobs completed successfully
