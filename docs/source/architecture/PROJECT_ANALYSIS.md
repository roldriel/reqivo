# Reqivo: Requirements and Context Analysis

> **Project Definition Document**
> Defines the purpose, justification, and boundaries of the Reqivo project.
>
> **For technical implementation details, see:**
> - [ARCHITECTURE.md](ARCHITECTURE.md) (Architecture and Components)
> - [ADR/0000-ADR.md](ADR/0000-ADR.md) (Design Decisions)
> - [ROADMAP.md](ROADMAP.md) (Roadmap and Development Status)

---

## 1. 🔭 Vision and Problem

### The Problem
The HTTP client ecosystem in Python is mature, but the dominant solutions (`requests`, `httpx`, `aiohttp`) share a characteristic that becomes problematic in certain contexts: **dependency on complex external libraries**.

They depend on a chain of libraries (`urllib3`, `httpcore`, `certifi`, `idna`, `chardet`, `h11`, `yarl`, etc.) which introduce:
1.  **Audit Complexity**: Difficult to verify security in critical infrastructures.
2.  **Footprint**: Unnecessary for specific microservices or embedded systems.
3.  **Version Conflicts**: "Dependency hell" in large projects.
4.  **Opacity**: Difficulty understanding and controlling *exactly* what happens at the network level.

### The Solution: Reqivo
**Reqivo** positions itself as a **modern, transparent, and self-contained** alternative.

Its value proposition is to **eliminate the black box**: provide a complete, asynchronous HTTP client using **exclusively the Python standard library**, without sacrificing modern ergonomics or performance.

---

## 2. 📋 Fundamental Requirements

### Functional Requirements (The "What")

1.  **Complete HTTP/1.1 Client**:
    *   Robust support for standard methods (GET, POST, PUT, DELETE, etc.).
    *   Correct handling of `Transfer-Encoding: chunked` (read and write).
    *   Support for `keep-alive` and connection reuse.
    *   Automatic handling of cookies and redirects.

2.  **WebSocket Client (RFC 6455)**:
    *   Complete implementation of WebSocket handshake and framing.
    *   Support for text and binary messages.
    *   PING/PONG handling.
    *   Seamless integration with the async architecture.

3.  **Dual Interface (Async/Sync)**:
    *   **Native Async**: Designed on `asyncio` as a first-class citizen.
    *   **Sync Wrapper**: Blocking interface compatible for simple scripts or legacy migration.

### Non-Functional Requirements (The "How")

1.  **Zero Dependencies Policy (Zero-Deps)**:
    *   **Strict**: Production code MUST NOT import anything outside the `stdlib` (Python 3.9+).
    *   **Exception**: Only development tools (pytest, mypy, black) allowed in dev environment.

2.  **Security by Design**:
    *   Use of secure TLS contexts by default (`ssl.create_default_context`).
    *   Strict input validation (prevention of Header Injection).
    *   Strict typing (`mypy --strict`) to prevent runtime type errors.

3.  **Performance and Efficiency**:
    *   Use of `__slots__` to minimize memory consumption in frequent objects (Request, Response).
    *   "Async-first" architecture to maximize I/O concurrency.
    *   Smart pooling strategy (LIFO) to improve cache locality and reduce latency.

4.  **Maintainability and Quality**:
    *   Test coverage > 97% mandatory.
    *   Readable and explicit code (prefer clarity over "magic").
    *   Exhaustive documentation of architectural decisions.

---

## 3. 🚧 Project Scope

Defining what Reqivo is NOT is as important as defining what it is.

### ✅ In-Scope
*   Complete and robust **HTTP/1.1** protocol.
*   **HTTP/2** protocol (Planned for v1.0.0, not initial).
*   **WebSocket** client protocol.
*   Standard Authentication (Basic, Bearer).
*   Granular Timeouts handling (connect, read, pool).
*   Official support for CPython 3.9, 3.10, 3.11, 3.12+.

### ❌ Out-of-Scope
*   **Legacy Complexity**: No support for EOL Python versions (< 3.9).
*   **HTTP/3 (QUIC)**: Too complex for a "stdlib-only" implementation for now.
*   **Brotli Compression**: Requires external dependencies or complex C-extensions (Gzip/Deflate via stdlib is acceptable).
*   **Server Implementation**: Reqivo is purely a **client**.
*   **Web Framework**: Not a competitor to Flask/FastAPI/Django.

---

## 4. 🧭 Development Philosophy

> *"If you can't explain how your HTTP client works just by looking at your own code, you depend on too much magic."*

Reqivo seeks to be **educational and transparent**. The code should be a reference for how to implement network protocols in modern Python, serving for both production, auditing, and learning.
