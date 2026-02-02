# Session Management

Sessions in Reqivo provide persistent connections, cookie handling, and authentication management across multiple requests.

## Basic Session Usage

```python
from reqivo import Session

# Create a session
session = Session()

# Make multiple requests using the same session
response1 = session.get("https://httpbin.org/get")
response2 = session.get("https://httpbin.org/uuid")
response3 = session.post("https://httpbin.org/post", json={"key": "value"})

# Close when done
session.close()
```

## Persistent Headers

Set headers that persist across all requests in the session:

```python
from reqivo import Session

session = Session()

# Set persistent headers
session.headers["User-Agent"] = "MyApp/1.0"
session.headers["Accept"] = "application/json"
session.headers["X-API-Key"] = "secret-key"

# All requests will include these headers
response = session.get("https://httpbin.org/headers")
print(response.json())

session.close()
```

## Cookie Handling

Reqivo automatically handles cookies within a session:

```python
from reqivo import Session

session = Session()

# Server sets a cookie
response1 = session.get("https://httpbin.org/cookies/set?session_id=abc123")

# Cookie is automatically sent in subsequent requests
response2 = session.get("https://httpbin.org/cookies")
print(response2.json())  # Shows the session_id cookie

session.close()
```

### Manual Cookie Management

```python
from reqivo import Session

session = Session()

# Set cookies manually
session.cookies["session_id"] = "abc123"
session.cookies["user_pref"] = "dark_mode"

# Cookies are sent with requests
response = session.get("https://httpbin.org/cookies")
print(response.json())

# Access cookies
print(session.cookies)  # {'session_id': 'abc123', 'user_pref': 'dark_mode'}

session.close()
```

## Basic Authentication

Use HTTP Basic Authentication:

```python
from reqivo import Session

session = Session()

# Set Basic Auth credentials
session.set_basic_auth("username", "password")

# Credentials are automatically included in requests
response = session.get("https://httpbin.org/basic-auth/username/password")
print(f"Status: {response.status_code}")  # 200

session.close()
```

## Bearer Token Authentication

Use Bearer token authentication (common with APIs):

```python
from reqivo import Session

session = Session()

# Set Bearer token
session.set_bearer_token("your-api-token-here")

# Token is included in Authorization header
response = session.get("https://api.example.com/protected-resource")

session.close()
```

## Connection Pooling

Sessions automatically manage connection pooling for better performance:

```python
from reqivo import Session

session = Session()

# First request opens a connection
response1 = session.get("https://httpbin.org/get")

# Subsequent requests to the same host reuse the connection
response2 = session.get("https://httpbin.org/uuid")
response3 = session.get("https://httpbin.org/headers")

# Connections are reused, avoiding TCP/TLS handshake overhead
session.close()
```

## Async Session Management

All session features work with `AsyncSession`:

```python
import asyncio
from reqivo import AsyncSession

async def main():
    async with AsyncSession() as session:
        # Set persistent headers
        session.headers["Authorization"] = "Bearer token"

        # Set cookies
        session.cookies["session"] = "abc123"

        # Make requests
        response1 = await session.get("https://httpbin.org/get")
        response2 = await session.post("https://httpbin.org/post", json={"data": 123})

        print(f"Cookies: {session.cookies}")

asyncio.run(main())
```

## Session Configuration

### Custom Timeout

```python
from reqivo import Session

session = Session()

# Set default timeout for all requests
# (Can be overridden per-request)
response = session.get("https://httpbin.org/delay/2", timeout=5.0)

session.close()
```

### Per-Request Headers

Override or add headers for specific requests:

```python
from reqivo import Session

session = Session()

# Set default headers
session.headers["User-Agent"] = "MyApp/1.0"

# Override for specific request
response = session.get(
    "https://httpbin.org/headers",
    headers={"User-Agent": "SpecialBot/2.0"}
)

session.close()
```

## Session Lifecycle

### Context Manager (Recommended)

```python
from reqivo import Session

# Automatic cleanup
with Session() as session:
    session.headers["API-Key"] = "secret"
    response = session.get("https://api.example.com/data")
    print(response.json())
# Session automatically closed
```

### Manual Lifecycle

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

def create_api_session(api_key: Optional[str] = None) -> Session:
    """Create a configured session for API access"""
    session = Session()

    # Configure session
    session.headers["Accept"] = "application/json"
    session.headers["User-Agent"] = "MyApp/1.0"

    if api_key:
        session.set_bearer_token(api_key)

    return session

# Usage
with create_api_session("my-api-key") as session:
    response = session.get("https://api.example.com/users")
    print(response.json())
```

### Session Wrapper Class

```python
from reqivo import Session
from typing import Any, Dict, Optional

class ApiClient:
    """Wrapper around Session for API-specific logic"""

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
        response = self.session.post(url, json=data, **kwargs)
        return response.json()

# Usage
with ApiClient("https://api.example.com", "my-key") as client:
    users = client.get("/users")
    new_user = client.post("/users", {"name": "Alice"})
```

## Session State

### Inspecting Session State

```python
from reqivo import Session

session = Session()

# Set some state
session.cookies["user_id"] = "123"
session.headers["Authorization"] = "Bearer token"

# Inspect state
print(f"Cookies: {session.cookies}")
print(f"Headers: {session.headers}")

# Check authentication
print(f"Has Basic Auth: {session._basic_auth is not None}")
print(f"Has Bearer Token: {session._bearer_token is not None}")

session.close()
```

## Best Practices

1. **Use Context Managers**: Always use `with Session()` for automatic cleanup

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

- [Quick Start Guide](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md)
- [Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md)
- [Error Handling](https://github.com/roldriel/reqivo/blob/main/examples/error_handling.md)
- [Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md)
