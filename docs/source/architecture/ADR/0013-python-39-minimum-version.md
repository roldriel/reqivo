# ADR-013: Python 3.9+ Minimum Version

**Status**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

## Context

Python versions and support:

| Version | Release | EOL | Status |
|---------|---------|-----|--------|
| 3.7 | 2018-06 | 2023-06 | ❌ EOL |
| 3.8 | 2019-10 | 2024-10 | ❌ EOL |
| 3.9 | 2020-10 | 2025-10 | ✅ Supported |
| 3.10 | 2021-10 | 2026-10 | ✅ Supported |
| 3.11 | 2022-10 | 2027-10 | ✅ Supported |
| 3.12 | 2023-10 | 2028-10 | ✅ Supported |

Features per version relevant for Reqivo:

**Python 3.9+**:
- `dict` merge operator (`|`)
- Type hints improvements (`list[str]` instead of `List[str]`)
- `zoneinfo` module
- Performance improvements

**Python 3.10+**:
- Pattern matching (`match`/`case`)
- Better error messages
- Union types (`str | None` instead of `Optional[str]`)

**Python 3.11+**:
- Exception groups
- Performance (10-60% faster)

## Decision

**Python 3.9+ is the minimum supported version**.

Configuration (`pyproject.toml`):
```toml
[project]
requires-python = ">=3.9"
```

**Testing matrix** (CI):
```yaml
# .github/workflows/ci.yml
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12"]
```

**Reason**:
- 3.9 has EOL in 2025-10 (sufficient runway)
- Modern type hints without `typing.List`, `typing.Dict`
- Async improvements
- Balance between modernity and compatibility

## Consequences

### Positive ✅

1. **Modern features**: Dict merge, better type hints
2. **Long support**: 3.9 EOL in 2025-10
3. **Performance**: 3.9+ is faster than 3.7/3.8
4. **Security**: Old versions without security patches

### Negative ❌

1. **Excludes 3.8**: Some users still on 3.8
2. **Legacy systems**: Old systems may not have 3.9+
3. **Corporate environments**: Companies slow to update

### Mitigations

- **Clear documentation**: Indicate 3.9+ requirement
- **Error message**: Setup.py fails with clear message if <3.9
- **Long support**: 3.9 EOL still distant

### Type Hints Examples

**Python 3.9+**:
```python
# ✅ Modern (3.9+)
def get_headers(self) -> dict[str, str]:
    return self._headers

def get_cookies(self) -> list[str]:
    return self._cookies

# ❌ Old (3.7-3.8)
from typing import Dict, List

def get_headers(self) -> Dict[str, str]:
    return self._headers

def get_cookies(self) -> List[str]:
    return self._cookies
```

**Python 3.10+** (future, requires bump):
```python
# Cleaner union types
def timeout(self) -> float | None:  # Instead of Optional[float]
    return self._timeout
```

### Migration Path

If in the future we need 3.10+ features:
- Major version bump (breaking change)
- Document in CHANGELOG.md
- Migration guide for users

## Alternatives Considered

1. **Python 3.8+**: Rejected. 3.8 EOL in 2024-10.
2. **Python 3.10+**: Rejected. Excludes too many users.
3. **Python 3.11+**: Rejected. Too recent.

## References

- [Python Release Schedule](https://devguide.python.org/versions/)
- PEP 596: Python 3.9 Release Schedule
