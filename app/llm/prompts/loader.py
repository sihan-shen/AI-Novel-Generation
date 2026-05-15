"""Centralized prompt loader. Reads prompts from text files on demand."""

from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load(name: str) -> str:
    """Load a prompt by name (without .txt extension)."""
    path = _PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {name} ({path})")
    return path.read_text(encoding="utf-8").strip()
