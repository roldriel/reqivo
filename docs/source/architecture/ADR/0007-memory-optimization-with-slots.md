# ADR-007: Memory Optimization with `__slots__`

**Status**: ✅ Accepted
**Date**: 2026-01-29
**Deciders**: Rodrigo Roldán

## Context

Python objects use `__dict__` for attributes, which consumes memory:
- `__dict__` is dynamic, allows adding attributes at runtime
- Each instance has overhead of ~240 bytes (Python 3.9+)
- For frequently instantiated objects, this adds up

`__slots__` is an optimization:
- Defines fixed attributes in class
- Doesn't use `__dict__`, reduces memory by ~40%
- Attribute access is faster
- Trade-off: cannot add dynamic attributes

## Decision

**Use `__slots__` in frequently instantiated classes**:

Classes with `__slots__`:
- ✅ `Response` (one per request)
- ✅ `Request` (one per request)
- ✅ `Connection` (many in pool)
- ✅ `Timeout` (one per request)
- ✅ `Headers` (one per request)

Classes without `__slots__`:
- ❌ `Session` (few instances, mutable by design)
- ❌ `ConnectionPool` (one per session)
- ❌ Exceptions (rarely instantiated)

Example:
```python
class Response:
    __slots__ = (
        "raw",
        "status_line",
        "status_code",
        "headers",
        "body",
        "_text",
        "_json",
    )

    def __init__(self, raw: bytes):
        self.raw = raw
        self.status_line: str = ""
        # ...
```

## Consequences

### Positive ✅

1. **Memory**: ~40% less memory per instance
2. **Performance**: Faster attribute access
3. **Cache locality**: Better CPU cache utilization
4. **Type hints**: Attributes declared explicitly
5. **Bugs prevention**: Cannot add typos as attributes

### Negative ❌

1. **Rigidity**: Cannot add dynamic attributes
2. **Debugging**: Some debuggers assume `__dict__`
3. **Monkey patching**: Not possible (feature, not bug)
4. **Inheritance**: Subclasses must declare their own `__slots__`

### Mitigations

- **Only in stable classes**: Don't use in experimental classes
- **Document**: Indicate that class uses `__slots__`
- **Testing**: Verify that no attributes are attempted to be added

### Memory Savings

Estimation (Python 3.9+):

```python
# Without __slots__
Response object: ~280 bytes + data

# With __slots__
Response object: ~170 bytes + data

# For 10,000 requests:
Without __slots__: ~2.8 MB
With __slots__:    ~1.7 MB
Savings:           ~1.1 MB (39%)
```

## Alternatives Considered

1. **Don't use __slots__**: Rejected. Wastes memory unnecessarily.
2. **Use __slots__ everywhere**: Rejected. Makes extensibility difficult.
3. **Use frozen dataclasses**: Considered. Less control than __slots__.

## References

- [Python __slots__ documentation](https://docs.python.org/3/reference/datamodel.html#slots)
- [Memory savings with __slots__](https://wiki.python.org/moin/UsingSlots)
