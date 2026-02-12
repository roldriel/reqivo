# ADR-018: CI/CD Pipeline Strategy

**Estado**: Accepted
**Date**: 2026-02-11
**Deciders**: Rodrigo Roldan

### Context

As the project grows, automated quality checks become critical to prevent
regressions. Key questions:

1. What checks should run on every push/PR?
2. How to balance thoroughness vs CI execution time?
3. How to structure reusable CI components?

### Decision

**Three GitHub Actions workflows** with a shared composite action library:

#### CI Pipeline (`ci.yml`) — Runs on push/PR

| Job | Tool | Purpose |
|-----|------|---------|
| **validate** | dorny/paths-filter | Skip unchanged code, validate project structure |
| **test** | tox -e py | Unit tests on Python 3.9-3.14, coverage report |
| **lint** | tox -e lint | Black + isort + pylint (score >= 10.0) |
| **typing** | tox -e typing | mypy strict mode |
| **security** | bandit + pip-audit | Static security analysis |

All jobs (except validate) are conditional on source code changes via path filtering.

#### Release Pipeline (`release.yml`) — Runs on version tags

1. **validate-release**: Tag format validation, version match check
2. **pre-release-quality**: lint + typing + security (must pass before build)
3. **pre-release-tests**: Full test suite on Python 3.9-3.14
4. **build-package**: Build sdist and wheel
5. **publish-pypi**: Trusted publishing via OIDC (no API tokens)

#### Documentation Pipeline (`docs.yml`) — Runs on doc/source changes

1. **docs-build**: Sphinx build with Furo theme
2. **docs-deploy**: Deploy to GitHub Pages (master branch and tags only)

#### Composite Actions (`.github/actions/`)

| Action | Purpose |
|--------|---------|
| **setup-python** | Python setup with pip caching and optional tox install |
| **security-scan** | Bandit + pip-audit with configurable severity thresholds |

### Consequences

#### Positive

1. **Fast feedback**: lint/typing/security run in parallel with tests
2. **No regressions**: Every PR must pass all quality gates
3. **Reusable**: Composite actions reduce duplication across workflows
4. **Secure releases**: Quality gate + trusted publishing (no stored secrets)
5. **Cost-effective**: Path filtering skips unnecessary runs

#### Negative

1. **Complexity**: Three workflows + two composite actions to maintain
2. **GitHub dependency**: Tied to GitHub Actions ecosystem
3. **Execution time**: Full matrix (6 Python versions) takes ~15 minutes

#### Mitigations

- Path filtering reduces unnecessary CI runs
- Jobs run in parallel where possible
- Composite actions centralize tool setup logic

### Alternatives Considered

1. **Single workflow**: Rejected. Too slow, no parallel execution.
2. **External CI (Jenkins, CircleCI)**: Rejected. GitHub Actions is simpler for GitHub-hosted projects.
3. **Pre-commit hooks only**: Rejected. Insufficient for multi-version testing.

### References

- GitHub Actions documentation
- pypa/gh-action-pypi-publish (trusted publishing)
- dorny/paths-filter for conditional execution
