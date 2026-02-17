# Quick Start Guide

This guide will help you get started with Reqivo, a modern, async-first HTTP client library for Python.

## Installation

```bash
pip install reqivo
```

## Basic Synchronous Request

The simplest way to make an HTTP request with Reqivo using the `Reqivo` facade:

```python
from reqivo import Reqivo

# Create a client (supports context manager)
with Reqivo() as client:
    response = client.get("https://httpbin.org/get")

    print(f"Status: {response.status_code}")
    print(f"Body: {response.text()}")
# Client is automatically closed
```

Or using `Session` directly:

```python
from reqivo import Session

# Create a session
session = Session()

try:
    # Make a GET request
    response = session.get("https://httpbin.org/get")

    print(f"Status: {response.status_code}")
    print(f"Body: {response.text()}")
finally:
    # Close the session when done
    session.close()
```

## Basic Asynchronous Request

For async applications, use `AsyncReqivo` or `AsyncSession`:

```python
import asyncio
from reqivo import AsyncReqivo

async def main():
    # AsyncReqivo supports async context manager
    async with AsyncReqivo() as client:
        response = await client.get("https://httpbin.org/get")

        print(f"Status: {response.status_code}")
        print(f"Body: {response.text()}")

# Run the async function
asyncio.run(main())
```

Or with `AsyncSession`:

```python
import asyncio
from reqivo import AsyncSession

async def main():
    session = AsyncSession()

    try:
        response = await session.get("https://httpbin.org/get")

        print(f"Status: {response.status_code}")
        print(f"Body: {response.text()}")
    finally:
        await session.close()

asyncio.run(main())
```

## POST Request with JSON

Send JSON data with a POST request:

```python
import json
from reqivo import Reqivo

with Reqivo() as client:
    # Prepare JSON data
    data = {"name": "John Doe", "email": "john@example.com"}

    # Make a POST request with JSON body
    response = client.post(
        "https://httpbin.org/post",
        body=json.dumps(data),
        headers={"Content-Type": "application/json"},
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
```

## Adding Headers

Customize request headers:

```python
from reqivo import Session

session = Session()

try:
    # Add custom headers
    headers = {
        "User-Agent": "MyApp/1.0",
        "Accept": "application/json",
    }

    response = session.get(
        "https://httpbin.org/headers",
        headers=headers,
    )

    print(response.json())
finally:
    session.close()
```

## Using Context Managers

The `Reqivo` and `AsyncReqivo` facades support context managers for automatic cleanup:

```python
from reqivo import Reqivo

with Reqivo() as client:
    response = client.get("https://httpbin.org/get")
    print(response.status_code)
# Client is automatically closed
```

Async version:

```python
import asyncio
from reqivo import AsyncReqivo

async def main():
    async with AsyncReqivo() as client:
        response = await client.get("https://httpbin.org/get")
        print(response.status_code)
    # Client is automatically closed

asyncio.run(main())
```

## Handling Errors

Reqivo raises specific exceptions for different error conditions:

```python
from reqivo import Session
from reqivo.exceptions import NetworkError, TimeoutError

session = Session()

try:
    response = session.get(
        "https://httpbin.org/delay/10",
        timeout=5.0,  # 5 second timeout
    )
except TimeoutError:
    print("Request timed out")
except NetworkError as e:
    print(f"Network error: {e}")
finally:
    session.close()
```

## Response Methods

The `Response` object provides several methods to access response data:

```python
from reqivo import Session

session = Session()

try:
    response = session.get("https://httpbin.org/json")

    # Get response as text
    text = response.text()

    # Parse JSON response
    data = response.json()

    # Get raw bytes
    raw_bytes = response.body

    # Access headers
    content_type = response.headers.get("Content-Type")

    # Check status code
    if response.status_code == 200:
        print("Success!")
finally:
    session.close()
```

## Next Steps

- Learn about [async patterns](async_patterns.md)
- Explore [session management](session_management.md) for cookies and authentication
- Read about [error handling](error_handling.md) strategies
- Check out [advanced usage](advanced_usage.md) for connection pooling and more

## Zero Dependencies

Reqivo is built entirely on Python's standard library with zero external dependencies. This makes it lightweight, secure, and easy to deploy.
