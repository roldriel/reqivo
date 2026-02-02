# Advanced Usage

This guide covers advanced features and patterns for power users of Reqivo.

## Connection Pooling

Reqivo automatically manages connection pooling within sessions for optimal performance.

### How Connection Pooling Works

```python
from reqivo import Session

session = Session()

# First request opens a new connection
response1 = session.get("https://httpbin.org/get")

# Subsequent requests to the same host reuse the connection
response2 = session.get("https://httpbin.org/uuid")
response3 = session.get("https://httpbin.org/headers")

# Connection is kept alive and reused (LIFO strategy)
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

# Connections to different hosts are pooled separately
response1 = session.get("https://httpbin.org/get")      # Pool 1
response2 = session.get("https://www.example.com/")     # Pool 2
response3 = session.get("https://httpbin.org/uuid")     # Reuses Pool 1

session.close()
```

## Streaming Large Responses

Handle large responses efficiently without loading everything into memory.

### Basic Streaming

```python
from reqivo import Session

session = Session()

response = session.get(
    "https://httpbin.org/stream-bytes/10240",
    stream=True
)

# Read response in chunks
chunk_size = 1024
for chunk in response.iter_content(chunk_size=chunk_size):
    # Process chunk
    print(f"Received {len(chunk)} bytes")

session.close()
```

### Downloading Files

```python
from reqivo import Session

def download_file(url: str, output_path: str):
    """Download a file in chunks"""
    session = Session()

    try:
        response = session.get(url, stream=True)

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
    "downloaded_image.png"
)
```

### Async Streaming

```python
import asyncio
from reqivo import AsyncSession

async def stream_large_file():
    async with AsyncSession() as session:
        response = await session.get(
            "https://httpbin.org/stream-bytes/102400",
            stream=True
        )

        total_bytes = 0
        async for chunk in response.iter_content(chunk_size=8192):
            total_bytes += len(chunk)
            print(f"Downloaded {total_bytes} bytes so far...")

        print(f"Total downloaded: {total_bytes} bytes")

asyncio.run(stream_large_file())
```

## Custom Request Building

Build custom HTTP requests with fine-grained control.

### Custom Headers

```python
from reqivo import Session

session = Session()

headers = {
    "User-Agent": "MyCustomClient/1.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Request-ID": "unique-request-id-12345",
    "X-API-Version": "v2",
}

response = session.get(
    "https://httpbin.org/headers",
    headers=headers
)

print(response.json())
session.close()
```

### Query Parameters

```python
from reqivo import Session

session = Session()

# Method 1: URL with query string
response1 = session.get("https://httpbin.org/get?foo=bar&baz=qux")

# Method 2: Build URL with params
params = {
    "search": "python",
    "page": 1,
    "limit": 20,
}

# Manually build URL
from urllib.parse import urlencode
url = "https://api.example.com/search?" + urlencode(params)
response2 = session.get(url)

session.close()
```

### Request Body Formats

```python
from reqivo import Session
import json

session = Session()

# JSON body
data = {"name": "Alice", "age": 30}
response1 = session.post(
    "https://httpbin.org/post",
    json=data
)

# Form-encoded body
form_data = "key1=value1&key2=value2"
response2 = session.post(
    "https://httpbin.org/post",
    body=form_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)

# Raw bytes body
raw_data = b"\x00\x01\x02\x03"
response3 = session.post(
    "https://httpbin.org/post",
    body=raw_data,
    headers={"Content-Type": "application/octet-stream"}
)

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
    ws.send_text("Hello, WebSocket!")

    # Receive message
    message = ws.receive()
    print(f"Received: {message}")

    # Send binary message
    ws.send_binary(b"\x00\x01\x02\x03")

    # Receive binary
    binary_msg = ws.receive()
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
        await ws.send_text("Hello from async!")

        # Receive message
        message = await ws.receive()
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
    }
)

ws.connect()

try:
    # Send authenticated message
    ws.send_text('{"action": "subscribe", "channel": "updates"}')

    # Receive updates
    while True:
        message = ws.receive()
        if message is None:
            break
        print(f"Update: {message}")

finally:
    ws.close()
```

## Performance Optimization

### Reuse Sessions

```python
from reqivo import Session

# ❌ Bad: Creating new session for each request
def bad_approach():
    for i in range(100):
        session = Session()
        response = session.get("https://httpbin.org/get")
        session.close()

# ✅ Good: Reuse single session
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
    """Efficiently make many concurrent requests"""

    urls = [f"https://httpbin.org/uuid" for _ in range(50)]

    async with AsyncSession() as session:
        # Create all tasks
        tasks = [session.get(url) for url in urls]

        # Execute concurrently
        responses = await asyncio.gather(*tasks)

        # Process responses
        return [r.json() for r in responses]

# Execute
results = asyncio.run(optimized_concurrent_requests())
print(f"Completed {len(results)} requests")
```

### Memory-Efficient Streaming

```python
from reqivo import Session

def process_large_response():
    """Process large response without loading into memory"""
    session = Session()

    try:
        response = session.get(
            "https://httpbin.org/stream-bytes/1048576",  # 1 MB
            stream=True
        )

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

def fetch_user(user_id: int) -> Optional[Dict[str, any]]:
    """Fetch user data with type hints"""
    session: Session = Session()

    try:
        response: Response = session.get(f"https://api.example.com/users/{user_id}")

        if response.status_code == 200:
            return response.json()
        return None

    finally:
        session.close()

# Usage with type checking
user: Optional[Dict[str, any]] = fetch_user(123)
if user:
    print(user["name"])
```

### Generic Session Wrapper

```python
from reqivo import Session, Response
from typing import TypeVar, Generic, Optional

T = TypeVar('T')

class ApiClient(Generic[T]):
    """Type-safe API client"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = Session()

    def get(self, endpoint: str) -> Response:
        url = f"{self.base_url}{endpoint}"
        return self.session.get(url)

    def close(self) -> None:
        self.session.close()

# Usage with type checking
client = ApiClient[dict]("https://api.example.com")
response = client.get("/users/123")
client.close()
```

## Custom User Agents

### Simple User Agent

```python
from reqivo import Session

session = Session()
session.headers["User-Agent"] = "MyApp/1.0 (https://example.com)"

response = session.get("https://httpbin.org/user-agent")
print(response.json())

session.close()
```

### Detailed User Agent

```python
from reqivo import Session
import platform

def build_user_agent(app_name: str, app_version: str) -> str:
    """Build detailed user agent string"""
    python_version = platform.python_version()
    system = platform.system()
    system_version = platform.release()

    return f"{app_name}/{app_version} (Python {python_version}; {system} {system_version})"

session = Session()
session.headers["User-Agent"] = build_user_agent("MyApp", "2.0")

response = session.get("https://httpbin.org/user-agent")
print(response.json())

session.close()
```

## Request Timeouts

### Granular Timeout Control

```python
from reqivo import Session
from reqivo.utils.timing import Timeout

session = Session()

# Simple timeout (total time)
response1 = session.get("https://httpbin.org/delay/2", timeout=5.0)

# Detailed timeout control
timeout = Timeout(
    connect=3.0,  # Connection timeout
    read=10.0,    # Read timeout
    total=15.0    # Total timeout
)

response2 = session.get("https://httpbin.org/delay/2", timeout=timeout)

session.close()
```

## Best Practices Summary

1. **Reuse Sessions**: Create one session and reuse it for multiple requests
2. **Use Async for Concurrency**: Use `AsyncSession` for concurrent requests
3. **Stream Large Responses**: Don't load large responses entirely into memory
4. **Set Appropriate Timeouts**: Always set timeouts to prevent hanging
5. **Handle Errors Gracefully**: Use try-except blocks with specific exceptions
6. **Close Resources**: Always close sessions, use context managers
7. **Type Annotations**: Use type hints for better code quality
8. **Connection Pooling**: Let Reqivo manage connections automatically

## See Also

- [Quick Start Guide](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md)
- [Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md)
- [Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md)
- [Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md)
