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

> **See the numbers yourself:** For detailed performance metrics, check out our **[Benchmark Suite](https://github.com/roldriel/reqivo/blob/main/benchmarks/README.md)**.

---

## 📚 Documentation & Examples

Comprehensive examples and documentation are available:

### 📖 Core Examples
- **[Quick Start](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md)** - Installation, basic GET/POST, async introduction
- **[Advanced Patterns](https://github.com/roldriel/reqivo/blob/main/examples/advanced_patterns.md)** - Connection pooling, headers, timeouts, cookies
- **[Async Usage](https://github.com/roldriel/reqivo/blob/main/examples/async_usage.md)** - Concurrent requests, async patterns, error handling

### 🔗 More Examples (Coming Soon)
- WebSocket usage
- Error handling strategies
- Authentication patterns
- Real-world scenarios

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

### Run Benchmarks

```bash
cd benchmarks
pip install -r comparison_requirements.txt
python comparison.py
```

---

## 📖 Requirements

- Python 3.9 or higher
- No external dependencies for core functionality
- Optional: `pympler` for memory benchmarks

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📝 License

MIT © 2026 — Rodrigo Ezequiel Roldán  
[View full license](LICENSE.md)

---

## 🗺️ Roadmap

See our detailed [ROADMAP.md](docs/architecture/ROADMAP.md) for planned features and development timeline.
