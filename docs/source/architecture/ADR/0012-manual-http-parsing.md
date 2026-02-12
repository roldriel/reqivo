# ADR-012: Manual HTTP Parsing

**Estado**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

## Context

Para parsear HTTP responses, opciones:

1. **Manual parsing**: Implementar parser propio
2. **Stdlib http.client**: Usar cliente HTTP de stdlib
3. **External library**: Usar h11, httpcore, etc.

Consideraciones:
- ADR-001 establece zero dependencies
- stdlib `http.client` es sync-only y algo limitado
- Manual parsing da control total

## Decision

**Implementar parser HTTP/1.1 manual en `reqivo.http.http11`**.

Características del parser:
```python
class HttpParser:
    """HTTP/1.1 response parser."""

    def parse_response(self, data: bytes) -> tuple[str, Headers, bytes]:
        """
        Parse raw HTTP response.

        Returns: (status_line, headers, body)
        Raises: InvalidResponseError si malformed
        """
        # Parse status line
        # Parse headers
        # Extract body
```

**Principios de implementación**:
- ✅ RFC 7230-7235 compliance (HTTP/1.1)
- ✅ Robusto contra malformed responses
- ✅ Límites configurables (headers size, body size)
- ✅ Error messages claros
- ✅ Sin regex complejo (simple string operations)

**Scope**:
- ✅ Status line parsing
- ✅ Header parsing (case-insensitive)
- ✅ Chunked transfer encoding
- ✅ Content-Length body reading
- ✅ Duplicate headers
- ❌ NO multiline headers (obs-fold obsoleto)
- ❌ NO auto-decompression (gzip, br) en v0.1.x

## Consequences

### Positive ✅

1. **Control total**: Customizar parsing a necesidades
2. **Zero deps**: Cumple ADR-001
3. **Debuggeable**: Código propio es más fácil debuggear
4. **Optimizable**: Podemos optimizar bottlenecks
5. **Educational**: Entendemos HTTP en profundidad

### Negative ❌

1. **Más código**: Parser no trivial (~150 LOC)
2. **Bugs potenciales**: Implementación nueva tiene riesgo
3. **Mantenimiento**: Debemos mantener compliance con RFC
4. **Edge cases**: Servidores raros pueden romper parser

### Mitigations

- **Tests exhaustivos**: 97%+ coverage en parser
- **RFC compliance tests**: Test against known responses
- **Fuzzing**: (futuro) Fuzzing para edge cases
- **Limits**: Límites evitan DoS

### Implementation Notes

**Status line parsing**:
```python
# HTTP/1.1 200 OK
status_line, rest = data.split(b"\r\n", 1)
http_version, status_code, reason = status_line.split(b" ", 2)
```

**Header parsing**:
```python
# Header: Value\r\n
# Header: Value\r\n
# \r\n  ← End of headers
headers_end = data.find(b"\r\n\r\n")
headers_text = data[:headers_end]
for line in headers_text.split(b"\r\n"):
    key, value = line.split(b": ", 1)
    headers[key.decode()] = value.decode()
```

**Duplicate headers**:
```python
# Set-Cookie: a=1
# Set-Cookie: b=2
# → headers["Set-Cookie"] = ["a=1", "b=2"]
```

### Security Considerations

**Header injection prevention**:
```python
# Verificar que headers no contengan \r\n
if "\r\n" in header_value:
    raise ValueError("Header injection attempt")
```

**Size limits** (v0.2.0):
```python
class HttpParser:
    def __init__(self, max_header_size: int = 8192, max_body_size: int = 10_000_000):
        self.max_header_size = max_header_size
        self.max_body_size = max_body_size
```

## Alternatives Considered

1. **http.client**: Rejected. Sync-only, menos control.
2. **h11**: Rejected. External dependency.
3. **Regex-based**: Rejected. Más lento, más complejo.

## References

- RFC 7230: HTTP/1.1 Message Syntax
- RFC 7231: HTTP/1.1 Semantics
