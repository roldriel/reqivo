# Quick Start Guide

This guide will help you get started with Reqivo, a modern, async-first HTTP client library for Python.

## Installation

```bash
pip install reqivo
```

## Basic Synchronous Request

The simplest way to make an HTTP request with Reqivo:

```python
from reqivo import Session

# Create a session
session = Session()

# Make a GET request
response = session.get("https://httpbin.org/get")

print(f"Status: {response.status_code}")
print(f"Body: {response.text()}")

# Close the session when done
session.close()
```

## Basic Asynchronous Request

For async applications, use `AsyncSession`:

```python
import asyncio
from reqivo import AsyncSession

async def main():
    # Create an async session
    session = AsyncSession()

    # Make an async GET request
    response = await session.get("https://httpbin.org/get")

    print(f"Status: {response.status_code}")
    print(f"Body: {response.text()}")

    # Close the session when done
    await session.close()

# Run the async function
asyncio.run(main())
```

## POST Request with JSON

Send JSON data with a POST request:

```python
from reqivo import Session

session = Session()

# Prepare JSON data
data = {"name": "John Doe", "email": "john@example.com"}

# Make a POST request
response = session.post(
    "https://httpbin.org/post",
    json=data
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

session.close()
```

## Adding Headers

Customize request headers:

```python
from reqivo import Session

session = Session()

# Add custom headers
headers = {
    "User-Agent": "MyApp/1.0",
    "Accept": "application/json"
}

response = session.get(
    "https://httpbin.org/headers",
    headers=headers
)

print(response.json())

session.close()
```

## Using Context Managers

Reqivo sessions support context managers for automatic cleanup:

```python
from reqivo import Session

with Session() as session:
    response = session.get("https://httpbin.org/get")
    print(response.status_code)
# Session is automatically closed
```

Async version:

```python
import asyncio
from reqivo import AsyncSession

async def main():
    async with AsyncSession() as session:
        response = await session.get("https://httpbin.org/get")
        print(response.status_code)
    # Session is automatically closed

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
        timeout=5.0  # 5 second timeout
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

session.close()
```

## Next Steps

- Learn about [async patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md)
- Explore [session management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md) for cookies and authentication
- Read about [error handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md) strategies
- Check out [advanced usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md) for connection pooling and more

## Zero Dependencies

Reqivo is built entirely on Python's standard library with zero external dependencies. This makes it lightweight, secure, and easy to deploy.
