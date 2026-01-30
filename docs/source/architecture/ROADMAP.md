# 🗺️ Roadmap & Feature Status

> **Single Source of Truth for Reqivo's Progress and Direction**
>
> Last updated: 2026-01-29
> Current Version: 0.1.0 (Alpha)

---

## 📊 Progress Dashboard (v0.1.0)

**Overall Status**: 🟡 **Alpha** (53% complete)
The current version is a solid base but incomplete. Not suitable for critical production.

| Category | Goal v1.0 | Current | % Complete | Status |
|----------|-----------|---------|------------|--------|
| **HTTP/1.1 Core** | 15 reqs | 8 | 53% | 🟡 In Progress |
| **Session Management** | 8 reqs | 5 | 63% | 🟡 In Progress |
| **Connection Pooling** | 6 reqs | 4 | 67% | 🟡 In Progress |
| **WebSocket** | 10 reqs | 7 | 70% | 🟡 In Progress |
| **TLS/Security** | 8 reqs | 2 | 25% | 🔴 Initial |
| **Timeouts** | 4 reqs | 2 | 50% | 🟡 In Progress |
| **Streaming** | 5 reqs | 4 | 80% | 🟢 Advanced |
| **Authentication** | 6 reqs | 2 | 33% | 🔴 Initial |
| **Error Handling** | 8 reqs | 8 | 100% | ✅ Complete |
| **Testing & Quality** | 10 reqs | 4 | 40% | 🔴 Initial |
| **Observability** | 6 reqs | 0 | 0% | ⚫ Not Started |
| **Documentation** | 5 reqs | 2 | 40% | 🔴 Initial |

---

## 📍 Detailed Timeline

### ✅ v0.1.0: Baseline (WHAT WORKS NOW)
*Current released version. Verified base functionalities.*

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

### 🚧 v0.2.0: HTTP/1.1 Robustness (IN PROGRESS)
*Goal: Close fundamental gaps before adding new features.*

**Parser & Protocol**
- [ ] Duplicate headers handling (e.g., multiple `Set-Cookie`).
- [ ] Configurable size limits (headers and body) for security.
- [ ] Automatic redirects (3xx codes).
- [ ] Redirect loop detection.

**Resource Management**
- [ ] Differentiated timeouts: real `connect_timeout` vs `read_timeout`.
- [ ] Strict enforcement of Connection Pool limits (block/reject).
- [ ] Active cleanup of expired connections in the pool.
- [ ] Test coverage at 97%.

---

### 🔮 v0.3.0: Ergonomics
*Goal: Improve Developer Experience (DX).*

- [ ] **Streaming Uploads**: Send large files as iterables.
- [ ] **Hooks System**: `pre_request` and `post_response` interceptors.
- [ ] **Global Config**: `base_url`, `default_timeout` in Session.
- [ ] **WebSocket**: Auto-reconnect and frame limits.
- [ ] **Helpers**: `put`, `delete`, `patch` methods.

---

### 🔮 v0.4.0: Advanced Security
*Goal: Capabilities needed for enterprise environments.*

- [ ] **Mutual TLS (mTLS)**: Support for client certificates.
- [ ] **Certificate Pinning**: Fingerprint validation.
- [ ] **Custom SSL Context**: Allow custom SSL contexts.
- [ ] **Digest Auth**: RFC 7616 support.
- [ ] **Verification Control**: `verify=False` options or path to CA bundle.

---

### 🔮 v0.5.0: Observability & Production
*Goal: Auditing and confidence.*

- [ ] **Structured Logging**: Semantic logs with data sanitization.
- [ ] **Internal Metrics**: Counters for requests, errors, pool stats.
- [ ] **Int Mock Server**: Integrated test utilities.
- [ ] **Benchmarks**: Automated performance suite.

---

### 🔮 v1.0.0: Stable Release
*Final goal for the first major version.*

*   HTTP/2 Support (Experimental/Beta).
*   Stable and frozen API.
*   Complete Documentation (API Reference, Guides).
*   100% compliance with previous milestones.

---

## 🚫 Out of Current Roadmap
*Features explicitly NOT being developed for now.*

*   HTTP/3 (QUIC) - Requires complex dependencies.
*   Web Framework (Server) - Reqivo is only a client.
*   Brotli Compression - Requires external dependencies.
*   Python < 3.9 Support - EOL.
