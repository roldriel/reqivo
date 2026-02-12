# ADR-008: Strict Type Safety

**Status**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

## Context

Python allows dynamic programming without types, but type hints (PEP 484+) offer:
- Bug catching during development
- IDE autocomplete and refactoring
- Living documentation
- Better maintainability

Strictness levels in mypy:
1. **No types**: No verification
2. **Basic**: Optional types, permissive
3. **Strict**: All types required, no `Any`

## Decision

**Use mypy in strict mode with complete type hints**.

Configuration (`pyproject.toml`):
```toml
[tool.mypy]
strict = true
disallow_untyped_defs = true
disallow_any_explicit = true
disallow_any_generics = true
warn_return_any = true
warn_unused_ignores = true
warn_redundant_casts = true
warn_unreachable = true
```

**Rules**:
- ✅ All parameters with types
- ✅ All returns with types
- ✅ Avoid `Any` (use generics or Union)
- ✅ Type hints in variables when not inferred
- ❌ DO NOT use `# type: ignore` without justification
- ❌ DO NOT use `cast()` unnecessarily

Example:
```python
# ✅ CORRECT
def send_request(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> Response:
    ...

# ❌ INCORRECT
def send_request(url, headers=None, timeout=None):  # No types
    ...

# ❌ INCORRECT
def send_request(url: Any, headers: Any = None) -> Any:  # Any abused
    ...
```

## Consequences

#### Positive ✅

1. **Bug prevention**: Catch errors in development, not at runtime
2. **IDE support**: Autocomplete, go-to-definition, refactoring
3. **Documentation**: Types are executable documentation
4. **Refactoring safety**: Changes don't break contracts
5. **Onboarding**: New devs understand API faster
6. **PEP 561 compliance**: Distribution of type stubs

#### Negative ❌

1. **Verbosity**: Longer code
2. **Learning curve**: Advanced type hints are complex
3. **Maintenance**: Types must be updated with code
4. **CI time**: mypy adds time to pipeline

#### Mitigations

- **Generics**: Use `TypeVar` for flexibility
- **Protocols**: For type-safe duck typing
- **Overload**: For complex signatures
- **Documentation**: Type hints guide for contributors

### Type Coverage

Target: 100% type coverage

```bash
# Verify coverage
mypy --strict src/reqivo
```

## Alternatives Considered

1. **No types**: Rejected. Loses type safety benefits.
2. **Partial types**: Rejected. Inconsistency causes confusion.
3. **Gradual typing**: Rejected. New project, start strict.

## References

- PEP 484: Type Hints
- PEP 561: Distributing Type Information
- mypy documentation
