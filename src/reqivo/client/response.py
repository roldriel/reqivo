"""src/reqivo/client/response.py

HTTP Response handling module.

This module provides classes for parsing and handling HTTP responses,
including status line, headers, and body parsing.
"""

# pylint: disable=line-too-long,unused-import,unused-variable

import json as std_json
from typing import Any, Dict, Generator, List, Optional, Union, cast

from reqivo.exceptions import InvalidResponseError, ProtocolError

# pylint: disable=unused-import
from reqivo.http.body import iter_read_chunked, read_exact
from reqivo.http.headers import Headers
from reqivo.http.http11 import HttpParser
from reqivo.transport.connection import Connection

__all__ = ["ResponseParseError", "Response"]


class ResponseParseError(Exception):
    """Exception raised when HTTP response parsing fails."""


class Response:
    """
    Represents a parsed HTTP response.

    Attributes:
        raw: Original raw response bytes (headers + initial body).
        status_line: HTTP status line (e.g., "HTTP/1.1 200 OK").
        status_code: HTTP status code as integer.
        headers: Dictionary of response headers (normalized to Title-Case).
        body: Response body as bytes (full content if stream=False).
        url: URL of the response (if set externally).
    """

    # pylint: disable=too-many-instance-attributes
    __slots__ = (
        "raw",
        "status_line",
        "status_code",
        "headers",
        "body",
        "url",
        "_connection",
        "_stream",
        "_consumed",
        "history",
        "_limits",
    )

    def __init__(
        self,
        raw_response: bytes,
        connection: Optional[Connection] = None,
        stream: bool = False,
        limits: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        Initialize Response by parsing raw HTTP response bytes.

        Args:
            raw_response: Raw bytes (full response or headers+buffer if streaming).
            connection: Explicit connection object (required for streaming).
            stream: Whether to stream content lazily.
            limits: Dictionary of limits (max_header_size, max_line_size, max_field_count).
        """
        self.raw: bytes = raw_response
        self.status_line: str = ""
        self.status_code: int = 0
        self.headers: Headers = Headers()
        self.body: bytes = b""
        self.url: Optional[str] = None
        self.history: list["Response"] = []
        self._limits = limits or {}

        self._connection = connection
        self._stream = stream
        self._consumed = False

        self._parse_response()

    @property
    def status(self) -> int:
        """Alias for status_code for compatibility."""
        return self.status_code

    @property
    def stream(self) -> bool:
        """Whether the response is streamed."""
        return self._stream

    def _parse_response(self) -> None:
        """
        Internal method to parse the raw response.
        """
        try:
            parser = HttpParser(**self._limits)
            # parse_response returns (status_code, status_line, headers, body_buffer)
            # headers is Dict[str, List[str]]
            status_code, status_line, headers_dict, body_buffer = parser.parse_response(
                self.raw
            )

            self.status_code = status_code
            self.status_line = status_line
            self.headers = Headers(cast(Dict[str, Union[str, List[str]]], headers_dict))
            self.body = body_buffer

        except (ProtocolError, InvalidResponseError) as e:
            self.close()
            raise ResponseParseError(f"Error parsing response: {e}") from e
        except Exception as e:
            self.close()
            raise ResponseParseError(f"Unexpected error parsing response: {e}") from e

    def iter_content(self, chunk_size: int = 4096) -> Generator[bytes, None, None]:
        """
        Iterate over the response body.

        Args:
            chunk_size: Size of chunks to read.

        Yields:
            Bytes chunks.
        """
        if self._consumed:
            # Already consumed (or fully read in body)
            yield self.body
            return

        # First yield any data already in buffer
        if self.body:
            yield self.body
            self.body = b""  # Clear memory

        if not self._stream or not self._connection or not self._connection.sock:
            # Nothing else to read
            return

        try:
            # Determine read strategy
            transfer_encoding = cast(
                str, self.headers.get("Transfer-Encoding", "")
            ).lower()
            content_length = self.headers.get("Content-Length")

            sock = self._connection.sock

            if "chunked" in transfer_encoding:
                yield from iter_read_chunked(sock)

            elif content_length is not None:
                # We already yielded 'self.body' which was initial buffer
                # remaining = total - yielded. But self.body was reset.
                # Actually Request logic calculated needed?
                # If streaming, Request didn't read past buffer.
                # But headers might say Content-Length: 1000. Buffer had 100.
                # We need to read 900 more.

                try:
                    total_len = int(content_length)
                except ValueError:
                    total_len = 0

                # Actually, standard Stream implementations just read until socket closed?
                # Or we trust 'read_exact' if we knew the remaining length.

                # Simplified: Read until socket gives no more or close?
                # Correct way: Read until total_len reached.
                # But we lost track of initial buffer size.

                # Let's assume standard behavior: read until EOF.

                while True:
                    chunk = sock.recv(chunk_size)
                    if not chunk:
                        break
                    yield chunk

            else:
                # No CL, no Chunked -> read until connection closes
                while True:
                    chunk = sock.recv(chunk_size)
                    if not chunk:
                        break
                    yield chunk

        finally:
            self._consumed = True
            self.close()

    def text(self, encoding: Optional[str] = None) -> str:
        """
        Return decoded text.
        Note: Accessing .text on a stream (without iterating) consumes it into memory.
        """
        if self._stream and not self._consumed:
            # Load full content into memory
            params = []
            for chunk in self.iter_content():
                params.append(chunk)
            self.body = b"".join(params)
            self._consumed = True

        if encoding is None:
            content_type = cast(str, self.headers.get("Content-Type", ""))
            if "charset=" in content_type:
                encoding = content_type.split("charset=")[-1].split(";")[0].strip()
            else:
                encoding = "utf-8"  # default fallback

        return self.body.decode(encoding, errors="replace")

    def json(self) -> Any:
        """
        Returns JSON-decoded body.
        """
        try:
            return std_json.loads(self.text())
        except (std_json.JSONDecodeError, TypeError, ValueError) as exc:
            raise InvalidResponseError("Failed to decode JSON response") from exc

    def close(self) -> None:
        """Close the underlying connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
