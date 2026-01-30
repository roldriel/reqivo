# ADR-011: Three-Layer Architecture

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Arquitectura de cliente HTTP puede organizarse de varias formas:

1. **Monolithic**: Todo en un solo módulo
2. **Two-layer**: Client + Transport
3. **Three-layer**: Client + Protocol + Transport
4. **Multi-layer**: Muchas capas de abstracción

### Decisión

**Arquitectura de 3 capas claramente separadas**:

```
┌─────────────────────────────────────────┐
│         CLIENT LAYER                    │
│  Session, Request, Response, WebSocket  │  ← API pública, lógica de negocio
│  Responsabilidad: Estado, cookies, auth │
├─────────────────────────────────────────┤
│         PROTOCOL LAYER                  │
│  HttpParser, Headers, Body, URL         │  ← Parsing HTTP/1.1, WebSocket frames
│  Responsabilidad: Protocolo HTTP        │
├─────────────────────────────────────────┤
│         TRANSPORT LAYER                 │
│  Connection, ConnectionPool, TLS        │  ← Sockets, TLS, I/O
│  Responsabilidad: Red, conexiones       │
└─────────────────────────────────────────┘
```

**Principios**:
- **Separation of concerns**: Cada capa tiene responsabilidad única
- **Dependency direction**: Client → Protocol → Transport (nunca al revés)
- **Reusability**: Protocol layer compartido entre sync y async
- **Testability**: Cada capa testeable independientemente

**Mapeo a código**:
```
src/reqivo/
├── client/         ← CLIENT LAYER
│   ├── session.py
│   ├── request.py
│   ├── response.py
│   ├── websocket.py
│   └── auth.py
├── http/           ← PROTOCOL LAYER
│   ├── http11.py
│   ├── headers.py
│   ├── body.py
│   └── url.py
├── transport/      ← TRANSPORT LAYER
│   ├── connection.py
│   ├── connection_pool.py
│   └── tls.py
└── utils/          ← Cross-cutting concerns
    ├── timing.py
    └── validators.py
```

### Consecuencias

#### Positivas ✅

1. **Clear separation**: Cada capa tiene propósito definido
2. **Testability**: Mockear capas inferiores fácilmente
3. **Reusability**: Protocol layer usado por sync y async
4. **Maintainability**: Cambios localizados en capa correcta
5. **Understandability**: Estructura clara para nuevos devs

#### Negativas ❌

1. **Indirection**: Más archivos, más imports
2. **Over-engineering**: Puede ser excesivo para proyecto pequeño
3. **Coupling**: Capas deben coordinarse cuidadosamente

#### Mitigaciones

- **Clear interfaces**: Cada capa con API bien definida
- **Documentation**: Arquitectura documentada en ADR (este doc)
- **Refactoring freedom**: Internals pueden reorganizarse

### Layer Responsibilities

**CLIENT LAYER**:
- Estado de sesión (cookies, headers, auth)
- API pública de alto nivel
- Gestión de connection pool
- Business logic (redirects, retries)

**PROTOCOL LAYER**:
- Parsing HTTP responses
- Construcción HTTP requests
- WebSocket frame handling
- Protocol compliance (RFC 7230-7235, RFC 6455)

**TRANSPORT LAYER**:
- Socket management (TCP)
- TLS/SSL handshake
- Timeout enforcement
- Conexión física a servidor

### Alternativas Consideradas

1. **Monolithic**: Rechazada. Difícil mantener y testear.
2. **Two-layer**: Rechazada. Protocol y transport muy acoplados.
3. **Four+ layers**: Rechazada. Over-engineering innecesario.

### Referencias

- Clean Architecture (Robert C. Martin)
- Layered Architecture Pattern
