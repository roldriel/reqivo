# ADR-002: Async-First Architecture

**Status**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

## Context

Python is evolving toward async/await as the dominant pattern for I/O:
- FastAPI, Starlette, Quart are async-first
- Concurrency improves performance in I/O-bound operations
- asyncio has been part of stdlib since Python 3.4

Design options:
1. **Sync-first** (like `requests`): Primary synchronous API
2. **Async-only** (like `aiohttp`): Only async, no sync
3. **Async-first**: Async primary, sync as wrapper

## Decision

**Reqivo will be async-first**: The primary API will be async, with synchronous wrappers.

Structure:
```text
# Primary classes (async)
AsyncSession
AsyncRequest
AsyncConnection
AsyncConnectionPool
AsyncWebSocket

# Secondary classes (sync wrappers)
Session       → uses AsyncSession with asyncio.run()
Request       → uses AsyncRequest with asyncio.run()
Connection    → uses AsyncConnection with asyncio.run()
ConnectionPool → uses AsyncConnectionPool with threading.Lock
WebSocket     → uses AsyncWebSocket with asyncio.run()
```

**Shared code**:
- HTTP parsing is the same for async and sync
- Protocol layer is stateless and reusable
- Only the I/O layer changes (socket vs asyncio)

## Consequences

#### Positive ✅

1. **Performance**: Async allows better concurrency
2. **Modern**: Follows Python ecosystem trend
3. **Scalable**: Efficient handling of many simultaneous connections
4. **Compatibility**: Sync API available for legacy code
5. **Single implementation**: Shared protocol code

#### Negative ❌

1. **Complexity**: Maintaining two APIs (sync and async)
2. **Learning curve**: Async is harder for beginners
3. **Debugging**: Async debugging is more complex
4. **Overhead**: Sync wrapper has `asyncio.run()` overhead

#### Mitigations

- **Clear documentation**: Examples of both usages
- **Sensible defaults**: Simple and straightforward sync API
- **Dual testing**: Tests for both sync and async paths

## Alternatives Considered

1. **Sync-only**: Rejected. Doesn't leverage modern concurrency.
2. **Async-only**: Rejected. Excludes sync users.
3. **Sync-first**: Rejected. Async wrapper over sync is inefficient.

## References

- PEP 492: Coroutines with async/await
- asyncio documentation
