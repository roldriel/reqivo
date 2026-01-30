# ADR-010: Limited Public API Surface

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

API pública es el contrato con usuarios. Dos enfoques:

1. **Todo público**: Exportar todos los módulos
   - Pros: Máxima flexibilidad
   - Cons: Difícil mantener backward compatibility

2. **API limitada**: Solo exportar lo esencial
   - Pros: Libertad para cambiar internals
   - Cons: Puede limitar use cases avanzados

### Decisión

**Exportar solo API esencial en `reqivo.__init__.py`**.

Exports públicos:
```python
# src/reqivo/__init__.py

# Client layer (high-level)
from .client.session import Session, AsyncSession
from .client.request import Request, AsyncRequest
from .client.response import Response
from .client.websocket import WebSocket, AsyncWebSocket
from .client.auth import basic_auth, bearer_token

# Exceptions (todas públicas)
from .exceptions import *

# Version
from .version import __version__

# Utils selectos
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
    # Exceptions exportadas vía *
]
```

**NO exportado (internal)**:
- `reqivo.http.*` (HttpParser, Headers, Body)
- `reqivo.transport.*` (Connection, ConnectionPool, TLS)
- `reqivo.utils.*` (excepto Timeout)

**Uso**:
```python
# ✅ Público, estable
from reqivo import Session, Response
from reqivo import ConnectTimeout

# ❌ Internal, puede cambiar
from reqivo.http.http11 import HttpParser  # No garantizado
from reqivo.transport.connection import Connection  # Puede cambiar
```

### Consecuencias

#### Positivas ✅

1. **Backward compatibility**: Solo API pública es estable
2. **Refactoring freedom**: Internals pueden cambiar sin breaking
3. **Clear contract**: Usuarios saben qué es estable
4. **Smaller docs**: Solo documentar API pública
5. **Semantic versioning**: Breaking changes claros

#### Negativas ❌

1. **Menos flexibilidad**: Usuarios no pueden acceder a internals
2. **Feature requests**: Casos avanzados pueden no ser posibles
3. **Frustración**: "¿Por qué no puedo importar X?"

#### Mitigaciones

- **Extensible API**: Permitir customización vía hooks
- **Feature requests**: Evaluar promover internals a públicos
- **Documentation**: Explicar por qué API es limitada

### Semantic Versioning

Con API limitada, versioning es claro:

- **Major (X.0.0)**: Breaking changes en API pública
- **Minor (0.X.0)**: Nuevas features en API pública, backward compatible
- **Patch (0.0.X)**: Bug fixes, no cambia API

Cambios internos NO requieren major version bump.

### Alternativas Consideradas

1. **Todo público**: Rechazada. Dificulta evolución.
2. **Nada público (solo Session)**: Rechazada. Muy limitante.
3. **Underscore convention**: Rechazada. No enforced por imports.

### References

- [Semantic Versioning](https://semver.org/)
- PEP 8: Public and Internal Interfaces
