class LLMToolParseError(Exception):
    """Raised when an LLM returns a malformed tool-use block."""
    pass
