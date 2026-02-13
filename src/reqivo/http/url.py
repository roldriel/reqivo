"""src/reqivo/http/url.py

URL builder and parser for Reqivo.
"""

import urllib.parse

__all__ = ["URL"]


class URL:
    """Utility class for URL parsing and information."""

    __slots__ = ("parsed", "scheme", "host", "port", "path")

    def __init__(self, url: str):
        self.parsed = urllib.parse.urlparse(url)
        self.scheme = self.parsed.scheme
        self.host = self.parsed.hostname
        self.port = self.parsed.port
        self.path = self.parsed.path
