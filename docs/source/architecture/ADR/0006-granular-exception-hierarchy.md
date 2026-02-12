# ADR-006: Granular Exception Hierarchy

**Status**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

## Context

Error handling can be:

1. **Generic**: A single `HttpError` type
2. **Granular**: Specific exceptions for each error type
3. **Very granular**: Sub-exceptions for each case

Benefits of granularity:
- Allows selective catching
- Better recovery strategies
- Easier debugging
- Clearer documentation

## Decision

**Implement granular exception hierarchy** with 3 levels:

```text
ReqivoError (base)
├── RequestError
│   ├── NetworkError
│   │   └── TlsError
│   ├── TimeoutError
│   │   ├── ConnectTimeout
│   │   └── ReadTimeout
│   ├── ProtocolError
│   │   └── InvalidResponseError
│   └── RedirectLoopError
```

**Usage**:
```python
# Specific catch
try:
    response = session.get(url)
except ConnectTimeout:
    # Retry with higher timeout
    response = session.get(url, timeout=30)
except TlsError:
    # Log security issue
    logger.error("TLS handshake failed")
    raise
except NetworkError:
    # Fallback to another URL
    response = session.get(fallback_url)

# Generic catch
except ReqivoError:
    # Handle any Reqivo error
    pass
```

**Principles**:
- Each exception represents a distinct failure mode
- Inheritance allows catching at different levels
- Descriptive names (`ConnectTimeout` vs `Timeout`)
- Optional context info without sensitive data

## Consequences

#### Positive ✅

1. **Recovery strategies**: Code can react specifically
2. **Debugging**: Clearer stack traces
3. **Documentation**: API docs show what can fail
4. **Type safety**: mypy can verify exception handling
5. **Testable**: Easy to test each error path

#### Negative ❌

1. **More code**: More classes to maintain
2. **Documentation**: Each exception must be documented
3. **Breaking changes**: Adding exceptions can break existing code

#### Mitigations

- **Stable hierarchy**: Don't change inheritance after v1.0
- **Complete documentation**: Each exception with docstring
- **Semantic versioning**: Breaking changes only in major versions

## Alternatives Considered

1. **Only ReqivoError**: Rejected. Makes recovery difficult.
2. **String error codes**: Rejected. Not type-safe.
3. **Stdlib exceptions**: Rejected. Not specific to HTTP.

## References

- PEP 3151: Reworking the OS and IO exception hierarchy
- requests.exceptions
