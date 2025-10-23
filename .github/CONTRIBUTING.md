# Contributing to HN RSS Translator

Thank you for your interest in contributing!

## Development Setup

### Using uv (Recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/YOUR_USERNAME/hn-summary-and-translate
cd hn-summary-and-translate

# Install dependencies
uv sync

# Run tests
uv run pytest tests/ -v
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/hn-summary-and-translate
cd hn-summary-and-translate

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

## Development Workflow

1. Create a new branch for your feature/fix
2. Make your changes
3. Run tests: `uv run pytest tests/ -v`
4. Run linting: `uv run pylint src/`
5. Format code: `uv run black src/ main.py`
6. Submit a pull request

## Updating Dependencies

When adding or updating dependencies, use `pyproject.toml` as the source of truth:

```bash
# Add a new dependency
uv add package-name

# Update requirements.txt for pip users
uv pip compile pyproject.toml -o requirements.txt

# Update lockfile
uv lock
```

## Code Style

- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and small
- Add tests for new features

## Commit Messages

- Use clear, descriptive commit messages
- Start with a verb (Add, Fix, Update, Remove)
- Reference issues when applicable

## Questions?

Feel free to open an issue for any questions or concerns!
