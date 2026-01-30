# Technical Architecture & Components

> **Technical Blueprint**
> This document describes **HOW** Reqivo is built internally.
>
> **External References:**
> - [ADR/0000-ADR.md](ADR/0000-ADR.md) - Why these decisions were made.
> - [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) - Requirements and context.

---

## 1. 🏗️ High-Level Design

Reqivo follows a strict **3 separate layers** architecture. Dependency flows always top-down: Client uses Protocol and Transport, but Transport never knows about Protocol or Client.

```
    USER CODE
       │
       ▼
┌──────────────────────┐
│  LAYER 1: CLIENT     │ 🧠 "The Brain"
│  (Session, Request)  │ • Maintains State (Cookies, Auth)
└──────────┬───────────┘ • Decides WHAT to do
           │
           │ 1. Request bytes needed
           ▼
┌──────────────────────┐
│  LAYER 2: PROTOCOL   │ 📜 "The Translator"
│ (HttpParser, Body)   │ • Pure Logic (No I/O)
└──────────┬───────────┘ • Converts Objects <-> Bytes
           │
           │ 2. Delivers raw bytes
           ▼
┌──────────────────────┐
│ LAYER 3: TRANSPORT   │ 🚚 "The Truck"
│ (Connection, Pool)   │ • Socket I/O & TLS
└──────────┬───────────┘ • Moves bytes A -> B
           │
           │ 3. Network traffic
           ▼
      INTERNET
```

### Design Principles
1.  **Separation of Concerns**: Each layer has a single purpose.
2.  **Protocol Agnostic Transport**: Transport layer moves *bytes*, doesn't know what HTTP is.
3.  **State Isolation**: Persistent state lives only in the Client layer (`Session`).

---

## 2. 🧩 Component Map

### Layer 1: CLIENT (Logic & State)
Location: `src/reqivo/client/`

This is the only layer the end user imports directly.

*   **Session (`session.py`)**: "The Brain".
    *   **Responsibility**: Maintains persistent state between requests.
    *   **Data**: Cookie Jar, Authentication credentials, Default Headers.
    *   **Resources**: Manages `ConnectionPool` lifecycle.
*   **Request (`request.py`)**: "The Builder".
    *   **Responsibility**: Ephemeral object preparing data for sending.
    *   **Action**: Validates inputs, serializes body, and delegates sending to session/transport.
*   **Response (`response.py`)**: "The Result".
    *   **Responsibility**: Parse and expose response comfortably.
    *   **Optimization**: Uses `__slots__` to reduce memory in high-throughput apps.
*   **WebSocket (`websocket.py`)**: RFC 6455 Client.
    *   Handles initial handshake (HTTP Upgrade).
    *   Manages frame send/receive loop.

### Layer 2: PROTOCOL (Communication Rules)
Location: `src/reqivo/http/`

Pure HTTP/1.1 implementation. No I/O, only memory data manipulation.

*   **HttpParser (`http11.py`)**:
    *   State machine for parsing responses.
    *   Detects message boundaries (Content-Length vs Chunked).
*   **Headers (`headers.py`)**:
    *   Specialized case-insensitive dictionary (`Content-Type` == `content-type`).
*   **Body (`body.py`)**:
    *   Utilities for reading streams (fixed-length, chunked).

### Layer 3: TRANSPORT (The Network)
Location: `src/reqivo/transport/`

In charge of moving bytes from A to B.

*   **Connection (`connection.py`)**:
    *   Wrapper over native `socket.socket`.
    *   Handles TLS handshake (`ssl.wrap_socket`).
    *   Applies socket-level timeouts.
*   **ConnectionPool (`connection_pool.py`)**:
    *   Store of active connections.
    *   **LIFO (Last-In, First-Out)** Strategy: Reuses most recent connection to improve cache locality and reduce server timeout closures.

---

## 3. 🔄 Data Flow

### Request Lifecycle (Sync)

```
  USER              SESSION           POOL             CONNECTION         INTERNET
   │                   │                │                  │                 │
   │ 1. get(url)       │                │                  │                 │
   ├──────────────────►│                │                  │                 │
   │                   │ 2. get_conn()  │                  │                 │
   │                   ├───────────────►│                  │                 │
   │                   │                │ 3. Pop LIFO      │                 │
   │                   │                ├─────────────────►│                 │
   │                   │                │                  │                 │
   │                   │   4. send()    │                  │ 5. write()      │
   │                   ├──────────────────────────────────►├────────────────►│
   │                   │                │                  │                 │
   │                   │                │                  │ 6. read()       │
   │                   │   7. parse()   │                  │◄────────────────┤
   │                   │◄──────────────────────────────────┤                 │
   │                   │                │                  │                 │
   │                   │ 8. put_conn()  │                  │                 │
   │                   ├───────────────►│                  │                 │
   │ 9. Response       │                │                  │                 │
   │◄──────────────────┤                │                  │                 │
```

1.  **Preparation**: `Session` combines user headers + cookie jar + auth headers.
2.  **Acquisition**: Connection requested from `ConnectionPool`. If one alive exists for that host (LIFO), it's used; else, open socket + TLS.
3.  **Transmission**: Raw bytes sent via socket.
4.  **Reception**: Bytes read until headers complete.
5.  **Parsing**: `HttpParser` validates and structures response.
6.  **Release**: Connection returned to pool for reuse.

---

## 4. ⚡ Concurrency Model

Reqivo is **Async-First**. This means the "true" implementation is asynchronous.

### Sync/Async Duality

To avoid duplicating complex logic, Reqivo uses a **Synchronous Wrapper** pattern:

1.  **Base Code**: All Protocol and Utilities code is shared (pure CPU-bound).
2.  **Native IO**: Two Transport implementations exist:
    *   `AsyncConnection`: Uses `asyncio.StreamReader/Writer`.
    *   `Connection`: Uses blocking `socket`.
3.  **Client**:
    *   `AsyncSession`: Uses `AsyncConnection` and `await`.
    *   `Session`: Uses `Connection` and blocks current thread.

*Note: Unlike other libraries wrapping async code in a hidden loop (overhead), Reqivo implements the synchronous transport layer natively with blocking sockets for maximum performance in sync contexts.*

---

## 5. 🛡️ Security & Robustness

### Error Handling
The system transforms low-level errors (`socket.timeout`, `ssl.SSLError`) into semantic Reqivo exceptions before reaching Client layer.

*   `ConnectTimeout`: Failure establishing TCP/TLS.
*   `ReadTimeout`: Failure waiting for data (TTFB or body gap).
*   `TlsError`: Certificate validation failure.

### Resource Safety
*   **Context Managers**: Using `with Session()` guarantees socket closure.
*   **Finalizers**: `ConnectionPool` attempts to clean up connections when collected by GC (best effort).
