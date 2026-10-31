# AGENTS.md

Manual for AI agents working on `homeassistant-plum-ecomax`. Read fully before changing code.

## 1. Project Overview

1.1. `homeassistant-plum-ecomax` is a Home Assistant custom component integration for Plum ecoMAX boiler controllers and ecoSTER thermostats over serial (RS-485) or TCP bridge.

1.2. Protocol details, frame decoding, device models, and communication logic belong strictly in the underlying `PyPlumIO` library (submodule `PyPlumIO/`). The integration serves strictly as the glue layer between Home Assistant and `PyPlumIO`.

1.3. Minimum Python is 3.14.2 (`requires-python = ">=3.14.2"`). All tools target Python 3.14.

1.4. The single source of truth for version and dependency definitions is `pyproject.toml`. `manifest.json` and `hacs.json` are synchronized automatically via `scripts/sync_manifest.py`.

## 2. Tooling & Environment

2.1. Environment and dependencies are managed exclusively with `uv`. Git hooks are run with `prek`. Never run bare `pip` or `tox`.

2.2. Common commands:
- `uv sync`: Sync virtual environment with `uv.lock`.
- `uv run prek run --all-files`: Run all git hooks (check json, uv sync, ruff check, ruff format, codespell, mypy, complexipy, sync translations, sync manifest).
- `uv run pytest`: Run test suite (coverage is enforced automatically at 100% via `pytest-cov`). For fast parallel execution, use `uv run pytest -n auto`.
- `uv run python scripts/sync_translations.py --sort`: Sync and sort translations after editing `strings.json`.
- `uv run python scripts/sync_manifest.py`: Synchronize `manifest.json` and `hacs.json` from `pyproject.toml`.

2.3. Before finishing any task, both `uv run pytest` (with 100% coverage) and `uv run prek run --all-files` must pass inside the devcontainer.

## 3. Code Standards & Architecture

3.1. Ruff formats and lints: line length 88, double quotes, target Python 3.14.

3.2. Cognitive complexity must be at most 15 per function (`complexipy`). Extract private helpers instead of suppressing.

3.3. Timestamps: always use timezone-aware UTC datetimes (`datetime.now(tz=datetime.UTC)`).

3.4. Annotate every function. Mypy runs with strict equality and untyped checks; rules are relaxed only for `tests.*`.

3.5. Coverage must stay at 100% (`--cov-fail-under=100`). `if TYPE_CHECKING:` and `@overload` are excluded. Use `# pragma: no cover` only when coverage is truly impossible.

3.6. Enum naming: all enum classes must have plural names (e.g., `DeviceTypes` instead of `DeviceType`, `Weekdays` instead of `Weekday`).

## 4. Git & Commit Conventions

4.1. Commit message format:
- Subject prefixed with `[ai] ` for autonomous changes or `[human+ai] ` for collaborative changes.
- At most 50 characters long (including prefix).
- End in a full stop (`.`).
- An extended body is allowed.

4.2. Verify all checks pass before committing:
- `uv run prek run --all-files`
- `uv run pytest` (100% coverage required)
