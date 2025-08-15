# Contributing to MusicWeb

Thank you for your interest in contributing to MusicWeb! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Testing](#testing)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- A GitHub account

### Development Setup

1. **Fork the repository** on GitHub

2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/musicweb.git
   cd musicweb
   ```

3. **Set up the development environment**:
   ```bash
   # Create a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install development dependencies
   pip install -e ".[dev,test]"
   
   # Install pre-commit hooks
   pre-commit install
   ```

4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Making Changes

### Before You Start

1. **Check existing issues** and pull requests to avoid duplicating work
2. **Create an issue** to discuss major changes before implementing
3. **Ensure your branch is up to date** with the main branch

### Development Workflow

1. **Write tests** for your changes (if applicable)
2. **Make your changes** following our code style guidelines
3. **Run tests** to ensure everything works:
   ```bash
   pytest tests/
   ```
4. **Run code quality checks**:
   ```bash
   black src/ tests/
   isort src/ tests/
   flake8 src/ tests/
   mypy src/musicweb/
   ```

### Types of Contributions

#### Bug Fixes
- Include a clear description of the bug
- Add regression tests when possible
- Reference the issue number in your commit message

#### New Features
- Discuss the feature in an issue first
- Include comprehensive tests
- Update documentation as needed
- Follow existing code patterns

#### Documentation
- Use clear, concise language
- Include code examples when helpful
- Test any code examples you include

## Submitting Changes

### Pull Request Process

1. **Ensure your code passes all checks**:
   ```bash
   # Run the full test suite
   pytest tests/ --cov=src/musicweb
   
   # Check code quality
   black --check src/ tests/
   isort --check-only src/ tests/
   flake8 src/ tests/
   mypy src/musicweb/
   ```

2. **Update documentation** if needed

3. **Create a pull request** with:
   - Clear title and description
   - Reference to related issues
   - Screenshots for UI changes
   - Breaking changes highlighted

4. **Respond to feedback** from reviewers

### Pull Request Guidelines

- **One feature per PR**: Keep changes focused and atomic
- **Clear commit messages**: Use conventional commit format when possible
- **Update CHANGELOG.md**: Add your changes to the Unreleased section
- **Tests required**: New features and bug fixes must include tests
- **Documentation**: Update docs for new features or breaking changes

## Code Style

### Python Code Style

We follow PEP 8 with some modifications:

- **Line length**: 88 characters (Black default)
- **String quotes**: Double quotes preferred
- **Import sorting**: Use isort with Black profile
- **Type hints**: Required for public APIs

### Code Quality Tools

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security linting

### Pre-commit Hooks

We use pre-commit hooks to ensure code quality:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

## Testing

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── fixtures/       # Test data and fixtures
└── conftest.py     # Pytest configuration
```

### Writing Tests

- **Use pytest**: Our testing framework of choice
- **Test naming**: `test_function_name_scenario`
- **Fixtures**: Use pytest fixtures for test data
- **Mock external dependencies**: Use `pytest-mock` for mocking
- **Coverage**: Aim for >90% test coverage

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/musicweb --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_core/test_models.py
```

## Documentation

### Documentation Structure

- **README.md**: Project overview and quick start
- **docs/**: Detailed documentation
- **Docstrings**: All public functions and classes
- **Type hints**: All function signatures
- **CHANGELOG.md**: Version history

### Writing Documentation

- **Clear and concise**: Write for your intended audience
- **Code examples**: Include working examples
- **API documentation**: Automatically generated from docstrings
- **User guides**: Step-by-step instructions

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release PR
4. Tag release after merge
5. GitHub Actions handles PyPI publication

## Getting Help

- **GitHub Issues**: For bugs and feature requests
- **GitHub Discussions**: For questions and general discussion
- **Documentation**: Check the docs/ directory
- **Code Examples**: See the examples/ directory

## Recognition

Contributors will be recognized in:
- **CHANGELOG.md**: For their specific contributions
- **GitHub**: Through the contributors graph
- **Documentation**: In acknowledgments section

Thank you for contributing to MusicWeb! 🎵