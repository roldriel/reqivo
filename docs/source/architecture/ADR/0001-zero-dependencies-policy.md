# ADR-001: Zero Dependencies Policy

**Estado**: ✅ Aceptada
**Fecha**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Contexto

Los clientes HTTP existentes en Python (`requests`, `httpx`, `aiohttp`) dependen de múltiples librerías externas:
- `requests`: urllib3, certifi, chardet, idna
- `httpx`: httpcore, certifi, h11, sniffio
- `aiohttp`: aiosignal, attrs, frozenlist, multidict, yarl

Esto crea problemas en:
- **Sistemas embebidos**: Espacio limitado
- **Aplicaciones de seguridad crítica**: Más dependencias = mayor superficie de ataque
- **Containers cloud-native**: Minimizar footprint
- **Auditoría**: Más código para revisar

### Decisión

**Reqivo NO tendrá dependencias externas en runtime**. Solo usará la biblioteca estándar de Python 3.9+.

Esto significa:
- ✅ Solo `import` de módulos stdlib: `socket`, `ssl`, `http`, `json`, etc.
- ✅ Implementación manual de parsing HTTP/1.1
- ✅ Implementación manual de WebSocket (RFC 6455)
- ❌ NO usar: `urllib3`, `h11`, `httpcore`, etc.
- ❌ NO usar: `certifi` (confiamos en certificados del sistema)
- ❌ NO usar: `chardet` (usamos stdlib charset detection)

**Dependencias de desarrollo permitidas**:
- `pytest`, `coverage`, `mypy`, `black`, `isort`, `pylint`, `bandit` (solo dev/CI)
- `sphinx`, `myst-parser` (solo para docs)

### Consecuencias

#### Positivas ✅

1. **Portabilidad máxima**: Funciona donde Python funciona
2. **Seguridad**: Menor superficie de ataque
3. **Footprint mínimo**: Ideal para containers y embedded systems
4. **Sin dependency hell**: No hay conflictos de versiones
5. **Auditable**: Todo el código es visible y controlable
6. **Instalación instantánea**: `pip install reqivo` sin descargas extra

#### Negativas ❌

1. **Más código propio que mantener**: Parsing HTTP manual
2. **Re-inventar la rueda**: Funcionalidad ya existente en librerías
3. **Posibles bugs**: Implementaciones nuevas tienen más riesgo inicial
4. **Menos features avanzados**: Algunas optimizaciones requieren C extensions
5. **Desarrollo más lento**: Sin aprovechar código existente

#### Mitigaciones

- **Cobertura de tests ≥97%**: Para detectar bugs en código propio
- **Type hints estrictos**: Para prevenir errores
- **Roadmap conservador**: Priorizar robustez sobre features
- **Documentación de limitaciones**: Ser transparente sobre trade-offs

### Alternativas Consideradas

1. **Permitir dependencias opcionales**: Rechazada. Complejiza instalación.
2. **Solo dependencias puras Python**: Rechazada. Sigue siendo complejidad extra.
3. **Usar urllib3 como httpx/requests**: Rechazada. Pierde valor diferencial.

### Referencias

- Issue original: (pendiente)
- Discusión: (pendiente)
