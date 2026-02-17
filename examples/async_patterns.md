# Async Patterns with Reqivo

Reqivo is async-first, providing full support for `asyncio` with `AsyncReqivo` and `AsyncSession`.

## Basic Async Request

```python
import asyncio
from reqivo import AsyncReqivo

async def fetch_data():
    async with AsyncReqivo() as client:
        response = await client.get("https://httpbin.org/get")
        return response.json()

# Run the async function
data = asyncio.run(fetch_data())
print(data)
```

## Concurrent Requests

Make multiple requests concurrently using `asyncio.gather()`:

```python
import asyncio
from reqivo import AsyncSession

async def fetch_multiple():
    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/uuid",
        "https://httpbin.org/json",
    ]

    session = AsyncSession()

    try:
        # Create tasks for all requests
        tasks = [session.get(url) for url in urls]

        # Execute concurrently
        responses = await asyncio.gather(*tasks)

        # Process responses
        for url, response in zip(urls, responses):
            print(f"{url}: Status {response.status_code}")

        return responses
    finally:
        await session.close()

asyncio.run(fetch_multiple())
```

## Concurrent Requests with Error Handling

Handle errors gracefully when making concurrent requests:

```python
import asyncio
from reqivo import AsyncSession
from reqivo.exceptions import RequestError

async def fetch_with_error_handling():
    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/404",  # Will return 404
        "https://httpbin.org/delay/10",    # May timeout
    ]

    session = AsyncSession()

    try:
        tasks = []
        for url in urls:
            task = session.get(url, timeout=5.0)
            tasks.append(task)

        # Gather with return_exceptions=True to continue on errors
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                print(f"{url}: Error - {result}")
            else:
                print(f"{url}: Success - Status {result.status_code}")
    finally:
        await session.close()

asyncio.run(fetch_with_error_handling())
```

## Async POST Requests

Send POST requests asynchronously:

```python
import asyncio
import json
from reqivo import AsyncReqivo

async def post_data():
    data = {
        "username": "alice",
        "email": "alice@example.com",
    }

    async with AsyncReqivo() as client:
        response = await client.post(
            "https://httpbin.org/post",
            body=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")

asyncio.run(post_data())
```

## Using asyncio.create_task() for Background Requests

Execute requests in the background while doing other work:

```python
import asyncio
from reqivo import AsyncSession

async def background_fetch(session, url):
    """Fetch URL in background."""
    response = await session.get(url)
    return response.json()

async def main():
    session = AsyncSession()

    try:
        # Start background task
        task = asyncio.create_task(
            background_fetch(session, "https://httpbin.org/delay/2")
        )

        # Do other work while waiting
        print("Doing other work...")
        await asyncio.sleep(1)
        print("Still doing other work...")

        # Wait for background task to complete
        result = await task
        print(f"Background task completed: {result}")
    finally:
        await session.close()

asyncio.run(main())
```

## Async Context Manager Pattern

Use async context managers for resource cleanup:

```python
import asyncio
import json
from reqivo import AsyncSession

class ApiClient:
    """Example API client using AsyncSession."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = AsyncSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_user(self, user_id: int):
        response = await self.session.get(f"{self.base_url}/users/{user_id}")
        return response.json()

    async def create_user(self, data: dict):
        response = await self.session.post(
            f"{self.base_url}/users",
            body=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        return response.json()

# Usage
async def main():
    async with ApiClient("https://api.example.com") as client:
        user = await client.get_user(123)
        print(user)

asyncio.run(main())
```

## Rate Limiting with Semaphores

Control concurrency with asyncio.Semaphore:

```python
import asyncio
from reqivo import AsyncSession

async def fetch_with_semaphore(session, url, semaphore):
    """Fetch URL with semaphore-controlled concurrency."""
    async with semaphore:
        response = await session.get(url)
        return response.status_code

async def rate_limited_requests():
    urls = [f"https://httpbin.org/uuid" for _ in range(20)]

    # Allow maximum 5 concurrent requests
    semaphore = asyncio.Semaphore(5)

    session = AsyncSession()

    try:
        tasks = [
            fetch_with_semaphore(session, url, semaphore)
            for url in urls
        ]

        results = await asyncio.gather(*tasks)
        print(f"Completed {len(results)} requests")
    finally:
        await session.close()

asyncio.run(rate_limited_requests())
```

## Streaming Responses

Process response bodies in chunks:

```python
import asyncio
from reqivo import Session

def stream_response():
    session = Session()

    try:
        response = session.get("https://httpbin.org/stream-bytes/1024")

        # Process chunks as they arrive
        for chunk in response.iter_content(chunk_size=256):
            print(f"Received chunk of {len(chunk)} bytes")
    finally:
        session.close()

stream_response()
```

## Timeout Patterns

Different timeout strategies for async requests:

```python
import asyncio
from reqivo import AsyncSession
from reqivo.exceptions import TimeoutError

async def timeout_patterns():
    session = AsyncSession()

    try:
        # Simple timeout
        try:
            response = await session.get(
                "https://httpbin.org/delay/5",
                timeout=3.0,
            )
        except TimeoutError:
            print("Request timed out")

        # Timeout with asyncio.wait_for
        try:
            response = await asyncio.wait_for(
                session.get("https://httpbin.org/delay/5"),
                timeout=3.0,
            )
        except asyncio.TimeoutError:
            print("Request timed out (asyncio)")
    finally:
        await session.close()

asyncio.run(timeout_patterns())
```

## Best Practices

1. **Reuse Sessions**: Create one `AsyncSession` and reuse it for multiple requests to benefit from connection pooling

2. **Use Facades for Simplicity**: Use `AsyncReqivo` with `async with` for automatic cleanup, or `AsyncSession` with `try/finally`

3. **Handle Exceptions**: Wrap async requests in try-except blocks or use `return_exceptions=True` with `gather()`

4. **Limit Concurrency**: Use semaphores to prevent overwhelming servers or exhausting resources

5. **Set Timeouts**: Always set appropriate timeouts to prevent hanging requests

6. **Close Sessions**: Ensure sessions are properly closed, either with context managers (`AsyncReqivo`) or explicit `await session.close()`

## Performance Tips

- Use `asyncio.gather()` for truly concurrent requests
- Reuse `AsyncSession` instances for connection pooling
- Set appropriate timeouts to fail fast
- Use semaphores to control concurrency
- Stream large responses instead of loading into memory

## See Also

- [Quick Start Guide](quick_start.md)
- [Session Management](session_management.md)
- [Error Handling](error_handling.md)
- [Advanced Usage](advanced_usage.md)
