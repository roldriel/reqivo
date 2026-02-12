# ADR-014: Test Structure Organization

**Estado**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

## Context

Testing puede organizarse de varias formas:

1. **Flat structure**: Todos los tests en un directorio
2. **Mirror structure**: Tests reflejan estructura de src/
3. **Organized by type**: unit/, integration/, e2e/

Reqivo necesita:
- Unit tests para cada módulo
- Integration tests para flujos completos
- Mapeo claro código ↔ tests

## Decision

**Estructura organizada por tipo con mirror de src/**:

```
tests/
├── unit/                          ← Tests unitarios
│   ├── __init__.py
│   ├── test_version.py           ← src/reqivo/version.py
│   ├── test_exceptions.py        ← src/reqivo/exceptions.py
│   ├── test_utils.py             ← src/reqivo/utils/*
│   ├── test_response.py          ← src/reqivo/client/response.py
│   ├── test_request.py           ← src/reqivo/client/request.py
│   ├── test_session.py           ← src/reqivo/client/session.py (pendiente)
│   ├── test_websocket.py         ← src/reqivo/client/websocket.py (pendiente)
│   ├── test_http_parser.py       ← src/reqivo/http/http11.py (pendiente)
│   ├── test_headers.py           ← src/reqivo/http/headers.py (pendiente)
│   ├── test_body.py              ← src/reqivo/http/body.py (pendiente)
│   ├── test_connection.py        ← src/reqivo/transport/connection.py (pendiente)
│   └── test_connection_pool.py   ← src/reqivo/transport/connection_pool.py (pendiente)
│
├── integration/                   ← Tests de integración
│   ├── __init__.py
│   ├── test_http_requests.py     ← GET/POST flows completos
│   ├── test_session_cookies.py   ← Session + cookies + redirects
│   ├── test_websocket_flow.py    ← WebSocket handshake + messages
│   ├── test_connection_pooling.py ← Pool reuse + concurrency
│   ├── test_tls_connections.py   ← HTTPS + TLS
│   └── test_timeouts.py          ← Timeout scenarios
│
├── e2e/                           ← Tests end-to-end (futuro)
│   └── test_real_servers.py      ← Tests contra httpbin, etc.
│
└── utils/                         ← Test utilities
    ├── __init__.py
    ├── fixtures.py               ← Shared fixtures
    ├── mock_server.py            ← Mock HTTP server
    └── assertions.py             ← Custom assertions
```

**Principios**:

1. **Mirror source structure**:
   - `src/reqivo/client/response.py` → `tests/unit/test_response.py`
   - Un test file por cada source file

2. **Naming convention**:
   - Unit tests: `test_<module>.py`
   - Integration tests: `test_<feature>_flow.py` o `test_<component>_integration.py`

3. **Test organization dentro del archivo**:
   ```python
   # tests/unit/test_response.py

   class TestResponseInit:
       """Tests for Response.__init__()"""

   class TestResponseText:
       """Tests for Response.text()"""

   class TestResponseJson:
       """Tests for Response.json()"""

   class TestResponseStreaming:
       """Tests for Response.iter_*()"""
   ```

4. **Fixture organization**:
   - Fixtures comunes en `tests/utils/fixtures.py`
   - Fixtures específicas en conftest.py local

## Consequences

### Positive ✅

1. **Findability**: Fácil encontrar tests para un módulo
2. **Completeness**: Detectar módulos sin tests
3. **Separation**: Unit vs integration claro
4. **Scalability**: Estructura crece con proyecto
5. **Clear mapping**: 1:1 entre source y test files

### Negative ❌

1. **Duplicate structure**: Dos árboles de directorios (src + tests)
2. **Renaming overhead**: Renombrar módulo requiere renombrar test
3. **Large test files**: Módulos grandes → test files grandes

### Mitigations

- **Split large tests**: Dividir por funcionalidad si es muy grande
- **Shared utilities**: Reutilizar fixtures y helpers
- **Clear docstrings**: Documentar qué testea cada clase/función

### Test Naming

**Unit test**:
```python
def test_response_text_decodes_utf8():
    """Response.text() should decode UTF-8 body correctly."""

def test_response_json_raises_on_invalid_json():
    """Response.json() should raise ValueError on invalid JSON."""
```

**Integration test**:
```python
def test_session_preserves_cookies_across_requests():
    """Session should send cookies from previous response."""

def test_connection_pool_reuses_connections():
    """Connection pool should reuse connections for same host."""
```

### Current Status

**Existentes**:
- ✅ `tests/unit/test_version.py`
- ✅ `tests/unit/test_exceptions.py`
- ✅ `tests/unit/test_utils.py`
- ✅ `tests/unit/test_response.py`
- ✅ `tests/unit/test_request.py`

**Pendientes** (según ADR-014):
- ❌ `tests/unit/test_session.py`
- ❌ `tests/unit/test_websocket.py`
- ❌ `tests/unit/test_http_parser.py`
- ❌ `tests/unit/test_headers.py`
- ❌ `tests/unit/test_body.py`
- ❌ `tests/unit/test_connection.py`
- ❌ `tests/unit/test_connection_pool.py`
- ❌ `tests/unit/test_auth.py`
- ❌ `tests/integration/*` (todos)

## Alternatives Considered

1. **Flat structure**: Rejected. Difícil escalar.
2. **By feature**: Rejected. Ambiguo qué es una "feature".
3. **Colocated tests**: Rejected. Mezcla concerns.

## References

- pytest documentation: Test layout
- Python Packaging Guide
