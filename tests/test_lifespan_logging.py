"""Test that lifespan context manager replaced on_event and structured logging is present."""
import subprocess
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_no_deprecated_on_event():
    """`@app.on_event` must be gone from the codebase."""
    result = subprocess.run(
        ["grep", "-r", "on_event", "app", "--include=*.py"],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    # Filter out __pycache__ just in case
    lines = [line for line in result.stdout.splitlines() if "__pycache__" not in line and ".pyc" not in line]
    assert len(lines) == 0, f"Found on_event usages:\n{result.stdout}"


def test_structured_log_statements_count():
    """At least 40 meaningful logger.info/warning/error calls across app/."""
    result = subprocess.run(
        ["bash", "-c", 'grep -rn "logger\\.\\(info\\|warning\\|error\\)" app --include="*.py" | grep -v __pycache__ | wc -l'],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    count = int(result.stdout.strip())
    assert count >= 40, f"Expected ≥40 log statements, found {count}"


def test_getLogger_files_count():
    """At least 15 files import getLogger."""
    result = subprocess.run(
        ["bash", "-c", 'grep -rl "getLogger" app --include="*.py" | grep -v __pycache__ | grep -v ".pyc" | wc -l'],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
    )
    count = int(result.stdout.strip())
    assert count >= 15, f"Expected ≥15 files with getLogger, found {count}"


def test_lifespan_import_present():
    """main.py must import asynccontextmanager and define lifespan."""
    main_path = _PROJECT_ROOT / "app" / "main.py"
    src = main_path.read_text(encoding="utf-8")
    assert "asynccontextmanager" in src, "main.py missing asynccontextmanager import"
    assert "def lifespan(" in src, "main.py missing lifespan function"
    assert "lifespan=lifespan" in src, "FastAPI constructor missing lifespan= argument"
