"""utils/validators.py

Validation utilities for Reqivo.
"""


def validate_url(url: str) -> bool:
    """Simple URL validation."""
    return url.startswith(("http://", "https://", "ws://", "wss://"))
