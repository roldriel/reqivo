# ADR-003: Session-Based State Management

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Dos patrones comunes en clientes HTTP:

1. **Stateless requests** (como `urllib`):
   ```python
   response = urllib.request.urlopen(url)
   ```

2. **Stateful sessions** (como `requests`):
   ```python
   session = requests.Session()
   session.headers.update({'User-Agent': 'my-app'})
   response = session.get(url)  # Headers automáticos
   ```

Necesitamos decidir si Reqivo soporta estado persistente entre requests.

### Decisión

**Implementar Session-based architecture** siguiendo el patrón de `requests`:

- **Session**: Mantiene estado (cookies, headers, auth, connection pool)
- **Request**: Builder stateless que usa Session si se proporciona
- **API dual**: Soportar ambos patrones (stateless y stateful)

Estructura:
```python
# Stateful (recomendado)
with Session() as session:
    session.set_basic_auth("user", "pass")
    session.headers["User-Agent"] = "MyApp/1.0"

    resp1 = session.get(url1)  # Headers y auth automáticos
    resp2 = session.get(url2)  # Cookies de resp1 incluidas
    # Connection pool reutiliza conexiones

# Stateless (simple)
response = Request.send("GET", url)  # Sin estado, sin pool
```

**Responsabilidades**:

**Session**:
- ✅ Cookie jar (parsing Set-Cookie, envío automático)
- ✅ Headers persistentes
- ✅ Authentication (Basic, Bearer)
- ✅ Connection pooling
- ✅ Context manager (cleanup automático)

**Request**:
- ✅ Construcción de HTTP request bytes
- ✅ Header injection prevention
- ✅ Envío de requests
- ❌ NO mantiene estado
- ❌ NO tiene connection pool propio

### Consecuencias

#### Positivas ✅

1. **Familiar**: Patrón conocido de `requests`
2. **Eficiente**: Reutilización de conexiones vía pool
3. **Conveniente**: Headers/cookies/auth automáticos
4. **Flexible**: Soporta ambos patrones (stateful/stateless)
5. **Clean separation**: Session = estado, Request = builder

#### Negativas ❌

1. **Complejidad**: Más código que solo stateless
2. **Estado mutable**: Sessions pueden tener side effects
3. **Thread safety**: Sessions no son thread-safe por diseño

#### Mitigaciones

- **Documentar thread safety**: Session por thread
- **Context managers**: Garantizar cleanup
- **Stateless API disponible**: Para casos simples

### Alternativas Consideradas

1. **Solo stateless**: Rechazada. Ineficiente para múltiples requests.
2. **Solo stateful**: Rechazada. Demasiado overhead para casos simples.
3. **Global state**: Rechazada. Anti-pattern, dificulta testing.

### Referencias

- requests.Session documentation
- HTTP State Management (RFC 6265)
