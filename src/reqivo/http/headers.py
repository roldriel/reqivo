"""src/reqivo/http/headers.py

Robust HTTP header management for Reqivo.
"""

from typing import Dict, Optional


class Headers:
    """Case-insensitive dictionary for HTTP headers."""

    __slots__ = ("_headers",)

    def __init__(self, headers: Optional[Dict[str, str]] = None):
        self._headers: Dict[str, str] = {}
        if headers:
            for k, v in headers.items():
                self._headers[k.lower()] = v

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Gets a header value."""
        return self._headers.get(key.lower(), default)
