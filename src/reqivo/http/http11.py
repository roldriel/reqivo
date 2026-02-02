"""src/reqivo/http/http11.py

Robust HTTP Parser implementation.
"""

# pylint: disable=line-too-long

from typing import Dict, List, Optional, Tuple

from reqivo.exceptions import InvalidResponseError, ProtocolError


class HttpParser:
    """
    Robust HTTP/1.1 Parser.

    Handles:
    - Status Line parsing.
    - Header parsing with duplicate handling.
    - Defensive sizing.
    """

    def __init__(
        self,
        max_header_size: int = 8192,
        max_body_size: Optional[int] = None,
    ):
        self.max_header_size = max_header_size
        self.max_body_size = max_body_size

    def parse_response(self, data: bytes) -> Tuple[int, str, Dict[str, str], bytes]:
        """
        Parse a full raw HTTP response (or at least headers).

        Returns:
            Tuple of (status_code, status_line, headers, remaining_body)

        Raises:
            ProtocolError: If headers are too large or malformed.
            InvalidResponseError: If status line is invalid.
        """
        # Check header size limit
        if len(data) > self.max_header_size:
            # This check is heuristic; ideally we check before finding \r\n\r\n
            if b"\r\n\r\n" not in data[: self.max_header_size + 4]:
                # +4 for the delimiter itself
                raise ProtocolError(
                    f"Headers exceed maximum size of {self.max_header_size} bytes"
                )

        try:
            parts = data.split(b"\r\n\r\n", 1)
            if len(parts) < 2:
                # If we don't have the double CRLF yet, it might be incomplete.
                # But if we are called with 'data' assumed to be complete headers:
                raise InvalidResponseError(
                    "Incomplete response: headers delimiter not found"
                )

            header_bytes = parts[0]
            body_bytes = parts[1]

            header_text = header_bytes.decode("iso-8859-1")
            lines = header_text.split("\r\n")

            if not lines:
                raise InvalidResponseError("Empty response")

            # Parse Status Line
            status_line = lines[0]
            try:
                # HTTP/1.1 200 OK
                # pylint: disable=unused-variable
                proto, code, *reason = status_line.split(" ")
                status_code = int(code)
            except ValueError as exc:
                raise InvalidResponseError(
                    f"Invalid status line: {status_line}"
                ) from exc

            # Parse Headers
            headers = self._parse_headers(lines[1:])

            return status_code, status_line, headers, body_bytes

        except UnicodeDecodeError as e:
            raise ProtocolError(f"Header decoding failed: {e}") from e

    def _parse_headers(self, lines: List[str]) -> Dict[str, str]:
        """
        Parse header lines into a dictionary.
        Handles normalization and duplicates.
        """
        headers: Dict[str, str] = {}

        for line in lines:
            if not line:
                continue

            if ": " not in line:
                # Should we ignore malformed headers or raise?
                # Robustness: ignore garbage lines if tolerance is desired,
                # but strict HTTP/1.1 requires header: value.
                # Let's skip empty or invalid lines to be robust against minor noise,
                # unless strict mode is enabled.
                continue

            key, value = line.split(": ", 1)

            # Normalize Key: Title-Case
            # We want "content-type" -> "Content-Type"
            # But "ETag" -> "Etag" might be annoying.
            # Standard python http.client uses .lower() or keeps as is.
            # Reqivo v0.1 used Title-Case manual.

            normalized_key = "-".join(
                [part.capitalize() for part in key.strip().split("-")]
            )
            clean_value = value.strip()

            if normalized_key in headers:
                # Handle duplicates
                # Set-Cookie should NOT be comma-separated (RFC 6265)
                # Other headers can be combined with comma (RFC 7230)

                if normalized_key == "Set-Cookie":
                    # Set-Cookie with multiple values: keep only the last one
                    # This is a limitation of Dict[str, str] - proper fix needs List
                    # TODO: Consider using Dict[str, List[str]] for headers
                    headers[normalized_key] = clean_value
                else:
                    # Combine with comma as per RFC 7230
                    headers[normalized_key] += f", {clean_value}"
            else:
                headers[normalized_key] = clean_value

        return headers
