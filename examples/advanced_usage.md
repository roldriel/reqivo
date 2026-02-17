# Advanced Usage

This guide covers advanced features and patterns for power users of Reqivo.

## Connection Pooling

Reqivo automatically manages connection pooling within sessions for optimal performance.

### How Connection Pooling Works

```python
from reqivo import Session

session = Session()

try:
    # First request opens a new connection
    response1 = session.get("https://httpbin.org/get")

    # Subsequent requests to the same host reuse the connection
    response2 = session.get("https://httpbin.org/uuid")
    response3 = session.get("https://httpbin.org/headers")

    # Connection is kept alive and reused (LIFO strategy)
finally:
    session.close()
```

### Connection Pool Benefits

- **Reduced Latency**: Avoids TCP handshake and TLS negotiation overhead
- **Resource Efficiency**: Fewer socket connections to manage
- **HTTP Keep-Alive**: Maintains persistent connections
- **Automatic Management**: No manual configuration needed

### Pool Behavior

```python
from reqivo import Session

session = Session()

try:
    # Connections to different hosts are pooled separately
    response1 = session.get("https://httpbin.org/get")      # Pool 1
    response2 = session.get("https://www.example.com/")     # Pool 2
    response3 = session.get("https://httpbin.org/uuid")     # Reuses Pool 1
finally:
    session.close()
```

## Streaming Responses

Handle response bodies in chunks without loading everything into memory at once.

### Basic Streaming

```python
from reqivo import Session

session = Session()

try:
    response = session.get("https://httpbin.org/stream-bytes/10240")

    # Read response in chunks
    for chunk in response.iter_content(chunk_size=1024):
        print(f"Received {len(chunk)} bytes")
finally:
    session.close()
```

### Downloading Files

```python
from reqivo import Session

def download_file(url: str, output_path: str):
    """Download a file in chunks."""
    session = Session()

    try:
        response = session.get(url)

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)

        print(f"Downloaded to {output_path}")

    finally:
        session.close()

# Usage
download_file(
    "https://httpbin.org/image/png",
    "downloaded_image.png",
)
```

## Custom Request Building

Build custom HTTP requests with fine-grained control.

### Custom Headers

```python
from reqivo import Session

session = Session()

try:
    headers = {
        "User-Agent": "MyCustomClient/1.0",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Request-ID": "unique-request-id-12345",
        "X-API-Version": "v2",
    }

    response = session.get(
        "https://httpbin.org/headers",
        headers=headers,
    )

    print(response.json())
finally:
    session.close()
```

### Query Parameters

```python
from reqivo import Session
from urllib.parse import urlencode

session = Session()

try:
    # Method 1: URL with query string
    response1 = session.get("https://httpbin.org/get?foo=bar&baz=qux")

    # Method 2: Build URL with params
    params = {
        "search": "python",
        "page": 1,
        "limit": 20,
    }
    url = "https://api.example.com/search?" + urlencode(params)
    response2 = session.get(url)
finally:
    session.close()
```

### Request Body Formats

```python
import json
from reqivo import Session

session = Session()

try:
    # JSON body
    data = {"name": "Alice", "age": 30}
    response1 = session.post(
        "https://httpbin.org/post",
        body=json.dumps(data),
        headers={"Content-Type": "application/json"},
    )

    # Form-encoded body
    form_data = "key1=value1&key2=value2"
    response2 = session.post(
        "https://httpbin.org/post",
        body=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    # Raw bytes body
    raw_data = b"\x00\x01\x02\x03"
    response3 = session.post(
        "https://httpbin.org/post",
        body=raw_data,
        headers={"Content-Type": "application/octet-stream"},
    )
finally:
    session.close()
```

### Streaming Uploads (Chunked Transfer Encoding)

```python
from reqivo import Session

def file_chunks(filepath: str, chunk_size: int = 8192):
    """Read a file in chunks for streaming upload."""
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk

session = Session()

try:
    # Upload a file using chunked transfer encoding
    response = session.post(
        "https://upload.example.com/files",
        body=file_chunks("large_file.bin"),
    )
    print(f"Upload status: {response.status_code}")
finally:
    session.close()
```

## WebSocket Support

Reqivo provides WebSocket support for real-time communication.

### Synchronous WebSocket

```python
from reqivo import WebSocket

# Connect to WebSocket server
ws = WebSocket("wss://echo.websocket.org/")
ws.connect()

try:
    # Send text message
    ws.send("Hello, WebSocket!")

    # Receive message
    message = ws.recv()
    print(f"Received: {message}")

    # Send binary message
    ws.send(b"\x00\x01\x02\x03")

    # Receive binary
    binary_msg = ws.recv()
    print(f"Received binary: {binary_msg}")

finally:
    ws.close()
```

### Asynchronous WebSocket

```python
import asyncio
from reqivo import AsyncWebSocket

async def websocket_example():
    ws = AsyncWebSocket("wss://echo.websocket.org/")
    await ws.connect()

    try:
        # Send message
        await ws.send("Hello from async!")

        # Receive message
        message = await ws.recv()
        print(f"Received: {message}")

    finally:
        await ws.close()

asyncio.run(websocket_example())
```

### WebSocket with Custom Headers

```python
from reqivo import WebSocket

ws = WebSocket(
    "wss://api.example.com/ws",
    headers={
        "Authorization": "Bearer your-token",
        "X-Client-ID": "client-123",
    },
)

ws.connect()

try:
    # Send authenticated message
    ws.send('{"action": "subscribe", "channel": "updates"}')

    # Receive updates
    while True:
        message = ws.recv()
        print(f"Update: {message}")

finally:
    ws.close()
```

### WebSocket with Auto-Reconnect

```python
from reqivo import Reqivo

client = Reqivo()

try:
    ws = client.websocket(
        "wss://echo.websocket.org",
        auto_reconnect=True,
        max_reconnect_attempts=5,
        reconnect_delay=1.0,
    )
    ws.connect()

    try:
        ws.send("Hello with auto-reconnect!")
        message = ws.recv()
        print(f"Received: {message}")
    finally:
        ws.close()
finally:
    client.close()
```

## Hooks (Request/Response Interceptors)

The `Reqivo` facade provides a fluent API for registering hooks:

### Pre-Request Hook

```python
from reqivo import Reqivo

def log_request(method, url, headers):
    """Log outgoing requests."""
    print(f"-> {method} {url}")
    return method, url, headers

def add_custom_header(method, url, headers):
    """Add a custom header to every request."""
    headers["X-Custom-Header"] = "my-value"
    return method, url, headers

with Reqivo(base_url="https://httpbin.org").on_request(log_request).on_request(add_custom_header) as client:
    response = client.get("/headers")
    print(response.json())
```

### Post-Response Hook

```python
from reqivo import Reqivo

def log_response(response):
    """Log incoming responses."""
    print(f"<- {response.status_code} ({len(response.body)} bytes)")
    return response

with Reqivo().on_response(log_response) as client:
    response = client.get("https://httpbin.org/get")
```

### Hooks with Session

```python
from reqivo import Session

def add_correlation_id(method, url, headers):
    """Add correlation ID to all requests."""
    import uuid
    headers["X-Correlation-ID"] = str(uuid.uuid4())
    return method, url, headers

def validate_status(response):
    """Log warning for non-2xx responses."""
    if response.status_code >= 400:
        print(f"WARNING: {response.status_code} for {response.url}")
    return response

session = Session()
session.add_pre_request_hook(add_correlation_id)
session.add_post_response_hook(validate_status)

try:
    response = session.get("https://httpbin.org/get")
    print(response.json())
finally:
    session.close()
```

## Performance Optimization

### Reuse Sessions

```python
from reqivo import Session

# Bad: Creating new session for each request
def bad_approach():
    for i in range(100):
        session = Session()
        response = session.get("https://httpbin.org/get")
        session.close()

# Good: Reuse single session
def good_approach():
    session = Session()
    try:
        for i in range(100):
            response = session.get("https://httpbin.org/get")
    finally:
        session.close()
```

### Concurrent Async Requests

```python
import asyncio
from reqivo import AsyncSession

async def optimized_concurrent_requests():
    """Efficiently make many concurrent requests."""

    urls = [f"https://httpbin.org/uuid" for _ in range(50)]

    session = AsyncSession()

    try:
        # Create all tasks
        tasks = [session.get(url) for url in urls]

        # Execute concurrently
        responses = await asyncio.gather(*tasks)

        # Process responses
        return [r.json() for r in responses]
    finally:
        await session.close()

# Execute
results = asyncio.run(optimized_concurrent_requests())
print(f"Completed {len(results)} requests")
```

### Memory-Efficient Response Processing

```python
from reqivo import Session

def process_large_response():
    """Process large response without loading into memory."""
    session = Session()

    try:
        response = session.get("https://httpbin.org/stream-bytes/1048576")  # 1 MB

        total_size = 0
        chunk_count = 0

        for chunk in response.iter_content(chunk_size=8192):
            # Process chunk immediately
            total_size += len(chunk)
            chunk_count += 1

            # Chunk is discarded after processing
            # Not accumulated in memory

        print(f"Processed {total_size} bytes in {chunk_count} chunks")

    finally:
        session.close()

process_large_response()
```

## Type Hints and Static Typing

Reqivo is fully typed with PEP 561 compliance.

### Using Type Hints

```python
from reqivo import Session, Response
from typing import Dict, Optional

def fetch_user(user_id: int) -> Optional[Dict]:
    """Fetch user data with type hints."""
    session: Session = Session()

    try:
        response: Response = session.get(f"https://api.example.com/users/{user_id}")

        if response.status_code == 200:
            return response.json()
        return None

    finally:
        session.close()

# Usage with type checking
user: Optional[Dict] = fetch_user(123)
if user:
    print(user["name"])
```

## Custom User Agents

### Simple User Agent

```python
from reqivo import Session

session = Session()
session.headers["User-Agent"] = "MyApp/1.0 (https://example.com)"

try:
    response = session.get("https://httpbin.org/user-agent")
    print(response.json())
finally:
    session.close()
```

### Detailed User Agent

```python
import platform
from reqivo import Session

def build_user_agent(app_name: str, app_version: str) -> str:
    """Build detailed user agent string."""
    python_version = platform.python_version()
    system = platform.system()
    system_version = platform.release()

    return f"{app_name}/{app_version} (Python {python_version}; {system} {system_version})"

session = Session()
session.headers["User-Agent"] = build_user_agent("MyApp", "2.0")

try:
    response = session.get("https://httpbin.org/user-agent")
    print(response.json())
finally:
    session.close()
```

## Request Timeouts

### Granular Timeout Control

```python
from reqivo import Session
from reqivo.utils.timing import Timeout

session = Session()

try:
    # Simple timeout (total time)
    response1 = session.get("https://httpbin.org/delay/2", timeout=5.0)

    # Detailed timeout control
    timeout = Timeout(
        connect=3.0,  # Connection timeout
        read=10.0,    # Read timeout
        total=15.0,   # Total timeout
    )

    response2 = session.get("https://httpbin.org/delay/2", timeout=timeout)
finally:
    session.close()
```

## Best Practices Summary

1. **Reuse Sessions**: Create one session and reuse it for multiple requests
2. **Use Async for Concurrency**: Use `AsyncSession` for concurrent requests
3. **Stream Large Responses**: Use `iter_content()` for large response bodies
4. **Set Appropriate Timeouts**: Always set timeouts to prevent hanging
5. **Handle Errors Gracefully**: Use try-except blocks with specific exceptions
6. **Close Resources**: Always close sessions with `try/finally` or use `Reqivo` with context managers
7. **Type Annotations**: Use type hints for better code quality
8. **Connection Pooling**: Let Reqivo manage connections automatically

## See Also

- [Quick Start Guide](quick_start.md)
- [Async Patterns](async_patterns.md)
- [Session Management](session_management.md)
- [Error Handling](error_handling.md)
