# ADR-013: Python 3.9+ Minimum Version

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Python versions y soporte:

| Version | Release | EOL | Status |
|---------|---------|-----|--------|
| 3.7 | 2018-06 | 2023-06 | ❌ EOL |
| 3.8 | 2019-10 | 2024-10 | ❌ EOL |
| 3.9 | 2020-10 | 2025-10 | ✅ Supported |
| 3.10 | 2021-10 | 2026-10 | ✅ Supported |
| 3.11 | 2022-10 | 2027-10 | ✅ Supported |
| 3.12 | 2023-10 | 2028-10 | ✅ Supported |

Features por versión relevantes para Reqivo:

**Python 3.9+**:
- `dict` merge operator (`|`)
- Type hints improvements (`list[str]` en lugar de `List[str]`)
- `zoneinfo` module
- Performance improvements

**Python 3.10+**:
- Pattern matching (`match`/`case`)
- Better error messages
- Union types (`str | None` en lugar de `Optional[str]`)

**Python 3.11+**:
- Exception groups
- Performance (10-60% faster)

### Decisión

**Python 3.9+ es la versión mínima soportada**.

Configuración (`pyproject.toml`):
```toml
[project]
requires-python = ">=3.9"
```

**Testing matrix** (CI):
```yaml
# .github/workflows/ci.yml
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12"]
```

**Razón**:
- 3.9 tiene EOL en 2025-10 (suficiente runway)
- Type hints modernos sin `typing.List`, `typing.Dict`
- Async improvements
- Balance entre modernidad y compatibilidad

### Consecuencias

#### Positivas ✅

1. **Modern features**: Dict merge, better type hints
2. **Long support**: 3.9 EOL en 2025-10
3. **Performance**: 3.9+ es más rápido que 3.7/3.8
4. **Security**: Versiones viejas sin security patches

#### Negativas ❌

1. **Excluye 3.8**: Algunos usuarios aún en 3.8
2. **Legacy systems**: Sistemas viejos pueden no tener 3.9+
3. **Corporate environments**: Empresas lentas para actualizar

#### Mitigaciones

- **Documentación clara**: Indicar 3.9+ requirement
- **Error message**: Setup.py falla con mensaje claro si <3.9
- **Long support**: 3.9 EOL lejano aún

### Type Hints Examples

**Python 3.9+**:
```python
# ✅ Moderno (3.9+)
def get_headers(self) -> dict[str, str]:
    return self._headers

def get_cookies(self) -> list[str]:
    return self._cookies

# ❌ Viejo (3.7-3.8)
from typing import Dict, List

def get_headers(self) -> Dict[str, str]:
    return self._headers

def get_cookies(self) -> List[str]:
    return self._cookies
```

**Python 3.10+** (futuro, requiere bump):
```python
# Union types más limpios
def timeout(self) -> float | None:  # En lugar de Optional[float]
    return self._timeout
```

### Migration Path

Si en futuro necesitamos features de 3.10+:
- Major version bump (breaking change)
- Documentar en [CHANGELOG.md](../../changes/CHANGELOG.md)
- Migration guide para usuarios

### Alternativas Consideradas

1. **Python 3.8+**: Rechazada. 3.8 EOL en 2024-10.
2. **Python 3.10+**: Rechazada. Excluye demasiados usuarios.
3. **Python 3.11+**: Rechazada. Muy reciente.

### Referencias

- [Python Release Schedule](https://devguide.python.org/versions/)
- PEP 596: Python 3.9 Release Schedule
