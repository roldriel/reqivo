# Reqivo Examples

This directory contains comprehensive examples and guides for using Reqivo.

## Quick Links

- **[Quick Start Guide](quick_start.md)** - Get started with Reqivo in 5 minutes
- **[Async Patterns](async_patterns.md)** - Learn async/await patterns and concurrent requests
- **[Session Management](session_management.md)** - Cookies, authentication, and persistent connections
- **[Error Handling](error_handling.md)** - Handle errors gracefully with retry logic and fallbacks
- **[Advanced Usage](advanced_usage.md)** - Connection pooling, streaming, WebSockets, hooks, and performance tips

## What is Reqivo?

Reqivo is a modern, async-first HTTP client library for Python built entirely on the standard library with zero external dependencies.

### Key Features

- **Zero Dependencies**: Built entirely on Python's standard library
- **Async-First**: Full asyncio support with `AsyncReqivo` and `AsyncSession`
- **Type Safe**: Complete type hints for static analysis (PEP 561)
- **Connection Pooling**: Automatic connection reuse for better performance
- **WebSocket Support**: Both sync and async WebSocket clients
- **Hooks System**: Pre-request and post-response interceptors
- **Memory Optimized**: Uses `__slots__` for efficient memory usage

## Getting Started

Install Reqivo:

```bash
pip install reqivo
```

Make your first request:

```python
from reqivo import Reqivo

with Reqivo() as client:
    response = client.get("https://httpbin.org/get")
    print(response.json())
```

## Documentation Structure

### 1. Quick Start Guide

Perfect for beginners. Covers:

- Installation
- Basic GET and POST requests
- Headers and parameters
- Context managers
- Response handling

**Read it first:** [Quick Start Guide](quick_start.md)

### 2. Async Patterns

Learn how to leverage asyncio for concurrent requests:

- Basic async requests with `AsyncReqivo` and `AsyncSession`
- Concurrent requests with `asyncio.gather()`
- Error handling in async code
- Rate limiting with semaphores
- Streaming responses

**Go deeper:** [Async Patterns](async_patterns.md)

### 3. Session Management

Master persistent connections and authentication:

- Session lifecycle management
- Cookie handling
- Basic and Bearer authentication
- Fluent auth with `Reqivo` facade
- Persistent headers
- Connection pooling behavior

**Level up:** [Session Management](session_management.md)

### 4. Error Handling

Build robust applications with proper error handling:

- Exception hierarchy
- Timeout handling (connect, read, total)
- Network and TLS errors
- Retry logic with exponential backoff
- Circuit breaker pattern

**Stay resilient:** [Error Handling](error_handling.md)

### 5. Advanced Usage

Explore advanced features:

- Connection pooling internals
- Streaming uploads and downloads
- WebSocket clients (sync and async)
- Request/response hooks
- Performance optimization
- Custom request building
- Type hints and static typing

**Become an expert:** [Advanced Usage](advanced_usage.md)

## Example Index

### Basic Examples

| Topic | Location |
| ------- | ---------- |
| Simple GET request | [Quick Start](quick_start.md#basic-synchronous-request) |
| Simple POST request | [Quick Start](quick_start.md#post-request-with-json) |
| Custom headers | [Quick Start](quick_start.md#adding-headers) |
| Context managers | [Quick Start](quick_start.md#using-context-managers) |

### Async Examples

| Topic | Location |
| ------- | ---------- |
| Basic async request | [Async Patterns](async_patterns.md#basic-async-request) |
| Concurrent requests | [Async Patterns](async_patterns.md#concurrent-requests) |
| Async with error handling | [Async Patterns](async_patterns.md#concurrent-requests-with-error-handling) |
| Background tasks | [Async Patterns](async_patterns.md#using-asynciocreate_task-for-background-requests) |
| Rate limiting | [Async Patterns](async_patterns.md#rate-limiting-with-semaphores) |

### Session Examples

| Topic | Location |
| ------- | ---------- |
| Persistent headers | [Session Management](session_management.md#persistent-headers) |
| Cookie handling | [Session Management](session_management.md#cookie-handling) |
| Basic authentication | [Session Management](session_management.md#basic-authentication) |
| Bearer token auth | [Session Management](session_management.md#bearer-token-authentication) |
| Fluent auth (facade) | [Session Management](session_management.md#fluent-authentication-with-reqivo-facade) |
| Session factory | [Session Management](session_management.md#session-factory) |

### Error Handling Examples

| Topic | Location |
| ------- | ---------- |
| Timeout errors | [Error Handling](error_handling.md#timeout-errors) |
| Network errors | [Error Handling](error_handling.md#network-errors) |
| Retry with backoff | [Error Handling](error_handling.md#retry-logic) |
| Fallback endpoints | [Error Handling](error_handling.md#fallback-endpoints) |
| Circuit breaker | [Error Handling](error_handling.md#circuit-breaker-pattern) |

### Advanced Examples

| Topic | Location |
| ------- | ---------- |
| Connection pooling | [Advanced Usage](advanced_usage.md#connection-pooling) |
| Streaming responses | [Advanced Usage](advanced_usage.md#streaming-responses) |
| File downloads | [Advanced Usage](advanced_usage.md#downloading-files) |
| Streaming uploads | [Advanced Usage](advanced_usage.md#streaming-uploads-chunked-transfer-encoding) |
| WebSocket (sync) | [Advanced Usage](advanced_usage.md#synchronous-websocket) |
| WebSocket (async) | [Advanced Usage](advanced_usage.md#asynchronous-websocket) |
| Hooks | [Advanced Usage](advanced_usage.md#hooks-requestresponse-interceptors) |

## Running Examples

All examples are self-contained and can be run directly:

```python
# Save an example to a file
# example.py

from reqivo import Reqivo

with Reqivo() as client:
    response = client.get("https://httpbin.org/get")
    print(response.json())
```

```bash
# Run the example
python example.py
```

## Requirements

- Python 3.9 or higher
- No external dependencies required

## Support

- **Documentation**: <https://roldriel.github.io/reqivo/>
- **Repository**: <https://github.com/roldriel/reqivo>
- **Issues**: <https://github.com/roldriel/reqivo/issues>

## License

Reqivo is released under the MIT License.
