"""src/reqivo/http/headers.py

Robust HTTP header management for Reqivo.
"""

from typing import Any, Dict, Iterator, List, Mapping, Optional, TypeVar, Union, cast

_T = TypeVar("_T")


class Headers(Mapping[str, str]):
    """
    Case-insensitive dictionary for HTTP headers with support for multiple values.

    Behaves like a dictionary where values are strings. duplicate headers are
    joined by commas (except Set-Cookie).
    Access raw lists via get_all().
    """

    __slots__ = ("_headers",)

    def __init__(self, headers: Optional[Dict[str, Union[str, List[str]]]] = None):
        self._headers: Dict[str, List[str]] = {}
        if headers:
            for k, v in headers.items():
                # Support both single values and lists
                if isinstance(v, list):
                    self._headers[k.lower()] = v
                else:
                    self._headers[k.lower()] = [v]

    def __getitem__(self, key: str) -> str:
        """Get header value (comma-joined if multiple, except Set-Cookie)."""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return cast(str, value)

    def __iter__(self) -> Iterator[str]:
        return iter(self._headers)

    def __len__(self) -> int:
        return len(self._headers)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get header value.

        Args:
            key: Header name (case-insensitive).
            default: Default value if header not found.

        Returns:
            Comma-joined string for multiple values (except Set-Cookie
            which returns first), or default if not found.
        """
        values = self._headers.get(key.lower())
        if not values:
            return default

        if key.lower() == "set-cookie":
            return values[0]

        return ", ".join(values)

    def get_all(self, key: str) -> List[str]:
        """
        Get all values of a header.

        Args:
            key: Header name (case-insensitive).

        Returns:
            List of all values for the header, empty list if not found.
        """
        return self._headers.get(key.lower(), [])
