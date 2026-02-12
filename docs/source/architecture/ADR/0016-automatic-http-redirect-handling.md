# ADR-016: Automatic HTTP Redirect Handling

**Estado**: Accepted
**Date**: 2026-02-11
**Deciders**: Rodrigo Roldan

## Context

HTTP clients must decide how to handle redirect responses (3xx status codes).
Key questions:

1. Should redirects be followed automatically or require manual handling?
2. How should the HTTP method change across redirects?
3. How to prevent infinite redirect loops?

**Relevant RFCs**:
- RFC 7231 (HTTP/1.1 Semantics): Defines redirect status codes
- RFC 7538: 308 Permanent Redirect

## Decision

**Automatic redirect following is enabled by default** with configurable behavior.

**Parameters**:
- `allow_redirects: bool = True` — Enable/disable automatic following
- `max_redirects: int = 30` — Maximum number of redirects before raising `TooManyRedirects`

**Method conversion rules**:

| Status Code | Behavior |
|-------------|----------|
| 301 Moved Permanently | POST/PUT/PATCH -> GET (drop body). HEAD preserved. |
| 302 Found | POST/PUT/PATCH -> GET (drop body). HEAD preserved. |
| 303 See Other | Always convert to GET (drop body). |
| 307 Temporary Redirect | Preserve original method and body. |
| 308 Permanent Redirect | Preserve original method and body. |

**Security behavior**:
- `Authorization` header is stripped when the redirect changes the host
- Redirect history is tracked in `response.history`

**Cycle detection**:
- A `visited_urls` set tracks all URLs visited during a redirect chain
- If a URL is visited twice, `RedirectLoopError` is raised immediately
- This catches cycles (A -> B -> A) before reaching `max_redirects`

## Consequences

#### Positive

1. **Ergonomic**: Users get final responses without manual redirect handling
2. **Safe**: Method conversion prevents unintended POST replays
3. **Secure**: Auth header stripping prevents credential leakage to third parties
4. **Predictable**: Cycle detection provides fast failure on redirect loops

#### Negative

1. **Implicit behavior**: Redirects happen silently, may surprise users
2. **Performance**: Each redirect adds a round-trip

#### Mitigations

- `allow_redirects=False` for users who want manual control
- Response history accessible for debugging redirect chains
- `max_redirects` prevents runaway chains

## Alternatives Considered

1. **Manual redirects only**: Rejected. Poor DX, every client would need redirect logic.
2. **Always preserve method**: Rejected. Violates RFC 7231 and causes unintended POST replays.
3. **No cycle detection**: Rejected. `max_redirects` alone is too slow for tight loops.

## References

- RFC 7231 Section 6.4 (Redirection)
- RFC 7538 (308 Permanent Redirect)
- Python requests library redirect behavior
- httpx redirect implementation
