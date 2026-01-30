# ADR-008: Strict Type Safety

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Python permite programación dinámica sin tipos, pero type hints (PEP 484+) ofrecen:
- Catch de bugs en desarrollo
- IDE autocomplete y refactoring
- Documentación viva
- Mejor mantenibilidad

Niveles de strictness en mypy:
1. **No types**: No verificación
2. **Basic**: Tipos opcionales, permisivo
3. **Strict**: Todos los tipos requeridos, no `Any`

### Decisión

**Usar mypy en modo strict con type hints completos**.

Configuración (`pyproject.toml`):
```toml
[tool.mypy]
strict = true
disallow_untyped_defs = true
disallow_any_explicit = true
disallow_any_generics = true
warn_return_any = true
warn_unused_ignores = true
warn_redundant_casts = true
warn_unreachable = true
```

**Reglas**:
- ✅ Todos los parámetros con tipos
- ✅ Todos los returns con tipos
- ✅ Evitar `Any` (usar genéricos o Union)
- ✅ Type hints en variables cuando no se infiere
- ❌ NO usar `# type: ignore` sin justificación
- ❌ NO usar `cast()` innecesariamente

Ejemplo:
```python
# ✅ CORRECTO
def send_request(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> Response:
    ...

# ❌ INCORRECTO
def send_request(url, headers=None, timeout=None):  # No types
    ...

# ❌ INCORRECTO
def send_request(url: Any, headers: Any = None) -> Any:  # Any abusado
    ...
```

### Consecuencias

#### Positivas ✅

1. **Bug prevention**: Catch errores en desarrollo, no en runtime
2. **IDE support**: Autocomplete, go-to-definition, refactoring
3. **Documentation**: Tipos son documentación ejecutable
4. **Refactoring safety**: Cambios no rompen contratos
5. **Onboarding**: Nuevos devs entienden API más rápido
6. **PEP 561 compliance**: Distribución de type stubs

#### Negativas ❌

1. **Verbosidad**: Código más largo
2. **Learning curve**: Type hints avanzados son complejos
3. **Mantenimiento**: Tipos deben actualizarse con código
4. **CI time**: mypy añade tiempo al pipeline

#### Mitigaciones

- **Generics**: Usar `TypeVar` para flexibilidad
- **Protocols**: Para duck typing type-safe
- **Overload**: Para signatures complejas
- **Documentation**: Guía de type hints para contributors

### Type Coverage

Target: 100% type coverage

```bash
# Verificar coverage
mypy --strict src/reqivo
```

### Alternativas Consideradas

1. **No types**: Rechazada. Pierde beneficios de type safety.
2. **Partial types**: Rechazada. Inconsistencia confunde.
3. **Gradual typing**: Rechazada. Proyecto nuevo, empezar strict.

### Referencias

- PEP 484: Type Hints
- PEP 561: Distributing Type Information
- mypy documentation
