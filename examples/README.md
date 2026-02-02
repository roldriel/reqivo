# Reqivo Examples

This directory contains comprehensive examples and guides for using Reqivo.

## Quick Links

- **[Quick Start Guide](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md)** - Get started with Reqivo in 5 minutes
- **[Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md)** - Learn async/await patterns and concurrent requests
- **[Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md)** - Cookies, authentication, and persistent connections
- **[Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md)** - Handle errors gracefully with retry logic and fallbacks
- **[Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md)** - Connection pooling, streaming, WebSockets, and performance tips

## What is Reqivo?

Reqivo is a modern, async-first HTTP client library for Python built entirely on the standard library with zero external dependencies.

### Key Features

- **Zero Dependencies**: Built entirely on Python's standard library
- **Async-First**: Full asyncio support with `AsyncSession` and `AsyncRequest`
- **Type Safe**: Complete type hints for static analysis (PEP 561)
- **Connection Pooling**: Automatic connection reuse for better performance
- **WebSocket Support**: Both sync and async WebSocket clients
- **Memory Optimized**: Uses `__slots__` for efficient memory usage

## Getting Started

Install Reqivo:

```bash
pip install reqivo
```

Make your first request:

```python
from reqivo import Session

with Session() as session:
    response = session.get("https://httpbin.org/get")
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

**Read it first:** [Quick Start Guide](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md)

### 2. Async Patterns

Learn how to leverage asyncio for concurrent requests:
- Basic async requests with `AsyncSession`
- Concurrent requests with `asyncio.gather()`
- Error handling in async code
- Rate limiting with semaphores
- Streaming responses asynchronously

**Go deeper:** [Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md)

### 3. Session Management

Master persistent connections and authentication:
- Session lifecycle management
- Cookie handling
- Basic and Bearer authentication
- Persistent headers
- Connection pooling behavior

**Level up:** [Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md)

### 4. Error Handling

Build robust applications with proper error handling:
- Exception hierarchy
- Timeout handling (connect, read, total)
- Network and TLS errors
- Retry logic with exponential backoff
- Circuit breaker pattern

**Stay resilient:** [Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md)

### 5. Advanced Usage

Explore advanced features:
- Connection pooling internals
- Streaming large files
- WebSocket clients (sync and async)
- Performance optimization
- Custom request building
- Type hints and static typing

**Become an expert:** [Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md)

## Example Index

### Basic Examples

| Topic | Location |
|-------|----------|
| Simple GET request | [Quick Start](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md#basic-synchronous-request) |
| Simple POST request | [Quick Start](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md#post-request-with-json) |
| Custom headers | [Quick Start](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md#adding-headers) |
| Context managers | [Quick Start](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md#using-context-managers) |

### Async Examples

| Topic | Location |
|-------|----------|
| Basic async request | [Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md#basic-async-request) |
| Concurrent requests | [Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md#concurrent-requests) |
| Async with error handling | [Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md#concurrent-requests-with-error-handling) |
| Background tasks | [Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md#using-asynciocreate_task-for-background-requests) |
| Rate limiting | [Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md#rate-limiting-with-semaphores) |

### Session Examples

| Topic | Location |
|-------|----------|
| Persistent headers | [Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md#persistent-headers) |
| Cookie handling | [Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md#cookie-handling) |
| Basic authentication | [Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md#basic-authentication) |
| Bearer token auth | [Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md#bearer-token-authentication) |
| Session factory | [Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md#session-factory) |

### Error Handling Examples

| Topic | Location |
|-------|----------|
| Timeout errors | [Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md#timeout-errors) |
| Network errors | [Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md#network-errors) |
| Retry with backoff | [Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md#retry-logic) |
| Fallback endpoints | [Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md#fallback-endpoints) |
| Circuit breaker | [Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md#circuit-breaker-pattern) |

### Advanced Examples

| Topic | Location |
|-------|----------|
| Connection pooling | [Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md#connection-pooling) |
| Streaming responses | [Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md#streaming-large-responses) |
| File downloads | [Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md#downloading-files) |
| WebSocket (sync) | [Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md#synchronous-websocket) |
| WebSocket (async) | [Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md#asynchronous-websocket) |

## Running Examples

All examples are self-contained and can be run directly:

```python
# Save an example to a file
# example.py

from reqivo import Session

with Session() as session:
    response = session.get("https://httpbin.org/get")
    print(response.json())
```

```bash
# Run the example
python example.py
```

## Requirements

- Python 3.9 or higher
- No external dependencies required

## Contributing Examples

Have a useful example? We'd love to include it! Please:

1. Ensure code is well-documented
2. Include error handling
3. Use type hints
4. Follow the existing format
5. Test your example

## Support

- **Documentation**: https://roldriel.github.io/reqivo/
- **Repository**: https://github.com/roldriel/reqivo
- **Issues**: https://github.com/roldriel/reqivo/issues

## License

Reqivo is released under the MIT License.
