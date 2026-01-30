# Contributing to Reqivo

Thank you for your interest in contributing to Reqivo! This document provides guidelines and instructions for contributing.

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/roldriel/reqivo.git
cd reqivo
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[test,docs]"
pip install black isort pylint mypy bandit
```

## Code Quality Standards

Reqivo maintains high quality standards:

- **Coverage**: Minimum 97% test coverage
- **Type Hints**: All functions must have complete type annotations
- **Linting**: Code must pass pylint with score ≥8.0
- **Formatting**: Code must be formatted with Black and isort
- **Documentation**: All public APIs must have docstrings

## Running Tests

```bash
# Run all tests
tox

# Run tests for specific Python version
tox -e py312

# Run only unit tests
pytest tests/unit/

# Run with coverage
coverage run -m pytest
coverage report
```

## Code Style

We use:
- **Black** for code formatting (line length: 88)
- **isort** for import sorting
- **Pylint** for linting

Run formatters before committing:
```bash
black src tests
isort src tests
pylint src
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `ci`, `build`

Examples:
- `feat(async): add HTTP/2 multiplexing support`
- `fix: handle connection pool exhaustion`
- `docs: add WebSocket usage examples`

## Pull Request Process

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes following our code quality standards
3. Add tests for new functionality
4. Update documentation if needed
5. Run the full test suite: `tox`
6. Commit with conventional commit messages
7. Push and create a pull request

## Questions?

Open an issue on GitHub or reach out to the maintainers.

---

Thank you for helping make Reqivo better!
