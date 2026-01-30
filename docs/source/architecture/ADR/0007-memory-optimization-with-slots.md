# ADR-007: Memory Optimization with `__slots__`

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Python objects usan `__dict__` para atributos, que consume memoria:
- `__dict__` es dinámico, permite añadir atributos en runtime
- Cada instancia tiene overhead de ~240 bytes (Python 3.9+)
- Para objetos frecuentemente instanciados, esto suma

`__slots__` es una optimización:
- Define atributos fijos en clase
- No usa `__dict__`, reduce memoria ~40%
- Acceso a atributos es más rápido
- Trade-off: no se pueden añadir atributos dinámicos

### Decisión

**Usar `__slots__` en clases frecuentemente instanciadas**:

Clases con `__slots__`:
- ✅ `Response` (una por request)
- ✅ `Request` (una por request)
- ✅ `Connection` (muchas en pool)
- ✅ `Timeout` (una por request)
- ✅ `Headers` (una por request)

Clases sin `__slots__`:
- ❌ `Session` (pocas instancias, mutable por diseño)
- ❌ `ConnectionPool` (una por session)
- ❌ Exceptions (raramente instanciadas)

Ejemplo:
```python
class Response:
    __slots__ = (
        "raw",
        "status_line",
        "status_code",
        "headers",
        "body",
        "_text",
        "_json",
    )

    def __init__(self, raw: bytes):
        self.raw = raw
        self.status_line: str = ""
        # ...
```

### Consecuencias

#### Positivas ✅

1. **Memoria**: ~40% menos memoria por instancia
2. **Performance**: Acceso a atributos más rápido
3. **Cache locality**: Mejor CPU cache utilization
4. **Type hints**: Atributos declarados explícitamente
5. **Bugs prevention**: No se pueden añadir typos como atributos

#### Negativas ❌

1. **Rigidez**: No se pueden añadir atributos dinámicos
2. **Debugging**: Algunos debuggers asumen `__dict__`
3. **Monkey patching**: No se puede (feature, no bug)
4. **Herencia**: Subclasses deben declarar sus propios `__slots__`

#### Mitigaciones

- **Solo en clases estables**: No usar en clases experimentales
- **Documentar**: Indicar que clase usa `__slots__`
- **Testing**: Verificar que no se intenten añadir atributos

### Memory Savings

Estimación (Python 3.9+):

```python
# Sin __slots__
Response object: ~280 bytes + data

# Con __slots__
Response object: ~170 bytes + data

# Para 10,000 requests:
Sin __slots__: ~2.8 MB
Con __slots__:  ~1.7 MB
Ahorro:         ~1.1 MB (39%)
```

### Alternativas Consideradas

1. **No usar __slots__**: Rechazada. Desperdicia memoria innecesariamente.
2. **Usar __slots__ en todo**: Rechazada. Dificulta extensibilidad.
3. **Usar dataclasses frozen**: Considerada. Menos control que __slots__.

### Referencias

- [Python __slots__ documentation](https://docs.python.org/3/reference/datamodel.html#slots)
- [Memory savings with __slots__](https://wiki.python.org/moin/UsingSlots)
