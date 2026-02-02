# Error Handling

Reqivo provides a comprehensive exception hierarchy for handling different types of errors that can occur during HTTP requests.

## Exception Hierarchy

```
ReqivoError (base)
├── RequestError
│   ├── NetworkError
│   │   ├── ConnectionError
│   │   ├── ConnectTimeout
│   │   ├── ReadTimeout
│   │   └── TlsError
│   ├── TimeoutError
│   ├── RedirectLoopError
│   └── InvalidResponseError
└── ProtocolError
```

## Basic Error Handling

```python
from reqivo import Session
from reqivo.exceptions import ReqivoError

session = Session()

try:
    response = session.get("https://httpbin.org/get")
    print(response.json())
except ReqivoError as e:
    print(f"Request failed: {e}")
finally:
    session.close()
```

## Handling Specific Errors

### Timeout Errors

```python
from reqivo import Session
from reqivo.exceptions import TimeoutError, ConnectTimeout, ReadTimeout

session = Session()

try:
    response = session.get("https://httpbin.org/delay/10", timeout=5.0)
except ConnectTimeout:
    print("Could not connect to server in time")
except ReadTimeout:
    print("Server did not send response in time")
except TimeoutError:
    print("Request timed out")
finally:
    session.close()
```

### Network Errors

```python
from reqivo import Session
from reqivo.exceptions import NetworkError, ConnectionError

session = Session()

try:
    response = session.get("https://nonexistent-domain-12345.com")
except ConnectionError as e:
    print(f"Could not connect to server: {e}")
except NetworkError as e:
    print(f"Network error occurred: {e}")
finally:
    session.close()
```

### TLS/SSL Errors

```python
from reqivo import Session
from reqivo.exceptions import TlsError

session = Session()

try:
    response = session.get("https://expired.badssl.com")
except TlsError as e:
    print(f"TLS/SSL error: {e}")
finally:
    session.close()
```

### Protocol Errors

```python
from reqivo import Session
from reqivo.exceptions import ProtocolError, InvalidResponseError

session = Session()

try:
    response = session.get("https://httpbin.org/get")

    # Parse response
    data = response.json()

except InvalidResponseError as e:
    print(f"Invalid HTTP response: {e}")
except ProtocolError as e:
    print(f"Protocol error: {e}")
finally:
    session.close()
```

## Error Recovery Patterns

### Retry Logic

```python
from reqivo import Session
from reqivo.exceptions import NetworkError, TimeoutError
import time

def fetch_with_retry(url: str, max_retries: int = 3):
    """Fetch URL with exponential backoff retry"""
    session = Session()

    for attempt in range(max_retries):
        try:
            response = session.get(url, timeout=10.0)
            session.close()
            return response

        except (NetworkError, TimeoutError) as e:
            if attempt == max_retries - 1:
                session.close()
                raise

            wait_time = 2 ** attempt  # Exponential backoff
            print(f"Attempt {attempt + 1} failed: {e}")
            print(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    session.close()

# Usage
try:
    response = fetch_with_retry("https://httpbin.org/delay/2")
    print(f"Success: {response.status_code}")
except Exception as e:
    print(f"All retries failed: {e}")
```

### Fallback Endpoints

```python
from reqivo import Session
from reqivo.exceptions import ReqivoError

def fetch_with_fallback(primary_url: str, fallback_url: str):
    """Try primary endpoint, fallback to secondary on failure"""
    session = Session()

    try:
        response = session.get(primary_url, timeout=5.0)
        return response

    except ReqivoError as e:
        print(f"Primary endpoint failed: {e}")
        print(f"Trying fallback endpoint...")

        try:
            response = session.get(fallback_url, timeout=5.0)
            return response

        except ReqivoError as e2:
            print(f"Fallback endpoint also failed: {e2}")
            raise

    finally:
        session.close()

# Usage
try:
    response = fetch_with_fallback(
        "https://primary.api.example.com/data",
        "https://backup.api.example.com/data"
    )
    print(response.json())
except ReqivoError:
    print("Both endpoints failed")
```

### Circuit Breaker Pattern

```python
from reqivo import Session
from reqivo.exceptions import ReqivoError
import time
from dataclasses import dataclass
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures detected, block requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreaker:
    """Circuit breaker for API calls"""
    failure_threshold: int = 5
    timeout: float = 60.0  # seconds
    success_threshold: int = 2  # successes needed to close

    def __post_init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)

            # Success
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0

            return result

        except ReqivoError as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

            raise

# Usage
breaker = CircuitBreaker(failure_threshold=3, timeout=30.0)

def api_call():
    session = Session()
    try:
        response = session.get("https://api.example.com/data", timeout=5.0)
        return response.json()
    finally:
        session.close()

# Make calls through circuit breaker
for i in range(10):
    try:
        data = breaker.call(api_call)
        print(f"Call {i}: Success")
    except Exception as e:
        print(f"Call {i}: Failed - {e}")
    time.sleep(1)
```

## Async Error Handling

### Basic Async Errors

```python
import asyncio
from reqivo import AsyncSession
from reqivo.exceptions import TimeoutError, NetworkError

async def fetch_data():
    async with AsyncSession() as session:
        try:
            response = await session.get(
                "https://httpbin.org/delay/10",
                timeout=5.0
            )
            return response.json()

        except TimeoutError:
            print("Request timed out")
            return None

        except NetworkError as e:
            print(f"Network error: {e}")
            return None

# Run
data = asyncio.run(fetch_data())
```

### Handling Concurrent Request Errors

```python
import asyncio
from reqivo import AsyncSession
from reqivo.exceptions import ReqivoError

async def fetch_with_error_handling():
    urls = [
        "https://httpbin.org/get",
        "https://httpbin.org/status/500",  # Server error
        "https://nonexistent.example.com",  # Network error
    ]

    async with AsyncSession() as session:
        tasks = []
        for url in urls:
            tasks.append(session.get(url, timeout=5.0))

        # Gather with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for url, result in zip(urls, results):
            if isinstance(result, ReqivoError):
                print(f"{url}: Error - {type(result).__name__}: {result}")
            else:
                print(f"{url}: Success - Status {result.status_code}")

asyncio.run(fetch_with_error_handling())
```

## Logging Errors

### Basic Logging

```python
import logging
from reqivo import Session
from reqivo.exceptions import ReqivoError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

session = Session()

try:
    response = session.get("https://httpbin.org/status/404")

    if response.status_code == 404:
        logger.warning(f"Resource not found: {response.url}")

except ReqivoError as e:
    logger.error(f"Request failed: {e}", exc_info=True)

finally:
    session.close()
```

### Structured Logging

```python
import logging
import json
from reqivo import Session
from reqivo.exceptions import ReqivoError

logger = logging.getLogger(__name__)

def log_request_error(url: str, error: Exception):
    """Log request error with structured data"""
    log_data = {
        "event": "request_error",
        "url": url,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    logger.error(json.dumps(log_data))

session = Session()

try:
    response = session.get("https://httpbin.org/delay/10", timeout=5.0)
except ReqivoError as e:
    log_request_error("https://httpbin.org/delay/10", e)
finally:
    session.close()
```

## Best Practices

1. **Catch Specific Exceptions**: Handle specific exceptions before general ones

2. **Always Close Sessions**: Use `finally` blocks or context managers to ensure cleanup

3. **Set Timeouts**: Always set appropriate timeouts to avoid hanging requests

4. **Log Errors**: Use logging to track errors in production

5. **Retry with Backoff**: Implement exponential backoff for transient failures

6. **Circuit Breaker**: Use circuit breakers for failing external services

7. **Graceful Degradation**: Provide fallbacks when services are unavailable

8. **Error Context**: Include relevant context (URL, timeout, etc.) in error messages

## Common Patterns

### Validate Status Codes

```python
from reqivo import Session
from reqivo.exceptions import ReqivoError

session = Session()

try:
    response = session.get("https://httpbin.org/status/404")

    if response.status_code >= 400:
        print(f"HTTP error: {response.status_code}")

    elif response.status_code >= 200 and response.status_code < 300:
        print(f"Success: {response.status_code}")

except ReqivoError as e:
    print(f"Request failed: {e}")

finally:
    session.close()
```

### Timeout Strategy

```python
from reqivo import Session
from reqivo.exceptions import TimeoutError

session = Session()

# Different timeouts for different operations
try:
    # Quick health check
    health = session.get("https://api.example.com/health", timeout=2.0)

    # Normal API call
    data = session.get("https://api.example.com/data", timeout=10.0)

    # Long-running operation
    report = session.post(
        "https://api.example.com/generate-report",
        json={"type": "monthly"},
        timeout=30.0
    )

except TimeoutError as e:
    print(f"Operation timed out: {e}")

finally:
    session.close()
```

## See Also

- [Quick Start Guide](https://github.com/roldriel/reqivo/blob/main/examples/quick_start.md)
- [Async Patterns](https://github.com/roldriel/reqivo/blob/main/examples/async_patterns.md)
- [Session Management](https://github.com/roldriel/reqivo/blob/main/examples/session_management.md)
- [Advanced Usage](https://github.com/roldriel/reqivo/blob/main/examples/advanced_usage.md)
