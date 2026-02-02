# ADR-003: Session-Based State Management

**Status**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

### Context

Two common patterns in HTTP clients:

1. **Stateless requests** (like `urllib`):
   ```python
   response = urllib.request.urlopen(url)
   ```

2. **Stateful sessions** (like `requests`):
   ```python
   session = requests.Session()
   session.headers.update({'User-Agent': 'my-app'})
   response = session.get(url)  # Automatic headers
   ```

We need to decide whether Reqivo supports persistent state between requests.

### Decision

**Implement Session-based architecture** following the `requests` pattern:

- **Session**: Maintains state (cookies, headers, auth, connection pool)
- **Request**: Stateless builder that uses Session if provided
- **Dual API**: Support both patterns (stateless and stateful)

Structure:
```python
# Stateful (recommended)
with Session() as session:
    session.set_basic_auth("user", "pass")
    session.headers["User-Agent"] = "MyApp/1.0"

    resp1 = session.get(url1)  # Automatic headers and auth
    resp2 = session.get(url2)  # Cookies from resp1 included
    # Connection pool reuses connections

# Stateless (simple)
response = Request.send("GET", url)  # No state, no pool
```

**Responsibilities**:

**Session**:
- ✅ Cookie jar (Set-Cookie parsing, automatic sending)
- ✅ Persistent headers
- ✅ Authentication (Basic, Bearer)
- ✅ Connection pooling
- ✅ Context manager (automatic cleanup)

**Request**:
- ✅ HTTP request bytes construction
- ✅ Header injection prevention
- ✅ Request sending
- ❌ Does NOT maintain state
- ❌ Does NOT have its own connection pool

### Consequences

#### Positive ✅

1. **Familiar**: Known pattern from `requests`
2. **Efficient**: Connection reuse via pool
3. **Convenient**: Automatic headers/cookies/auth
4. **Flexible**: Supports both patterns (stateful/stateless)
5. **Clean separation**: Session = state, Request = builder

#### Negative ❌

1. **Complexity**: More code than stateless only
2. **Mutable state**: Sessions can have side effects
3. **Thread safety**: Sessions are not thread-safe by design

#### Mitigations

- **Document thread safety**: One Session per thread
- **Context managers**: Guarantee cleanup
- **Stateless API available**: For simple cases

### Alternatives Considered

1. **Stateless only**: Rejected. Inefficient for multiple requests.
2. **Stateful only**: Rejected. Too much overhead for simple cases.
3. **Global state**: Rejected. Anti-pattern, makes testing difficult.

### References

- requests.Session documentation
- HTTP State Management (RFC 6265)
