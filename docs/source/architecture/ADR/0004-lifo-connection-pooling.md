# ADR-004: LIFO Connection Pooling

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Connection pooling es crítico para performance. Dos estrategias principales:

1. **FIFO (First In, First Out)**: Cola, primeras conexiones se reutilizan primero
2. **LIFO (Last In, First Out)**: Stack, últimas conexiones se reutilizan primero

**Consideraciones**:
- Conexiones TCP idle tienen timeout del servidor
- Conexiones más recientes tienen más probabilidad de estar activas
- Cache locality: conexiones recientes están más "calientes"

### Decisión

**Usar LIFO (Last In, First Out) para connection pooling**.

Implementación:
```python
class ConnectionPool:
    def __init__(self):
        self._pools: Dict[str, List[Connection]] = {}

    def put_connection(self, host: str, port: int, conn: Connection):
        key = f"{host}:{port}"
        self._pools[key].append(conn)  # Push (LIFO)

    def get_connection(self, host: str, port: int) -> Connection:
        key = f"{host}:{port}"
        if self._pools[key]:
            return self._pools[key].pop()  # Pop (LIFO)
        return self._create_new_connection(host, port)
```

**Características**:
- Pool separado por `host:port`
- Max size configurable por host
- Dead connection detection antes de reutilizar
- Thread-safe con `threading.Lock`

### Consecuencias

#### Positivas ✅

1. **Menos conexiones muertas**: Conexiones recientes más probablemente activas
2. **Cache locality**: Mejores hit rates en CPU cache
3. **Simple**: Lista como stack es eficiente O(1)
4. **Predictible**: Comportamiento determinístico

#### Negativas ❌

1. **Desbalance**: Algunas conexiones nunca se reutilizan si pool está activo
2. **Starvation**: Conexiones antiguas pueden quedar idle hasta timeout
3. **No es round-robin**: No distribuye carga uniformemente

#### Mitigaciones

- **Dead connection detection**: Verificar `is_usable()` antes de reutilizar
- **Max idle time**: (futuro) Descartar conexiones muy antiguas
- **Pool limits**: Evitar crecimiento infinito

### Alternativas Consideradas

1. **FIFO**: Rechazada. Más conexiones muertas, peor performance.
2. **Round-robin**: Rechazada. Más complejo, no mejora performance.
3. **Least recently used**: Rechazada. Overhead de tracking innecesario.

### Performance Data

(Pendiente: benchmarks comparando LIFO vs FIFO)

### Referencias

- [urllib3 connection pooling](https://urllib3.readthedocs.io/en/stable/advanced-usage.html#connection-pooling)
- httpcore pool implementation
