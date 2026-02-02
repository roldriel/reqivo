# Reqivo
![Python](https://img.shields.io/badge/Python-3.9+-yellow?style=for-the-badge&logo=python)
![PyPI](https://img.shields.io/pypi/v/reqivo?style=for-the-badge)
![Coverage](https://img.shields.io/badge/Coverage-97%25-green?style=for-the-badge)
![Build](https://img.shields.io/badge/Build-passing-green?style=for-the-badge)

---

> Modern, async-first HTTP client for Python · Zero external dependencies · Built on standard library

---

## 🚀 TL;DR

```python
from reqivo import AsyncSession
import asyncio

async def main():
    async with AsyncSession() as session:
        response = await session.get('https://api.github.com/users/octocat')
        print(response.json())

asyncio.run(main())
```

---

## ✨ What is Reqivo?

Reqivo is a modern, async-first HTTP client library built entirely on Python's standard library. No external dependencies, pure performance.

### Philosophy

> **Reqivo is not a requests replacement. It's a modern HTTP foundation.**

Reqivo exists to bridge the gap between low-level `socket`/`ssl` usage and the need for a fast, modern HTTP client:

- Using **only the standard library** (Python 3.9+)
- Providing an **async-first API** with sync support
- Supporting modern protocols (HTTP/1.1, HTTP/2, WebSockets)
- Maintaining **zero external dependencies** for maximum portability

**Reqivo is for:**
- Developers who want async HTTP without heavyweight dependencies
- Teams building **cloud-native** applications  
- Projects where **dependencies matter** (embedded systems, security-critical apps)
- Anyone seeking **performance and simplicity**

---

## 📦 Installation

```bash
pip install reqivo
```

---

## 🧪 Basic Example

### Sync Usage

```python
from reqivo import Session

session = Session()
response = session.get('https://api.example.com/data')
print(response.status)  # 200
print(response.json())   # {"key": "value"}
```

### Async Usage

```python
import asyncio
from reqivo import AsyncSession

async def fetch():
    async with AsyncSession() as session:
        response = await session.get('https://api.example.com/data')
        return response.json()

asyncio.run(fetch())
```

### WebSocket Support

```python
from reqivo import WebSocket

ws = WebSocket('wss://echo.websocket.org')
ws.connect()
ws.send('Hello WebSocket!')
message = ws.receive()
ws.close()
```

---

## 🔍 Key Features

- ✅ **Zero external dependencies**: Pure Python (Python 3.9+)
- ✅ **Async-first design**: Built for modern async/await workflows
- ✅ **Sync support**: Also works in synchronous code
- ✅ **HTTP/1.1 support**: Full protocol implementation
- ✅ **WebSocket support**: Sync and async WebSocket clients
- ✅ **Connection pooling**: Automatic connection reuse for performance
- ✅ **Type hints**: Fully typed following PEP 561
- ✅ **Memory efficient**: Optimized with `__slots__` where beneficial
- ✅ **Comprehensive testing**: 97%+ test coverage

### Roadmap Features

- 🔄 **HTTP/2 support** (Planned v0.5.0)
- 🔄 **HTTP/3/QUIC** (Research phase)
- 🔄 **Advanced retry strategies** (Planned v0.3.0)
- 🔄 **Request/Response interceptors** (Planned v0.4.0)

---

## 🧾 Comparison with other libraries

### Why not requests, httpx, or aiohttp?

| Feature                                 | Reqivo | requests | httpx | aiohttp |
|-----------------------------------------|:------:|:--------:|:-----:|:-------:|
| Zero dependencies                       | ✅     | ❌       | ❌    | ❌      |
| Async/await native                      | ✅     | ❌       | ✅    | ✅      |
| Sync support                            | ✅     | ✅       | ✅    | ❌      |
| WebSocket support                       | ✅     | ❌       | ✅    | ✅      |
| HTTP/2 support                          | 🔄     | ❌       | ✅    | ✅      |
| Connection pooling                      | ✅     | ✅       | ✅    | ✅      |
| Type hints (PEP 561)                    | ✅     | ⚠️       | ✅    | ⚠️      |
| Memory optimized (`__slots__`)          | ✅     | ❌       | ❌    | ⚠️      |
| Coverage tested ≥ 97%                   | ✅     | ❓       | ✅    | ❓      |
| Standard library only                   | ✅     | ❌       | ❌    | ❌      |

> **Note:** Benchmark suite coming soon in a future release.

---

## 📚 Documentation & Examples

Comprehensive examples and documentation are available in the **[Examples Directory](https://github.com/roldriel/reqivo/blob/main/examples/README.md)**:

### 📖 Guides
- **[Quick Start](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md)** - Installation, basic GET/POST, async introduction
- **[Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md)** - Concurrent requests, async patterns
- **[Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md)** - Cookies, authentication, persistent connections
- **[Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md)** - Exception handling, retry logic, circuit breaker
- **[Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md)** - Connection pooling, streaming, WebSockets

---

## 🔧 Development & Testing

### Run Tests

```bash
# Run all tests with tox
tox

# Run specific Python version
tox -e py312

# Run with coverage
tox -e py312
coverage html && open htmlcov/index.html
```

---

## 📖 Requirements

- Python 3.9 or higher
- No external dependencies for core functionality

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](https://github.com/roldriel/reqivo/blob/main/CONTRIBUTING.md) for guidelines.

---

## 📝 License

MIT © 2026 — Rodrigo Ezequiel Roldán  
[View full license](https://github.com/roldriel/reqivo/blob/main/LICENSE.md)

---

## 🗺️ Roadmap & Changelog

- **[CHANGELOG](https://github.com/roldriel/reqivo/blob/main/CHANGELOG.md)** - Version history and release notes
- **[GitHub Issues](https://github.com/roldriel/reqivo/issues)** - Bug reports and feature requests
- **[Milestones](https://github.com/roldriel/reqivo/milestones)** - Planned features and development timeline
