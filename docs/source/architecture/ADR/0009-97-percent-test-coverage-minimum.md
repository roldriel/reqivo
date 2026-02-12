# ADR-009: 97% Test Coverage Minimum

**Status**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

## Context

Test coverage measures what % of code is executed by tests. Common levels:
- 80%: Good for legacy projects
- 90%: Very good
- 95%+: Excellent
- 100%: Aspirational, difficult to maintain

Reqivo is zero dependencies, critical code (HTTP, TLS, sockets). Bugs can cause:
- Security issues (header injection, TLS bypass)
- Data corruption
- Silent failures

**Coverage types**:
1. **Statement coverage**: Lines executed
2. **Branch coverage**: if/else paths executed (more strict)
3. **Per file**: Individual coverage of each module
4. **Project total**: Aggregated coverage of all modules

## Decision

**Minimum 97% test coverage of total project, with branch coverage enabled**.

**Coverage Policy**:
```
✅ Priority: TOTAL project coverage ≥ 97%
✅ Branch coverage enabled (--branch)
⚠️  Per-file coverage: Aspirational goal, NOT blocking
✅ Exception: Defensive code and non-testable edge cases
```

Configuration (`pyproject.toml`):
```toml
[tool.coverage.run]
source = ["reqivo"]
branch = true  # CRITICAL: Branch coverage enabled
omit = [
    "*/__init__.py",
    "tests/*",
    "setup.py"
]

[tool.coverage.report]
fail_under = 97           # Project TOTAL threshold
precision = 2
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "raise NotImplementedError"
]

[tool.coverage.html]
directory = "htmlcov"
```

**Coverage Rules**:

1. **Project total**:
   - ✅ MUST be ≥97% (blocking in CI)
   - ✅ Measured with branch coverage
   - ❌ DO NOT merge PRs with total coverage < 97%

2. **Individual file**:
   - ⚠️  Aspirational goal: 90%+ per module
   - ⚠️  NOT blocking in CI
   - ✅ Allowed <90% if: defensive code, non-testable edge cases, platform-specific

3. **Branch coverage**:
   - ✅ Mandatory enabled (`--branch`)
   - ✅ Stricter than statement coverage
   - ✅ Detects untested paths in if/else

**Allowed exceptions**:
```python
# Defensive programming
if some_impossible_condition:  # pragma: no cover
    raise AssertionError("Should never happen")

# Platform-specific code
if sys.platform == "win32":  # pragma: no cover (testing on Linux)
    ...

# Non-testable error handling
except UnicodeDecodeError:  # pragma: no cover
    # iso-8859-1 decoder handles all byte values
    pass
```

**Reason for prioritizing total vs per-file**:
- Some core modules (connection, session) naturally have more branches
- Edge cases and defensive code difficult to test exhaustively
- **What matters**: High global coverage guarantees project robustness
- Allows flexibility in complex modules without compromising total quality

## Consequences

#### Positive ✅

1. **Confidence**: Safe refactorings
2. **Bug prevention**: Tests detect regressions
3. **Documentation**: Tests are usage examples
4. **API design**: Testing enforces good API
5. **Debugging**: Bugs are replicated in tests

#### Negative ❌

1. **Slower development**: Writing tests takes time
2. **Maintenance**: Tests also need maintenance
3. **False confidence**: 97% doesn't guarantee bug absence
4. **Overhead**: Complex tests can be fragile

#### Mitigations

- **TDD**: Tests first reduces rework
- **Fast tests**: Optimize suite for speed
- **Good fixtures**: Reuse setup between tests
- **Clear test names**: Tests are documentation

### Test Types

**Required**:
1. **Unit tests**: Each function/method isolated
2. **Integration tests**: Components together
3. **Edge cases**: Boundaries, special values
4. **Error paths**: Exceptions, timeouts, failures

**Desirable**:
1. **Property-based**: hypothesis for random cases
2. **Performance**: Benchmarks for regressions
3. **Load tests**: Behavior under load

### Coverage Report

```bash
# Run with coverage
pytest --cov=reqivo --cov-report=html --cov-report=term

# Verify threshold
coverage report --fail-under=97

# View HTML report
open htmlcov/index.html
```

## Alternatives Considered

1. **95% threshold**: Rejected. Allows too many exceptions.
2. **100% threshold**: Rejected. Very difficult to maintain.
3. **No threshold**: Rejected. Coverage decays over time.

## References

- pytest-cov documentation
- coverage.py documentation
