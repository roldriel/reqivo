# Test Mapping - Source Code ↔ Tests

> **Complete mapping of source files to unit and integration tests**
>
> Last updated: 2026-01-29
> Version: 0.1.1
> Status: Updated to reflect existing tests in `tests/unit/`

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Organization Principle](#organization-principle)
3. [Complete Mapping](#complete-mapping)
4. [Coverage Status](#coverage-status)
5. [Pending Tests](#pending-tests)
6. [Guide for New Tests](#guide-for-new-tests)

---

## 📊 Executive Summary

### Current Test Status

| Category | Total Files | With Unit Tests | With Int Tests | Unit Coverage | Int Coverage |
|----------|-------------|----------------|----------------|---------------|--------------|
| **CLIENT** | 5 | 4/5 (80%) | 0/5 (0%) | ✅ High (Files) | 0% |
| **HTTP** | 4 | 4/4 (100%) | 0/4 (0%) | ✅ High (Files) | 0% |
| **TRANSPORT** | 3 | 3/3 (100%) | 0/3 (0%) | ✅ High (Files) | 0% |
| **UTILS** | 4 | 4/4 (100%) | 0/4 (0%) | ✅ High (Files) | 0% |
| **CORE** | 2 | 2/2 (100%) | 0/2 (0%) | 100% | 0% |
| **TOTAL** | 18 | 17/18 (94% files) | 0/18 (0%) | ~90% (Est.) | 0% |

**Note**: "94% files" = percentage of files that have a dedicated test file. Actual line coverage needs verification via `pytest --cov`.

**⚠️ Status**: Unit tests are largely implemented. Focus shifts to **Integration Tests** and the missing `test_auth.py`.

---

## 🎯 Organization Principle

We follow **ADR-014: Test Structure Organization**:

### 1:1 Mapping Rule

**Each source file must have**:
1. **A corresponding unit test file** (Mostly complete!)
2. **At least one integration test** using it in real context (Pending)

### Directory Structure

```
src/reqivo/                      tests/
├── client/                      ├── unit/
│   ├── session.py      ────────►│   ├── test_session.py      ✅
│   ├── request.py      ────────►│   ├── test_request.py      ✅
│   ├── response.py     ────────►│   ├── test_response.py     ✅
│   ├── websocket.py    ────────►│   ├── test_websocket.py    ✅
│   └── auth.py         ────────►│   └── (MISSING)            ❌
│                                │
├── http/                        │
│   ├── http11.py       ────────►│   ├── test_http_parser.py  ✅
│   ├── headers.py      ────────►│   ├── test_headers.py      ✅
│   ├── body.py         ────────►│   ├── test_body.py         ✅
│   └── url.py          ────────►│   ├── test_url.py          ✅
│                                │
├── transport/                   │
│   ├── connection.py   ────────►│   ├── test_connection.py   ✅
│   ├── connection_pool.py ─────►│   ├── test_connection_pool.py ✅
│   └── tls.py          ────────►│   ├── test_tls.py          ✅
│                                │
├── utils/                       │
│   ├── timing.py       ────────►│   ├── test_timing.py       ✅
│   ├── validators.py   ────────►│   ├── test_utils.py (Combined) ✅
│   ├── websocket_utils.py ─────►│   ├── test_websocket_utils.py ✅
│   └── serialization.py ───────►│   ├── test_utils.py (Combined) ✅
│                                │
├── exceptions.py       ────────►│   ├── test_exceptions.py   ✅
└── version.py          ────────►│   └── test_version.py      ✅
                                 │
                                 ├── integration/
                                 │   └── test_placeholder.py  ⚠️ (Need real tests)
                                 │
                                 └── utils/
                                     └── (Helpers to be documented)
```

---

## 🗺️ Complete Mapping

### 1. CLIENT LAYER (`src/reqivo/client/`)

#### 1.1 session.py

**Source**: [src/reqivo/client/session.py](../../src/reqivo/client/session.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_session.py`
**Status**: Implemented. Needs coverage verification.

#### 1.2 request.py

**Source**: [src/reqivo/client/request.py](../../src/reqivo/client/request.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_request.py`
**Status**: Implemented.

#### 1.3 response.py

**Source**: [src/reqivo/client/response.py](../../src/reqivo/client/response.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_response.py`
**Status**: Implemented.

#### 1.4 websocket.py

**Source**: [src/reqivo/client/websocket.py](../../src/reqivo/client/websocket.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_websocket.py`
**Status**: Implemented.

#### 1.5 auth.py

**Source**: [src/reqivo/client/auth.py](../../src/reqivo/client/auth.py)
**Unit Tests**: ❌ **PENDING** → `tests/unit/test_auth.py`
**Status**: Missng. High Priority for next steps.

---

### 2. HTTP LAYER (`src/reqivo/http/`)

#### 2.1 http11.py

**Source**: [src/reqivo/http/http11.py](../../src/reqivo/http/http11.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_http_parser.py`
**Status**: Implemented.

#### 2.2 headers.py

**Source**: [src/reqivo/http/headers.py](../../src/reqivo/http/headers.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_headers.py`
**Status**: Implemented.

#### 2.3 body.py

**Source**: [src/reqivo/http/body.py](../../src/reqivo/http/body.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_body.py`
**Status**: Implemented.

#### 2.4 url.py

**Source**: [src/reqivo/http/url.py](../../src/reqivo/http/url.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_url.py`
**Status**: Implemented.

---

### 3. TRANSPORT LAYER (`src/reqivo/transport/`)

#### 3.1 connection.py

**Source**: [src/reqivo/transport/connection.py](../../src/reqivo/transport/connection.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_connection.py`
**Status**: Implemented.

#### 3.2 connection_pool.py

**Source**: [src/reqivo/transport/connection_pool.py](../../src/reqivo/transport/connection_pool.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_connection_pool.py`
**Status**: Implemented.

#### 3.3 tls.py

**Source**: [src/reqivo/transport/tls.py](../../src/reqivo/transport/tls.py)
**Unit Tests**: ✅ **EXISTING** → `tests/unit/test_tls.py`
**Status**: Implemented.

---

### 4. UTILS LAYER (`src/reqivo/utils/`)

#### 4.1-4.4 Utils

- **timing.py**: ✅ `tests/unit/test_timing.py`
- **validators.py**: ✅ `tests/unit/test_utils.py` (Functional tests)
- **websocket_utils.py**: ✅ `tests/unit/test_websocket_utils.py`
- **serialization.py**: ✅ `tests/unit/test_utils.py` (Functional tests)

---

### 5. CORE MODULES

- **exceptions.py**: ✅ `tests/unit/test_exceptions.py`
- **version.py**: ✅ `tests/unit/test_version.py`

---

## 📈 Coverage Status

### Coverage by Module

| Module | Unit Tests | Status |
|--------|------------|--------|
| **client/session.py** | ✅ `test_session.py` | ✅ OK |
| **client/request.py** | ✅ `test_request.py` | ✅ OK |
| **client/response.py** | ✅ `test_response.py` | ✅ OK |
| **client/websocket.py** | ✅ `test_websocket.py` | ✅ OK |
| **client/auth.py** | ❌ Missing | 🔴 PENDING |
| **http/http11.py** | ✅ `test_http_parser.py` | ✅ OK |
| **http/* other** | ✅ Individual tests | ✅ OK |
| **transport/connection** | ✅ `test_connection.py` | ✅ OK |
| **transport/pool** | ✅ `test_connection_pool.py` | ✅ OK |
| **transport/tls** | ✅ `test_tls.py` | ✅ OK |

### Pending Tests Prioritization

#### 🔥 HIGH PRIORITY (Critical)

1. **client/auth.py** - Missing Unit Tests.
2. **Integration Tests** - All missing. Need to create real flows.

#### 🔸 MEDIUM PRIORITY

3. **Verify Coverage** - Run `pytest --cov` to ensure 97% is met in these existing files.

---

## 📝 Pending Tests

### Pending Unit Tests

```bash
tests/unit/test_auth.py  ← 🔥 PRIORITY 1 (Missing)
```

### Pending Integration Tests

```bash
# Still required to prove components work together
tests/integration/test_http_flow.py
tests/integration/test_session_flow.py
tests/integration/test_websocket_flow.py
tests/integration/test_connection_pooling.py
tests/integration/test_tls_flow.py
tests/integration/test_timeout_flow.py
```

---

**End of Test Mapping**
