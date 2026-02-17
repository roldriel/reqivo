# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.x     | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Reqivo, please report it responsibly.

**Do not open a public issue.** Instead, send an email to **roldriel@gmail.com** with the following information:

- A description of the vulnerability
- Steps to reproduce the issue
- The potential impact
- Any suggested fix (optional)

You should receive an initial response within **48 hours**. Once the issue is confirmed, a fix will be developed and released as soon as possible, typically within **7 days** for critical issues.

## Disclosure Policy

- We will acknowledge receipt of your report promptly.
- We will work with you to understand and resolve the issue.
- We will credit you in the release notes (unless you prefer to remain anonymous).
- We ask that you do not disclose the vulnerability publicly until a fix has been released.

## Scope

This policy applies to the `reqivo` Python package distributed via [PyPI](https://pypi.org/project/reqivo/) and the source code hosted at [GitHub](https://github.com/roldriel/reqivo).

## Security Best Practices

Reqivo is designed with security in mind:

- **Zero external dependencies** in core — minimizes supply chain risk
- **No `eval()` or dynamic code execution** — all parsing is explicit
- **Strict type checking** with mypy and type hints across the codebase
- **Extensive test coverage (97%+)** to reduce regressions
