# ADR-005: HTTP/1.1 Before HTTP/2

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Opciones de protocolo HTTP a soportar:

1. **HTTP/1.1**: Universal, simple, bien entendido
2. **HTTP/2**: Multiplexing, server push, binary framing, HPACK compression
3. **HTTP/3**: QUIC, UDP-based

**Complejidad relativa**:
- HTTP/1.1: Parsing de texto, relativamente simple
- HTTP/2: Requiere HPACK, multiplexing, binary frames, flow control
- HTTP/3: Requiere QUIC stack completo

### Decisión

**Implementar HTTP/1.1 completo y robusto ANTES de HTTP/2**.

Roadmap de protocolos:
```
v0.1.x - v0.6.x: HTTP/1.1 complete & robust
v1.0.0:          HTTP/2 support added
v2.0.0+:         HTTP/3 (maybe)
```

**Criterios para considerar HTTP/2**:
- ✅ HTTP/1.1 RFC 7230-7235 compliant
- ✅ Chunked transfer encoding completo
- ✅ Connection pooling robusto
- ✅ Redirects automáticos
- ✅ TLS configurable
- ✅ Tests exhaustivos (97%+)
- ✅ Production-ready stability

**HTTP/2 scope (v1.0.0)**:
- Multiplexing de streams
- HPACK header compression
- Server push handling
- Binary framing
- Flow control
- Priority

### Consecuencias

#### Positivas ✅

1. **Mejor foundation**: HTTP/1.1 robusto antes de complejidad
2. **Usable hoy**: HTTP/1.1 cubre 99% de casos
3. **Menos riesgo**: No introducir bugs de HTTP/2 temprano
4. **Debugging simple**: HTTP/1.1 es texto legible
5. **Zero dependencies**: HTTP/2 sin h2 lib es posible pero complejo

#### Negativas ❌

1. **Sin HTTP/2 features**: No multiplexing, no server push (por ahora)
2. **Performance limitado**: HTTP/1.1 tiene head-of-line blocking
3. **Competencia**: httpx ya tiene HTTP/2

#### Mitigaciones

- **Roadmap claro**: HTTP/2 en v1.0.0 está comprometido
- **Documentar limitación**: Ser transparente sobre HTTP/1.1 only
- **Connection pooling**: Mitiga parcialmente lack de multiplexing

### Alternativas Consideradas

1. **HTTP/2 desde día 1**: Rechazada. Demasiada complejidad inicial.
2. **Solo HTTP/1.1 forever**: Rechazada. HTTP/2 es futuro.
3. **HTTP/3 primero**: Rechazada. Extremadamente complejo.

### Referencias

- RFC 7230-7235: HTTP/1.1
- RFC 7540: HTTP/2
- RFC 9114: HTTP/3
