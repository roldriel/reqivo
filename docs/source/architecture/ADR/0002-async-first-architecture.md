# ADR-002: Async-First Architecture

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Python está evolucionando hacia async/await como patrón dominante para I/O:
- FastAPI, Starlette, Quart son async-first
- Concurrency mejora rendimiento en I/O-bound operations
- asyncio es parte de stdlib desde Python 3.4

Opciones de diseño:
1. **Sync-first** (como `requests`): API principal síncrona
2. **Async-only** (como `aiohttp`): Solo async, sin sync
3. **Async-first**: Async principal, sync como wrapper

### Decisión

**Reqivo será async-first**: La API principal será async, con wrappers síncronos.

Estructura:
```python
# Clases primarias (async)
AsyncSession
AsyncRequest
AsyncConnection
AsyncConnectionPool
AsyncWebSocket

# Clases secundarias (sync wrappers)
Session       → usa AsyncSession con asyncio.run()
Request       → usa AsyncRequest con asyncio.run()
Connection    → usa AsyncConnection con asyncio.run()
ConnectionPool → usa AsyncConnectionPool con threading.Lock
WebSocket     → usa AsyncWebSocket con asyncio.run()
```

**Código compartido**:
- HTTP parsing es el mismo para async y sync
- Protocol layer es stateless y reutilizable
- Solo cambia la capa de I/O (socket vs asyncio)

### Consecuencias

#### Positivas ✅

1. **Performance**: Async permite mejor concurrency
2. **Moderno**: Sigue tendencia del ecosistema Python
3. **Escalable**: Manejo eficiente de muchas conexiones simultáneas
4. **Compatibilidad**: Sync API disponible para legacy code
5. **Single implementation**: Código de protocolo compartido

#### Negativas ❌

1. **Complejidad**: Mantener dos APIs (sync y async)
2. **Learning curve**: Async es más difícil para beginners
3. **Debugging**: Async debugging es más complejo
4. **Overhead**: Sync wrapper tiene overhead de `asyncio.run()`

#### Mitigaciones

- **Documentación clara**: Ejemplos de ambos usos
- **Defaults sensatos**: Sync API simple y directa
- **Testing dual**: Tests para sync y async paths

### Alternativas Consideradas

1. **Sync-only**: Rechazada. No aprovecha concurrency moderna.
2. **Async-only**: Rechazada. Excluye usuarios sync.
3. **Sync-first**: Rechazada. Wrapper async sobre sync es ineficiente.

### Referencias

- PEP 492: Coroutines with async/await
- asyncio documentation
