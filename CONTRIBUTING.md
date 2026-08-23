# Contributing

Bug reports and focused pull requests are welcome. By contributing, you agree that your work is
licensed under MIT.

1. Create a branch and a Python 3.11 virtual environment.
2. Install `.[app,dev]`.
3. Keep OS behavior behind an adapter and engine behavior behind a domain protocol.
4. Run `ruff check .`, `ruff format --check .`, `mypy src`, and `pytest`.
5. Describe privacy or packaging implications in the pull request.

Do not introduce telemetry or cloud inference into the default application. New network access
must be opt-in, clearly documented, and isolated behind an interface.
