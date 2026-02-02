# ADR-010: Limited Public API Surface

**Status**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Context

Public API is the contract with users. Two approaches:

1. **Everything public**: Export all modules
   - Pros: Maximum flexibility
   - Cons: Difficult to maintain backward compatibility

2. **Limited API**: Only export essentials
   - Pros: Freedom to change internals
   - Cons: May limit advanced use cases

### Decision

**Export only essential API in `reqivo.__init__.py`**.

Public exports:
```python
# src/reqivo/__init__.py

# Client layer (high-level)
from .client.session import Session, AsyncSession
from .client.request import Request, AsyncRequest
from .client.response import Response
from .client.websocket import WebSocket, AsyncWebSocket
from .client.auth import basic_auth, bearer_token

# Exceptions (all public)
from .exceptions import *

# Version
from .version import __version__

# Selected utils
from .utils.timing import Timeout

__all__ = [
    # Sessions
    "Session",
    "AsyncSession",
    # Requests
    "Request",
    "AsyncRequest",
    # Response
    "Response",
    # WebSocket
    "WebSocket",
    "AsyncWebSocket",
    # Auth
    "basic_auth",
    "bearer_token",
    # Utils
    "Timeout",
    # Version
    "__version__",
    # Exceptions exported via *
]
```

**NOT exported (internal)**:
- `reqivo.http.*` (HttpParser, Headers, Body)
- `reqivo.transport.*` (Connection, ConnectionPool, TLS)
- `reqivo.utils.*` (except Timeout)

**Usage**:
```python
# ✅ Public, stable
from reqivo import Session, Response
from reqivo import ConnectTimeout

# ❌ Internal, may change
from reqivo.http.http11 import HttpParser  # Not guaranteed
from reqivo.transport.connection import Connection  # May change
```

### Consequences

#### Positive ✅

1. **Backward compatibility**: Only public API is stable
2. **Refactoring freedom**: Internals can change without breaking
3. **Clear contract**: Users know what is stable
4. **Smaller docs**: Only document public API
5. **Semantic versioning**: Clear breaking changes

#### Negative ❌

1. **Less flexibility**: Users cannot access internals
2. **Feature requests**: Advanced cases may not be possible
3. **Frustration**: "Why can't I import X?"

#### Mitigations

- **Extensible API**: Allow customization via hooks
- **Feature requests**: Evaluate promoting internals to public
- **Documentation**: Explain why API is limited

### Semantic Versioning

With limited API, versioning is clear:

- **Major (X.0.0)**: Breaking changes in public API
- **Minor (0.X.0)**: New features in public API, backward compatible
- **Patch (0.0.X)**: Bug fixes, doesn't change API

Internal changes DO NOT require major version bump.

### Alternatives Considered

1. **Everything public**: Rejected. Makes evolution difficult.
2. **Nothing public (only Session)**: Rejected. Too limiting.
3. **Underscore convention**: Rejected. Not enforced by imports.

### References

- [Semantic Versioning](https://semver.org/)
- PEP 8: Public and Internal Interfaces
