# ADR-009: 97% Test Coverage Minimum

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Test coverage mide qué % del código es ejecutado por tests. Niveles comunes:
- 80%: Bueno para proyectos legacy
- 90%: Muy bueno
- 95%+: Excelente
- 100%: Aspiracional, difícil de mantener

Reqivo es cero dependencias, código crítico (HTTP, TLS, sockets). Bugs pueden causar:
- Security issues (header injection, TLS bypass)
- Data corruption
- Silent failures

**Tipos de coverage**:
1. **Statement coverage**: Líneas ejecutadas
2. **Branch coverage**: Caminos de if/else ejecutados (más estricto)
3. **Por archivo**: Coverage individual de cada módulo
4. **Total del proyecto**: Coverage agregado de todos los módulos

### Decisión

**Mínimo 97% de test coverage total del proyecto, con branch coverage habilitado**.

**Coverage Policy**:
```
✅ Prioridad: Coverage TOTAL del proyecto ≥ 97%
✅ Branch coverage habilitado (--branch)
⚠️  Coverage por archivo: Meta aspiracional, NO bloqueante
✅ Excepción: Código defensivo y edge cases no testeables
```

Configuración (`pyproject.toml`):
```toml
[tool.coverage.run]
source = ["reqivo"]
branch = true  # CRÍTICO: Branch coverage habilitado
omit = [
    "*/__init__.py",
    "tests/*",
    "setup.py"
]

[tool.coverage.report]
fail_under = 97           # Umbral TOTAL del proyecto
precision = 2
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "raise NotImplementedError"
]

[tool.coverage.html]
directory = "htmlcov"
```

**Reglas de Coverage**:

1. **Total del proyecto**:
   - ✅ DEBE ser ≥97% (bloqueante en CI)
   - ✅ Medido con branch coverage
   - ❌ NO merge PRs con coverage total < 97%

2. **Por archivo individual**:
   - ⚠️  Meta aspiracional: 90%+ por módulo
   - ⚠️  NO bloqueante en CI
   - ✅ Permitido <90% si: código defensivo, edge cases no testeables, platform-specific

3. **Branch coverage**:
   - ✅ Habilitado obligatoriamente (`--branch`)
   - ✅ Más estricto que statement coverage
   - ✅ Detecta paths no testeados en if/else

**Excepciones permitidas**:
```python
# Defensive programming
if some_impossible_condition:  # pragma: no cover
    raise AssertionError("Should never happen")

# Platform-specific code
if sys.platform == "win32":  # pragma: no cover (testing on Linux)
    ...

# Error handling no testeable
except UnicodeDecodeError:  # pragma: no cover
    # iso-8859-1 decoder handles all byte values
    pass
```

**Razón para priorizar total vs por-archivo**:
- Algunos módulos core (connection, session) naturalmente tienen más branches
- Edge cases y código defensivo difíciles de testear exhaustivamente
- **Lo importante**: Cobertura global alta garantiza robustez del proyecto
- Permite flexibilidad en módulos complejos sin comprometer calidad total

### Consecuencias

#### Positivas ✅

1. **Confidence**: Refactorings seguros
2. **Bug prevention**: Tests detectan regresiones
3. **Documentation**: Tests son ejemplos de uso
4. **API design**: Testing obliga a buena API
5. **Debugging**: Bugs se replican en tests

#### Negativas ❌

1. **Desarrollo más lento**: Escribir tests toma tiempo
2. **Mantenimiento**: Tests también necesitan mantenerse
3. **False confidence**: 97% no garantiza ausencia de bugs
4. **Overhead**: Tests complejos pueden ser frágiles

#### Mitigaciones

- **TDD**: Tests primero reduce rework
- **Fast tests**: Optimizar suite para velocidad
- **Good fixtures**: Reutilizar setup entre tests
- **Clear test names**: Tests son documentación

### Test Types

**Requeridos**:
1. **Unit tests**: Cada función/método aislado
2. **Integration tests**: Componentes juntos
3. **Edge cases**: Límites, valores especiales
4. **Error paths**: Excepciones, timeouts, failures

**Deseables**:
1. **Property-based**: hypothesis para casos aleatorios
2. **Performance**: Benchmarks para regresiones
3. **Load tests**: Behavior bajo carga

### Coverage Report

```bash
# Run con coverage
pytest --cov=reqivo --cov-report=html --cov-report=term

# Verificar threshold
coverage report --fail-under=97

# Ver HTML report
open htmlcov/index.html
```

### Alternativas Consideradas

1. **95% threshold**: Rechazada. Permite demasiadas excepciones.
2. **100% threshold**: Rechazada. Muy difícil mantener.
3. **No threshold**: Rechazada. Coverage decae con tiempo.

### Referencias

- pytest-cov documentation
- coverage.py documentation
