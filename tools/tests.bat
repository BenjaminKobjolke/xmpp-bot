@echo off
echo Running tests...
uv run pytest -v
echo.
echo Running ruff check...
uv run ruff check src/ tests/
echo.
echo Running mypy...
uv run mypy src/
pause
