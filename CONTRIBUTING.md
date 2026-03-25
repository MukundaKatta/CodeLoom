# Contributing to CodeLoom

We welcome contributions! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/MukundaKatta/CodeLoom.git
cd CodeLoom
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Running Tests

```bash
make test
```

## Linting

```bash
make lint
make format
```

## Pull Request Guidelines

1. Fork the repo and create a feature branch from `main`.
2. Write tests for any new functionality.
3. Ensure `make test` and `make lint` pass.
4. Keep commits focused — one logical change per commit.
5. Open a PR with a clear description of the change.

## Code Style

- Follow PEP 8 conventions (enforced by ruff).
- Line length limit: 100 characters.
- Use type hints for all public function signatures.

## Reporting Issues

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behaviour
- Python version and OS

Thank you for helping improve CodeLoom!
