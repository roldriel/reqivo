# ADR-001: Zero Dependencies Policy

**Status**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

## Context

Existing HTTP clients in Python (`requests`, `httpx`, `aiohttp`) depend on multiple external libraries:
- `requests`: urllib3, certifi, chardet, idna
- `httpx`: httpcore, certifi, h11, sniffio
- `aiohttp`: aiosignal, attrs, frozenlist, multidict, yarl

This creates problems in:
- **Embedded systems**: Limited space
- **Security-critical applications**: More dependencies = larger attack surface
- **Cloud-native containers**: Minimize footprint
- **Auditing**: More code to review

## Decision

**Reqivo will NOT have external runtime dependencies**. It will only use the Python 3.9+ standard library.

This means:
- ✅ Only `import` from stdlib modules: `socket`, `ssl`, `http`, `json`, etc.
- ✅ Manual implementation of HTTP/1.1 parsing
- ✅ Manual implementation of WebSocket (RFC 6455)
- ❌ DO NOT use: `urllib3`, `h11`, `httpcore`, etc.
- ❌ DO NOT use: `certifi` (we trust system certificates)
- ❌ DO NOT use: `chardet` (we use stdlib charset detection)

**Allowed development dependencies**:
- `pytest`, `coverage`, `mypy`, `black`, `isort`, `pylint`, `bandit` (dev/CI only)
- `sphinx`, `myst-parser` (docs only)

## Consequences

#### Positive ✅

1. **Maximum portability**: Works wherever Python works
2. **Security**: Smaller attack surface
3. **Minimal footprint**: Ideal for containers and embedded systems
4. **No dependency hell**: No version conflicts
5. **Auditable**: All code is visible and controllable
6. **Instant installation**: `pip install reqivo` without extra downloads

#### Negative ❌

1. **More code to maintain**: Manual HTTP parsing
2. **Re-inventing the wheel**: Functionality already exists in libraries
3. **Potential bugs**: New implementations have higher initial risk
4. **Fewer advanced features**: Some optimizations require C extensions
5. **Slower development**: Without leveraging existing code

#### Mitigations

- **Test coverage ≥97%**: To detect bugs in custom code
- **Strict type hints**: To prevent errors
- **Conservative roadmap**: Prioritize robustness over features
- **Documentation of limitations**: Be transparent about trade-offs

## Alternatives Considered

1. **Allow optional dependencies**: Rejected. Complicates installation.
2. **Only pure Python dependencies**: Rejected. Still adds extra complexity.
3. **Use urllib3 like httpx/requests**: Rejected. Loses differentiating value.

## References

- Original issue: (pending)
- Discussion: (pending)
