# AI Agents & Developer Guide for Reqivo

> **Master Guide for AI Agents and Developers on How to Operate in the Reqivo Codebase**
>
> ⚠️ **CRITICAL INSTRUCTION FOR AGENTS**: This is your primary instruction manual. Follow it strictly.
>
> Last updated: 2026-01-29
> Version: 0.1.0

---

## 🤖 QUICK AGENT DIRECTIVE (Read First)

**You are an expert software engineer working on Reqivo.**

**Your Core Directives:**
1.  **Zero Dependencies**: NEVER add external libraries (except dev tools). Use only Python 3.9+ stdlib.
2.  **Coverage ≥97%**: NO negotiation. If you change code, you MUST update/add tests to maintain 97%+.
3.  **Strict Typing**: NO `Any`. NO `type: ignore` (unless fully justified). Use explicit `Optional`, `Union`, etc.
4.  **Google-Style Docstrings**: REQUIRED for all public modules, classes, and functions. English only.
5.  **3-Layer Architecture**: Respect Client -> Protocol -> Transport boundaries.
6.  **No Git Commands**: NEVER execute `git commit` or `git push`. Suggest commands to the user.

**Before writing a single line of code:**
1.  Read `ARCHITECTURE.md` (Blueprints).
2.  Read `ADR/0000-ADR.md` (Rules).
3.  Read `TEST_MAPPING.md` (Where to test).

---

## 📋 Full Manual Table of Contents

1. [Before Starting](#before-starting)
2. [Complete Workflow](#complete-workflow)
3. [Code Standards](#code-standards)
4. [Testing Requirements](#testing-requirements)
5. [Required Documentation](#required-documentation)
6. [Semantic Versioning](#semantic-versioning)
7. [Git Workflow](#git-workflow)
8. [Checklist by Change Type](#checklist-by-change-type)
9. [Special Cases](#special-cases)
10. [FAQ](#faq)

---

## 🚦 BEFORE STARTING

### 1. Mandatory Reading

Before making **ANY** change, you must have read:

- ✅ [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) - Documentation Index
- ✅ [0000-ADR.md](../architecture/ADR/0000-ADR.md) - Architectural Decisions (14 ADRs)
- ✅ [ROADMAP.md](../architecture/ROADMAP.md) - Current status and future
- ✅ [TEST_MAPPING.md](TEST_MAPPING.md) - Tests mapping
- ✅ [CONTRIBUTING.md](../../CONTRIBUTING.md) - Contribution guide

### 2. Verify Alignment with ADRs

**CRITICAL**: Every change must respect existing architectural decisions.

Verify that your change is compatible with:

| ADR | Decision | Does your change respect it? |
|-----|----------|------------------------------|
| [ADR-001](../architecture/ADR/0001-zero-dependencies-policy.md) | Zero Dependencies | ❓ Adding external deps? → ❌ NOT ALLOWED |
| [ADR-002](../architecture/ADR/0002-async-first-architecture.md) | Async-First | ❓ Async code is primary, sync is wrapper? |
| [ADR-003](../architecture/ADR/0003-session-based-state-management.md) | Session-Based | ❓ Session holds state, Request is stateless? |
| [ADR-004](../architecture/ADR/0004-lifo-connection-pooling.md) | LIFO Pooling | ❓ Connection pool uses LIFO strategy? |
| [ADR-005](../architecture/ADR/0005-http11-before-http2.md) | HTTP/1.1 First | ❓ No HTTP/2 added before v1.0.0? |
| [ADR-006](../architecture/ADR/0006-granular-exception-hierarchy.md) | Granular Exceptions | ❓ Using specific existing exceptions? |
| [ADR-007](../architecture/ADR/0007-memory-optimization-with-slots.md) | `__slots__` | ❓ Using `__slots__` in frequent classes? |
| [ADR-008](../architecture/ADR/0008-strict-type-safety.md) | Strict Types | ❓ Complete type hints, strict mypy? |
| [ADR-009](../architecture/ADR/0009-97-percent-test-coverage-minimum.md) | 97% Coverage | ❓ Tests maintain ≥97% coverage? |
| [ADR-010](../architecture/ADR/0010-limited-public-api-surface.md) | Limited API | ❓ Only adding to public API if necessary? |
| [ADR-011](../architecture/ADR/0011-three-layer-architecture.md) | 3 Layers | ❓ Respecting Client/Protocol/Transport? |
| [ADR-012](../architecture/ADR/0012-manual-http-parsing.md) | Manual Parsing | ❓ Not using external libs for HTTP? |
| [ADR-013](../architecture/ADR/0013-python-39-minimum-version.md) | Python 3.9+ | ❓ Code compatible with Python 3.9+? |
| [ADR-014](../architecture/ADR/0014-test-structure-organization.md) | Test Structure | ❓ Tests follow 1:1 structure? |

**If any answer is NO**: You must create a new ADR or justify why one is being broken.

### 3. Identify Change Type

Classify your change:

- 🆕 **New Feature** → Requires: Tests, Docs, roadmap update, possible version bump
- 🐛 **Bug Fix** → Requires: Regression test, CHANGELOG entry
- 🔧 **Refactoring** → Requires: Maintain existing tests passing, no API changes
- 📝 **Documentation** → Requires: Verify consistency with code
- 🧪 **Tests** → Requires: Update TEST_MAPPING.md
- ⚡ **Performance** → Requires: Benchmarks before/after
- 🔒 **Security** → Requires: Impact analysis, possible hotfix

---

## 🔄 COMPLETE WORKFLOW

### Step 0: Preparation

```bash
# 1. Ensure clean environment
# 2. Have Python 3.9+ installed
# 3. Development dependencies installed
pip install -e ".[test,docs]"
pip install black isort pylint mypy bandit
```

### Step 1: Read Context

1. ✅ Read relevant ADRs
2. ✅ Review ROADMAP.md for current status - [ROADMAP.md](../architecture/ROADMAP.md)
3. ✅ Review TEST_MAPPING.md for existing tests
4. ✅ Read related existing code

### Step 2: Plan Change

**Before writing code**:

1. ✅ Identify files to be modified
2. ✅ Identify new files to be created
3. ✅ Identify tests to be created/modified
4. ✅ Identify documentation to be updated
5. ✅ Determine if it's a breaking change

**Key Question**: Does this change break backward compatibility?
- YES → Major version bump (1.0.0 → 2.0.0)
- NO, adds features → Minor version bump (0.1.0 → 0.2.0)
- NO, only bug fix → Patch version bump (0.1.0 → 0.1.1)

### Step 3: Implement Change

**Recommended Order** (TDD):

```
1. Write tests first (if feature or bug fix)
2. Implement code
3. Pass tests
4. Refactor
5. Repeat
```

**WHILE IMPLEMENTING**:

- ✅ Type hints on EVERYTHING
- ✅ English Google-style docstrings on EVERYTHING
- ✅ `__slots__` on frequent classes
- ✅ Error handling with specific exceptions
- ✅ Logging (when supported in v0.5.0+)

### Step 4: Testing

```bash
# 1. Format code
black src/reqivo tests/
isort src/reqivo tests/

# 2. Type check
mypy src/reqivo --strict

# 3. Lint
pylint src/reqivo

# 4. Security scan
bandit -r src/reqivo

# 5. Run tests
pytest --cov=reqivo --cov-report=term --cov-report=html

# 6. Verify coverage ≥97%
coverage report --fail-under=97
```

**ALL CHECKS MUST PASS**.

### Step 5: Documentation

Update the following files as appropriate:

| Document | When to update |
|----------|----------------|
| **README.md** | If public API or installation changed |
| **CHANGELOG.md** | ALWAYS (every visible change) |
| **ROADMAP.md** | If completed/started a feature |
| **TEST_MAPPING.md** | If added/modified tests or modules |
| **ADR/0000-ADR.md** | If architectural decision taken |
| **docs/** | If documented behavior changed |
| **PROJECT_ANALYSIS.md** | If major architecture changed |

See [Documentation Section](#required-documentation) for details.

### Step 6: Versioning

**IMPORTANT**: Update version according to Semantic Versioning.

```python
# src/reqivo/version.py
__version__ = "0.X.Y"  # Update per change type
```

See [Versioning Section](#semantic-versioning) for rules.

### Step 7: Prepare Commit (DO NOT EXECUTE)

**⚠️ CRITICAL: NEVER execute `git commit` or `git push` automatically.**

Instead, **RECOMMEND** to the user the commands and commit messages. See [Git Workflow](#git-workflow).

---

## 📐 CODE STANDARDS

### 1. Type Hints (MANDATORY)

**✅ CORRECT**:
```python
from typing import Optional, Dict, List, Union

def send_request(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> Response:
    """Send HTTP request.

    Args:
        url: Target URL.
        headers: Optional headers dict.
        timeout: Optional timeout in seconds.

    Returns:
        Response object.

    Raises:
        NetworkError: If connection fails.
        TimeoutError: If request times out.
    """
    pass
```

**❌ INCORRECT**:
```python
def send_request(url, headers=None, timeout=None):  # No types
    pass

def send_request(url: Any, headers: Any) -> Any:  # Abused Any
    pass
```

**Rules**:
- ✅ All parameters typed
- ✅ All returns typed
- ✅ Variables typed when not obvious
- ❌ NO `Any` (use `Union` or generics)
- ❌ NO `# type: ignore` without strong justification

### 2. Docstrings (MANDATORY)

**Format**: Google Style, in **ENGLISH**

**✅ CORRECT**:
```python
def parse_headers(data: bytes) -> Dict[str, str]:
    """Parse HTTP headers from raw bytes.

    This function parses HTTP headers following RFC 7230 spec.
    Header names are case-insensitive and normalized to lowercase.

    Args:
        data: Raw HTTP header bytes including CRLF separators.

    Returns:
        Dictionary with header name (lowercase) as key and value as string.

    Raises:
        InvalidResponseError: If headers are malformed or exceed size limit.

    Example:
        >>> data = b"Content-Type: application/json\\r\\n\\r\\n"
        >>> headers = parse_headers(data)
        >>> headers["content-type"]
        'application/json'

    Note:
        Duplicate headers are combined into a list value.
    """
    pass
```

**Mandatory Sections**:
- **Description**: What it does (simple present, 3rd person)
- **Args**: Each parameter with description
- **Returns**: What it returns
- **Raises**: What exceptions it raises
- **Example**: (optional but recommended) Usage example

### 3. Formatting

**Black** (line length 88, Python 3.9+ target):

```bash
black src/reqivo tests/
```

**isort** (import sorting, Black profile):

```bash
isort src/reqivo tests/
```

### 4. Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| **Modules** | lowercase_with_underscores | `connection_pool.py` |
| **Classes** | PascalCase | `ConnectionPool` |
| **Functions** | lowercase_with_underscores | `get_connection()` |
| **Variables** | lowercase_with_underscores | `max_size` |
| **Constants** | UPPERCASE_WITH_UNDERSCORES | `MAX_HEADER_SIZE` |
| **Private** | _leading_underscore | `_internal_method()` |

### 5. Memory Optimization

Use `__slots__` in **frequently instantiated** classes:

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

### 6. Error Handling

**Use existing specific exceptions**:

```python
# ✅ CORRECT
from reqivo.exceptions import ConnectTimeout, TlsError, InvalidResponseError

try:
    conn.open()
except socket.timeout:
    raise ConnectTimeout(f"Connection to {host}:{port} timed out")
except ssl.SSLError as e:
    raise TlsError(f"TLS handshake failed: {e}")
```

**❌ INCORRECT**:
```python
# DO NOT create generic new exceptions
raise Exception("Connection failed")  # NO
raise ValueError("Invalid response")  # NO (use InvalidResponseError)
```

### 7. Imports

**Order** (isort does automatically):
```python
# 1. Standard library
import socket
import ssl
from typing import Optional, Dict

# 2. Reqivo imports (absolute)
from reqivo.exceptions import NetworkError, ConnectTimeout
from reqivo.http.headers import Headers
from reqivo.transport.connection import Connection
```

---

## 🧪 TESTING REQUIREMENTS

### 1. Minimum Coverage: 97%

**NON-NEGOTIABLE**: Every change must maintain coverage ≥97%.

```bash
# Verify coverage
pytest --cov=reqivo --cov-report=term --cov-report=html

# Must show:
# TOTAL    1966    XX    97%
```

If coverage drops below 97%:
- ❌ Change rejected
- ✅ Add tests until 97%+ reached

### 2. Test Structure

**1:1 Rule**: Every source file has its unit test.

```
src/reqivo/client/session.py → tests/unit/test_session.py
src/reqivo/http/http11.py     → tests/unit/test_http_parser.py
```

See [TEST_MAPPING.md](TEST_MAPPING.md) for full structure.

### 3. Unit Tests

**Template**:
```python
"""tests/unit/test_<module>.py

Unit tests for reqivo.<layer>.<module>
"""
import pytest
from reqivo.<layer>.<module> import <Class>

class Test<Class>Init:
    """Tests for <Class>.__init__()"""
    def test_init_<scenario>(self):
        # ...

class Test<Class><Method>:
    """Tests for <Class>.<method>()"""
    def test_<method>_<normal_case>(self):
        # ...
```

### 4. Integration Tests

**Location**: `tests/integration/test_<feature>_flow.py`

### 5. Coverage Types

Each module must have tests for:

- ✅ **Happy path**: Normal usage
- ✅ **Edge cases**: Limits, special values (0, None, "", etc.)
- ✅ **Error paths**: Exceptions, timeouts, failures
- ✅ **Async variant**: If async version exists
- ✅ **Integration**: Full end-to-end flow

---

## 📝 REQUIRED DOCUMENTATION

### 1. README.md & CHANGELOG.md

**Update when**: Public API changes or visible features added.

### 2. ROADMAP.md

**Update when**: Completed or started a feature.

### 3. TEST_MAPPING.md

**Update when**: Added or modified tests.

### 4. ADR/0000-ADR.md

**Update when**: Significant architectural decision taken.

---

## 📦 SEMANTIC VERSIONING

**Rules** ([Semantic Versioning 2.0.0](https://semver.org/)):

- **MAJOR (X.0.0)**: Breaking changes.
- **MINOR (0.X.0)**: New features (backward compatible).
- **PATCH (0.0.X)**: Bug fixes, internal improvements.

**Version 0.x.x (Pre-1.0.0)**:
- 0.1.0 → 0.2.0: Can include breaking changes.
- 1.0.0 → 1.1.0: CANNOT include breaking changes.

---

## 🔀 GIT WORKFLOW

### ⚠️ CRITICAL RULE: NO GIT COMMANDS

**NEVER execute `git commit` or `git push` automatically.**

Instead, **RECOMMEND** to the user what to do using markdown code blocks.

### Commit Recommendation

Group changes logically:

1. **Implementation**: `feat(scope): ...`
2. **Tests**: `test(scope): ...`
3. **Docs**: `docs: ...`

---

## ✅ CHECKLIST BY CHANGE TYPE

### 🆕 NEW FEATURE

- [ ] Feature in ROADMAP.md
- [ ] Code with type hints and docstrings
- [ ] Unit and integration tests created
- [ ] Coverage ≥97%
- [ ] Quality checks pass (mypy, pylint, black)
- [ ] Docs updated (CHANGELOG, ROADMAP, TEST_MAPPING)
- [ ] Version updated (MINOR)

### 🐛 BUG FIX

- [ ] Test reproducing bug
- [ ] Fix implemented (without breaking API)
- [ ] Tests pass
- [ ] CHANGELOG updated (Fixed)
- [ ] Version updated (PATCH)

### 🔧 REFACTORING

- [ ] Clear objective
- [ ] Existing tests pass without changes
- [ ] Coverage maintained
- [ ] NO version change (unless major)

---

## 🔍 SPECIAL CASES

### Case 1: Breaking Change (v1.0.0+)
- Only with MAJOR bump.
- Requires deprecation path.

### Case 2: Dependencies (PROHIBITED)
- **ADR-001**: Zero dependencies.
- Only stdlib allowed.
- Exception: Dev tools.

---

## ❓ FAQ

**Q: Can I use external libraries?**
**A**: ❌ NO. ADR-001 establishes zero dependencies.

**Q: Can I commit on my own?**
**A**: ❌ NO if you are AI. Always recommend to user.

**Q: What if coverage drops below 97%?**
**A**: ❌ Not accepted. Add tests.

**Q: Can I use `Any`?**
**A**: ❌ NO. mypy strict doesn't allow `Any`.

**Q: Tests in Spanish?**
**A**: ❌ NO. Everything (docstrings, commits, tests) in **ENGLISH**.

---

## 📚 Quick References

- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- [ADR/0000-ADR.md](../architecture/ADR/0000-ADR.md)
- [ROADMAP.md](../architecture/ROADMAP.md)
- [TEST_MAPPING.md](TEST_MAPPING.md)
