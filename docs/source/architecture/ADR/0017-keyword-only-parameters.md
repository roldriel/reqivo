# ADR-017: Keyword-Only Parameters for Request Methods

**Estado**: Accepted
**Date**: 2026-02-11
**Deciders**: Rodrigo Roldan

## Context

Session request methods (`post`, `put`, `patch`, `delete`) accept multiple optional
parameters: `headers`, `body`, `timeout`, `limits`. Two API design options:

1. **Positional arguments**: `session.post(url, headers, body, timeout, limits)`
2. **Keyword-only arguments**: `session.post(url, *, headers=None, body=None, ...)`

Common errors with positional arguments:
```python
# Bug: body accidentally passed as headers
session.post("http://example.com", "my data")

# Bug: argument order confusion
session.post("http://example.com", None, "my data", None, {"max_body_size": 1024})
```

## Decision

**All optional parameters after `url` are keyword-only** (enforced via `*` separator).

```python
class Session:
    def get(self, url: str, headers=None, timeout=5, limits=None) -> Response: ...

    def post(  # pylint: disable=too-many-arguments
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = 5,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response: ...
```

**Rules**:
- `url` is the only positional parameter
- `get()` keeps positional args (no `body` parameter, less risk of confusion)
- Methods with `body` (`post`, `put`, `patch`, `delete`) use keyword-only args
- `pylint: disable=too-many-arguments` is acceptable for these methods

## Consequences

### Positive

1. **Clear intent**: `session.post(url, body="data")` is unambiguous
2. **Error prevention**: Cannot accidentally swap `headers` and `body`
3. **Extensible**: New parameters can be added without breaking existing calls
4. **Readable**: Call sites are self-documenting

### Negative

1. **Verbosity**: Requires explicit keyword names at call sites
2. **Pylint suppression**: `too-many-arguments` needs inline disable

### Mitigations

- Keyword names are short and intuitive (`body=`, `timeout=`)
- Pylint suppression is scoped to specific methods, not global

## Alternatives Considered

1. **All positional**: Rejected. Error-prone for methods with many optional params.
2. **Config object**: Rejected. Over-engineering for 4-5 parameters.
3. **Builder pattern**: Rejected. Adds complexity without proportional benefit.

## References

- PEP 3102: Keyword-Only Arguments
- Python requests library API design
