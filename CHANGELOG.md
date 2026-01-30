# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive benchmark suite with comparison, microbenchmarks, memory, and profiling scripts
- Enhanced documentation with examples directory (quick_start, advanced_patterns, async_usage)
- Strict mypy type checking configuration
- py.typed marker for PEP 561 compliance
- Integration and all test environments in tox.ini
- Professional project configuration files (.editorconfig, MANIFEST.in, git commit template)

### Changed
- Increased coverage threshold from 80% to 97%
- Enhanced pylint configuration with design rules
- Improved tox.ini with additional test environments

## [0.1.0] - 2026-01-21

### Added
- Initial release of Reqivo
- Async/await support with AsyncSession and AsyncRequest
- HTTP/1.1 support with GET and POST methods
- WebSocket support (sync and async)
- Connection pooling
- Basic type hints
- Unit tests for core functionality

### Project Goals
- Modern, async-first design
- Zero-dependency HTTP client (using only standard library)
- High performance and memory efficiency
- Production-ready quality standards
