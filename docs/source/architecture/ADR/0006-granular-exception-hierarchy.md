# ADR-006: Granular Exception Hierarchy

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Manejo de errores puede ser:

1. **Genérico**: Un solo tipo `HttpError`
2. **Granular**: Excepciones específicas para cada tipo de error
3. **Muy granular**: Sub-excepciones para cada caso

Beneficios de granularidad:
- Permite catch selectivo
- Mejor recovery strategies
- Debugging más fácil
- Documentación más clara

### Decisión

**Implementar jerarquía granular de excepciones** con 3 niveles:

```python
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

**Uso**:
```python
# Catch específico
try:
    response = session.get(url)
except ConnectTimeout:
    # Retry con timeout mayor
    response = session.get(url, timeout=30)
except TlsError:
    # Log security issue
    logger.error("TLS handshake failed")
    raise
except NetworkError:
    # Fallback a otra URL
    response = session.get(fallback_url)

# Catch genérico
except ReqivoError:
    # Handle cualquier error de Reqivo
    pass
```

**Principios**:
- Cada excepción representa un failure mode distinto
- Herencia permite catch a diferentes niveles
- Nombres descriptivos (`ConnectTimeout` vs `Timeout`)
- Context info opcional sin datos sensibles

### Consecuencias

#### Positivas ✅

1. **Recovery strategies**: Código puede reaccionar específicamente
2. **Debugging**: Stack traces más claros
3. **Documentation**: API docs muestran qué puede fallar
4. **Type safety**: mypy puede verificar exception handling
5. **Testable**: Fácil testear cada path de error

#### Negativas ❌

1. **Más código**: Más clases que mantener
2. **Documentación**: Cada excepción debe documentarse
3. **Breaking changes**: Añadir excepciones puede romper código existente

#### Mitigaciones

- **Jerarquía estable**: No cambiar inheritance después de v1.0
- **Documentación completa**: Cada excepción con docstring
- **Semantic versioning**: Breaking changes solo en major versions

### Alternativas Consideradas

1. **Solo ReqivoError**: Rechazada. Dificulta recovery.
2. **String error codes**: Rechazada. No type-safe.
3. **Excepciones de stdlib**: Rechazada. No específicas para HTTP.

### Referencias

- PEP 3151: Reworking the OS and IO exception hierarchy
- requests.exceptions
