# Roadmap & Feature Status

> **Single Source of Truth for Reqivo's Progress and Direction**
>
> Last updated: 2026-02-16
> Current Version: 0.3.0 (Alpha)

---

## Progress Dashboard (v0.3.0)

**Overall Status**: **Alpha** (75% complete)
v0.3.0 is feature-complete. DX ergonomics added: HTTP method helpers, global config, hooks, streaming uploads, WebSocket auto-reconnect, and unified facade.

| Category               | Goal v1.0 | Current | % Complete | Status      |
|------------------------|-----------|---------|------------|-------------|
| **HTTP/1.1 Core**      | 15 reqs   | 15      | 100%       | Complete    |
| **Session Management** | 8 reqs    | 8       | 100%       | Complete    |
| **Connection Pooling** | 6 reqs    | 6       | 100%       | Complete    |
| **WebSocket**          | 10 reqs   | 9       | 90%        | Advanced    |
| **TLS/Security**       | 8 reqs    | 2       | 25%        | Initial     |
| **Timeouts**           | 4 reqs    | 4       | 100%       | Complete    |
| **Streaming**          | 5 reqs    | 5       | 100%       | Complete    |
| **Authentication**     | 6 reqs    | 2       | 33%        | Initial     |
| **Error Handling**     | 8 reqs    | 8       | 100%       | Complete    |
| **Testing & Quality**  | 10 reqs   | 8       | 80%        | Advanced    |
| **Observability**      | 6 reqs    | 0       | 0%         | Not Started |
| **Documentation**      | 5 reqs    | 2       | 40%        | Initial     |

---

## Detailed Timeline

### v0.1.0: Baseline (COMPLETE)

*Verified base functionalities.*

**Core HTTP & Session**

- [x] Basic GET and POST requests.
- [x] Custom headers and body (str/bytes).
- [x] Response parsing (status, case-insensitive headers, body).
- [x] Chunked transfer encoding support.
- [x] Session with automatic Cookies handling.
- [x] Persistent headers in Session.

**Transport & Async**

- [x] LIFO Connection Pooling per host.
- [x] Dual Architecture: Native Async + Sync wrappers.
- [x] Default TLS (using `ssl.create_default_context`).
- [x] Basic dead connection detection (`is_usable`).

**Special Features**

- [x] WebSocket Client RFC 6455 (handshake, text/binary frames, masking).
- [x] Response Streaming (`iter_content`, `iter_lines`).
- [x] Complete Exception Hierarchy (`ReqivoError`, `ConnectTimeout`, etc.).

---

### v0.2.0: HTTP/1.1 Robustness (COMPLETE)

*All fundamental gaps closed.*

**Parser & Protocol**

- [x] Duplicate headers handling (e.g., multiple `Set-Cookie`). — `headers.py`, `http11.py`
- [x] Configurable size limits (headers and body). — `http11.py` (`max_header_size`, `max_field_count`, `max_body_size`)
- [x] Automatic redirects (301, 302, 303, 307, 308). — `request.py`
- [x] Redirect loop detection (`RedirectLoopError`). — `request.py`, `exceptions.py`

**Resource Management**

- [x] Differentiated timeouts: `connect_timeout`, `read_timeout`, `total`. — `timing.py`, `connection.py`
- [x] Strict enforcement of Connection Pool limits (Semaphore-based blocking). — `connection_pool.py`
- [x] Active cleanup of expired connections (`_cleanup_expired`, `max_idle_time`). — `connection_pool.py`
- [x] Test coverage at 97% (`fail_under = 97`). — `pyproject.toml`

---

### v0.3.0: Ergonomics (COMPLETE)

*Goal: Improve Developer Experience (DX).*

- [x] **HTTP Method Helpers**: `put`, `delete`, `patch`, `head`, `options` methods in Session, AsyncSession, Request, AsyncRequest.
- [x] **Global Config**: `base_url`, `default_timeout` in Session and AsyncSession.
- [x] **Session Refactoring**: Extracted `_request()` in sync Session to eliminate code duplication.
- [x] **Hooks System**: `pre_request` and `post_response` interceptors with sync/async support.
- [x] **Streaming Uploads**: Chunked transfer encoding for iterables and file-like objects.
- [x] **WebSocket**: Auto-reconnect with exponential backoff and configurable frame limits.
- [x] **WebSocket Error Hierarchy**: `WebSocketError` moved to `exceptions.py` under `ReqivoError`.
- [x] **Unified Facade**: `Reqivo` and `AsyncReqivo` classes as single entry points with fluent API.

---

### v0.4.0: Advanced Security

*Goal: Capabilities needed for enterprise environments.*

- [ ] **Mutual TLS (mTLS)**: Support for client certificates.
- [ ] **Certificate Pinning**: Fingerprint validation.
- [ ] **Custom SSL Context**: Allow custom SSL contexts.
- [ ] **Digest Auth**: RFC 7616 support.
- [ ] **Verification Control**: `verify=False` options or path to CA bundle.

---

### v0.5.0: Observability & Production

*Goal: Auditing and confidence.*

- [ ] **Structured Logging**: Semantic logs with data sanitization.
- [ ] **Internal Metrics**: Counters for requests, errors, pool stats.
- [ ] **Int Mock Server**: Integrated test utilities.
- [ ] **Benchmarks**: Automated performance suite.

---

### v1.0.0: Stable Release

*Final goal for the first major version.*

- [ ] HTTP/2 Support (Experimental/Beta).
- [ ] Stable and frozen API.
- [ ] Complete Documentation (API Reference, Guides).
- [ ] 100% compliance with previous milestones.

---

## Out of Current Roadmap

*Features explicitly NOT being developed for now.*

- HTTP/3 (QUIC) - Requires complex dependencies.
- Web Framework (Server) - Reqivo is only a client.
- Brotli Compression - Requires external dependencies.
- Python < 3.9 Support - EOL.
