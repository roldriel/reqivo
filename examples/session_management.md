# Session Management

Sessions in Reqivo provide persistent connections, cookie handling, and authentication management across multiple requests.

## Basic Session Usage

```python
import json
from reqivo import Session

# Create a session
session = Session()

try:
    # Make multiple requests using the same session
    response1 = session.get("https://httpbin.org/get")
    response2 = session.get("https://httpbin.org/uuid")
    response3 = session.post(
        "https://httpbin.org/post",
        body=json.dumps({"key": "value"}),
        headers={"Content-Type": "application/json"},
    )
finally:
    # Close when done
    session.close()
```

## Persistent Headers

Set headers that persist across all requests in the session:

```python
from reqivo import Session

session = Session()

try:
    # Set persistent headers
    session.headers["User-Agent"] = "MyApp/1.0"
    session.headers["Accept"] = "application/json"
    session.headers["X-API-Key"] = "secret-key"

    # All requests will include these headers
    response = session.get("https://httpbin.org/headers")
    print(response.json())
finally:
    session.close()
```

## Cookie Handling

Reqivo automatically handles cookies within a session:

```python
from reqivo import Session

session = Session()

try:
    # Server sets a cookie
    response1 = session.get("https://httpbin.org/cookies/set?session_id=abc123")

    # Cookie is automatically sent in subsequent requests
    response2 = session.get("https://httpbin.org/cookies")
    print(response2.json())  # Shows the session_id cookie
finally:
    session.close()
```

### Manual Cookie Management

```python
from reqivo import Session

session = Session()

try:
    # Set cookies manually
    session.cookies["session_id"] = "abc123"
    session.cookies["user_pref"] = "dark_mode"

    # Cookies are sent with requests
    response = session.get("https://httpbin.org/cookies")
    print(response.json())

    # Access cookies
    print(session.cookies)  # {'session_id': 'abc123', 'user_pref': 'dark_mode'}
finally:
    session.close()
```

## Basic Authentication

Use HTTP Basic Authentication:

```python
from reqivo import Session

session = Session()

try:
    # Set Basic Auth credentials
    session.set_basic_auth("username", "password")

    # Credentials are automatically included in requests
    response = session.get("https://httpbin.org/basic-auth/username/password")
    print(f"Status: {response.status_code}")  # 200
finally:
    session.close()
```

## Bearer Token Authentication

Use Bearer token authentication (common with APIs):

```python
from reqivo import Session

session = Session()

try:
    # Set Bearer token
    session.set_bearer_token("your-api-token-here")

    # Token is included in Authorization header
    response = session.get("https://api.example.com/protected-resource")
finally:
    session.close()
```

## Fluent Authentication with Reqivo Facade

The `Reqivo` facade provides a fluent API for authentication:

```python
from reqivo import Reqivo

# Basic auth with fluent chaining
client = Reqivo(base_url="https://api.example.com").basic_auth("user", "pass")

try:
    response = client.get("/protected")
    print(response.json())
finally:
    client.close()

# Bearer token with context manager
with Reqivo(base_url="https://api.example.com").bearer_token("my-token") as client:
    response = client.get("/data")
    print(response.json())
```

## Connection Pooling

Sessions automatically manage connection pooling for better performance:

```python
from reqivo import Session

session = Session()

try:
    # First request opens a connection
    response1 = session.get("https://httpbin.org/get")

    # Subsequent requests to the same host reuse the connection
    response2 = session.get("https://httpbin.org/uuid")
    response3 = session.get("https://httpbin.org/headers")

    # Connections are reused, avoiding TCP/TLS handshake overhead
finally:
    session.close()
```

## Async Session Management

All session features work with `AsyncSession`:

```python
import asyncio
import json
from reqivo import AsyncSession

async def main():
    session = AsyncSession()

    try:
        # Set persistent headers
        session.headers["Authorization"] = "Bearer token"

        # Set cookies
        session.cookies["session"] = "abc123"

        # Make requests
        response1 = await session.get("https://httpbin.org/get")
        response2 = await session.post(
            "https://httpbin.org/post",
            body=json.dumps({"data": 123}),
            headers={"Content-Type": "application/json"},
        )

        print(f"Cookies: {session.cookies}")
    finally:
        await session.close()

asyncio.run(main())
```

## Session Configuration

### Base URL

```python
from reqivo import Session

# All requests will be relative to the base URL
session = Session(base_url="https://api.example.com")

try:
    response = session.get("/users")       # https://api.example.com/users
    response = session.get("/users/123")   # https://api.example.com/users/123
finally:
    session.close()
```

### Custom Timeout

```python
from reqivo import Session

# Set default timeout for all requests (overridable per-request)
session = Session(default_timeout=10.0)

try:
    response = session.get("https://httpbin.org/delay/2")

    # Override timeout for a specific request
    response = session.get("https://httpbin.org/delay/2", timeout=5.0)
finally:
    session.close()
```

### Per-Request Headers

Override or add headers for specific requests:

```python
from reqivo import Session

session = Session()

try:
    # Set default headers
    session.headers["User-Agent"] = "MyApp/1.0"

    # Override for specific request
    response = session.get(
        "https://httpbin.org/headers",
        headers={"User-Agent": "SpecialBot/2.0"},
    )
finally:
    session.close()
```

## Session Lifecycle

### Using Reqivo Facade (Recommended)

```python
from reqivo import Reqivo

# Automatic cleanup with context manager
with Reqivo() as client:
    client._session.headers["API-Key"] = "secret"
    response = client.get("https://api.example.com/data")
    print(response.json())
# Client automatically closed
```

### Manual Session Lifecycle

```python
from reqivo import Session

session = Session()
try:
    response = session.get("https://httpbin.org/get")
    print(response.status_code)
finally:
    session.close()  # Always close
```

## Advanced Session Patterns

### Session Factory

```python
from reqivo import Session
from typing import Optional

def create_api_session(
    base_url: str,
    api_key: Optional[str] = None,
) -> Session:
    """Create a configured session for API access."""
    session = Session(base_url=base_url)

    # Configure session
    session.headers["Accept"] = "application/json"
    session.headers["User-Agent"] = "MyApp/1.0"

    if api_key:
        session.set_bearer_token(api_key)

    return session

# Usage
session = create_api_session("https://api.example.com", api_key="my-api-key")
try:
    response = session.get("/users")
    print(response.json())
finally:
    session.close()
```

### Session Wrapper Class

```python
import json
from reqivo import Session
from typing import Any, Dict

class ApiClient:
    """Wrapper around Session for API-specific logic."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.session = Session()
        self.session.set_bearer_token(api_key)
        self.session.headers["Content-Type"] = "application/json"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.session.close()

    def get(self, endpoint: str, **kwargs) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, **kwargs)
        return response.json()

    def post(self, endpoint: str, data: Dict, **kwargs) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = self.session.post(
            url,
            body=json.dumps(data),
            **kwargs,
        )
        return response.json()

# Usage
with ApiClient("https://api.example.com", "my-key") as client:
    users = client.get("/users")
    new_user = client.post("/users", {"name": "Alice"})
```

## Best Practices

1. **Use try/finally or Wrappers**: `Session` does not support context managers directly; use `Reqivo` for `with` support or implement your own wrapper

2. **Reuse Sessions**: Create one session and reuse it for multiple requests to the same host

3. **Set Persistent Headers**: Configure common headers once on the session

4. **Close Sessions**: Ensure sessions are closed to release resources and connections

5. **Separate Sessions**: Use different sessions for different APIs or authentication contexts

6. **Thread Safety**: Sessions are not thread-safe; create separate sessions per thread

## Performance Tips

- **Connection Pooling**: Reusing sessions enables connection pooling, reducing latency
- **Keep-Alive**: Sessions maintain persistent connections to servers
- **Authentication**: Set authentication once on the session instead of per-request
- **Headers**: Persistent headers avoid repeated configuration

## See Also

- [Quick Start Guide](quick_start.md)
- [Async Patterns](async_patterns.md)
- [Error Handling](error_handling.md)
- [Advanced Usage](advanced_usage.md)
