---
date: 2025-12-31
status: Accepted
---

# 0002: Release Please for Monorepo Versioning

## Context

Wingman is a monorepo containing two independently versioned packages:
- `backend`: Python FastAPI application
- `frontend`: Next.js TypeScript application

As the project grows, maintaining consistent versioning and changelogs across multiple packages becomes critical. Manual version bumping is error-prone and doesn't scale well.

## Decision

We will use [Release Please](https://github.com/googleapis/release-please) to automate release management for the monorepo with the following configuration:

- Each package (`backend`, `frontend`) maintains independent version tracking in `.release-please-manifest.json`
- Release candidates are created as pull requests on each commit to `main` that includes conventional commits (`feat:`, `fix:`, etc.)
- Both packages start at version `1.0.0`
- Package-specific changelogs are generated at `backend/CHANGELOG.md` and `frontend/CHANGELOG.md`
- The GitHub Action triggers on pushes to `main` and manages release creation

## Alternatives Considered

1. **Manual versioning** — Versioning via git tags and manual changelog management
   - Simple to understand but error-prone and requires discipline
   - Hard to scale across multiple packages
   - No automatic changelog generation

2. **Semantic Release** — Alternative automation tool
   - Similar capabilities to Release Please
   - Less GHA-native integration
   - Requires additional configuration overhead

3. **Single version across packages** — Bump all packages together
   - Simpler to manage but creates artificial coupling
   - Forces releases of unchanged packages
   - Not suitable for independent package lifecycles

## Consequences

**Positive:**
- Automated, consistent versioning reduces human error
- Conventional commits (`feat:`, `fix:`) drive semantic versioning automatically
- Independent version tracking allows packages to release on their own schedule
- GitHub-native integration requires no external services

**Negative:**
- Requires discipline to follow conventional commit conventions
- Release PRs are created on every `feat:` or `fix:` commit (requires explicit merge to release)
- Changelog format is opinionated and harder to customize

## References

- `.github/workflows/release-please.yml` — Workflow configuration
- `release-please-config.json` — Package and changelog settings
- `.release-please-manifest.json` — Version tracker
- [Release Please Documentation](https://github.com/googleapis/release-please)
- [Conventional Commits](https://www.conventionalcommits.org/)
