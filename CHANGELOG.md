# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-02-15

### Added

- **Unified Facade**: `Reqivo` and `AsyncReqivo` classes as single entry points with fluent API, method chaining for auth and hooks, and WebSocket factory
- **HTTP Method Helpers**: `put()`, `delete()`, `patch()`, `head()`, `options()` methods in Session, AsyncSession, Request, and AsyncRequest
- **Global Config**: `base_url` and `default_timeout` parameters in Session and AsyncSession constructors
- **Hooks System**: `pre_request` and `post_response` interceptors via `add_pre_request_hook()` and `add_post_response_hook()` with sync/async support
- **Streaming Uploads**: Chunked transfer encoding for `Iterator[bytes]`, `AsyncIterator[bytes]`, and `IO[bytes]` body types via `iter_write_chunked()` and `async_iter_write_chunked()`
- **WebSocket Auto-Reconnect**: Automatic reconnection with exponential backoff (`auto_reconnect`, `max_reconnect_attempts`, `reconnect_delay` parameters)
- **WebSocket Configurable Frame Limits**: `max_frame_size` parameter in WebSocket and AsyncWebSocket constructors
- **WebSocketError Exception**: `WebSocketError` moved to `exceptions.py` under `ReqivoError` hierarchy

### Changed

- **Session Refactoring**: Extracted `_request()` in sync `Session` to eliminate code duplication across HTTP methods
- **Session Constructor**: `limits` parameter changed from positional to keyword-only in both Session and AsyncSession
- **User-Agent**: Updated from `reqivo/0.1` to `reqivo/0.3`
- **Body Type**: Expanded body parameter type to accept `Iterator[bytes]`, `AsyncIterator[bytes]`, and `IO[bytes]` in addition to `str` and `bytes`

## [0.2.0] - 2026-02-01

### Added

- Duplicate headers handling (e.g., multiple `Set-Cookie`)
- Configurable size limits for headers and body (`max_header_size`, `max_field_count`, `max_body_size`)
- Automatic HTTP redirects (301, 302, 303, 307, 308) with `RedirectLoopError` detection
- Differentiated timeouts: `connect_timeout`, `read_timeout`, `total`
- Semaphore-based connection pool limit enforcement
- Active cleanup of expired connections (`_cleanup_expired`, `max_idle_time`)
- `__slots__` on all core classes for ~40% memory reduction
- Comprehensive benchmark suite with comparison, microbenchmarks, memory, and profiling scripts
- Enhanced documentation with examples directory (quick_start, advanced_patterns, async_usage)
- Strict mypy type checking configuration
- py.typed marker for PEP 561 compliance
- Integration and all test environments in tox.ini
- Professional project configuration files (.editorconfig, MANIFEST.in, git commit template)
- TLS 1.2 minimum version enforcement on all SSL contexts
- Pinned development dependency versions for reproducible builds

### Changed

- Increased coverage threshold from 80% to 97%
- Enhanced pylint configuration with design rules
- Improved tox.ini with additional test environments

## [0.1.0] - 2026-01-21

### Added

- Initial release of Reqivo
- Async/await support with AsyncSession and AsyncRequest
- HTTP/1.1 support with GET and POST methods
- WebSocket support (sync and async)
- Connection pooling
- Basic type hints
- Unit tests for core functionality

### Project Goals

- Modern, async-first design
- Zero-dependency HTTP client (using only standard library)
- High performance and memory efficiency
- Production-ready quality standards
