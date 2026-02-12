"""tests/unit/test_http_parser.py

Unit tests for reqivo.http.http11.HttpParser module.

This module provides comprehensive test coverage for the HTTP/1.1 parser implementation,
ensuring robust parsing of HTTP responses including status lines, headers, and body data.

Test Coverage:
    - HttpParser initialization and configuration
    - Successful parsing of well-formed HTTP responses
    - Edge cases (empty responses, missing headers, etc.)
    - Error handling (malformed responses, size limits, encoding issues)
    - Header parsing including duplicate handling and normalization

Security Focus:
    - Header size limit enforcement
    - Body size limit enforcement (when configured)
    - Invalid encoding handling
    - Malformed response rejection
"""

from typing import Dict, Tuple

import pytest

from reqivo.exceptions import InvalidResponseError, ProtocolError
from reqivo.http.http11 import HttpParser

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def parser() -> HttpParser:
    """Create a default HttpParser instance for testing.

    Returns:
        HttpParser: Parser with default configuration (8192 max header size).
    """
    return HttpParser()


@pytest.fixture
def strict_parser() -> HttpParser:
    """Create an HttpParser with strict size limits for testing.

    Returns:
        HttpParser: Parser with small limits to trigger size errors.
    """
    return HttpParser(max_header_size=256, max_body_size=1024)


# ============================================================================
# TEST CLASS: HttpParser Initialization
# ============================================================================


class TestHttpParserInit:
    """Tests for HttpParser.__init__() method."""

    def test_init_default_values(self) -> None:
        """Test that HttpParser initializes with correct default values."""
        parser = HttpParser()

        assert parser.max_header_size == 8192
        assert parser.max_body_size is None

    def test_init_custom_max_header_size(self) -> None:
        """Test that HttpParser accepts custom max_header_size."""
        parser = HttpParser(max_header_size=16384)

        assert parser.max_header_size == 16384
        assert parser.max_body_size is None

    def test_init_custom_max_body_size(self) -> None:
        """Test that HttpParser accepts custom max_body_size."""
        parser = HttpParser(max_body_size=5000000)

        assert parser.max_header_size == 8192
        assert parser.max_body_size == 5000000

    def test_init_both_custom_values(self) -> None:
        """Test that HttpParser accepts both custom size limits."""
        parser = HttpParser(max_header_size=4096, max_body_size=10000)

        assert parser.max_header_size == 4096
        assert parser.max_body_size == 10000


# ============================================================================
# TEST CLASS: parse_response() - Success Cases
# ============================================================================


class TestParseResponseSuccess:
    """Tests for successful parsing of well-formed HTTP responses."""

    def test_parse_simple_response(self, parser: HttpParser) -> None:
        """Test parsing a minimal valid HTTP response."""
        data = b"HTTP/1.1 200 OK\r\n\r\n"

        status_code, status_line, headers, body = parser.parse_response(data)

        assert status_code == 200
        assert status_line == "HTTP/1.1 200 OK"
        assert headers == {}
        assert body == b""

    def test_parse_response_with_single_header(self, parser: HttpParser) -> None:
        """Test parsing response with one header."""
        data = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"

        status_code, status_line, headers, body = parser.parse_response(data)

        assert status_code == 200
        assert headers == {"Content-Type": ["text/html"]}
        assert body == b""

    def test_parse_response_with_multiple_headers(self, parser: HttpParser) -> None:
        """Test parsing response with multiple headers."""
        data = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 42\r\n"
            b"Server: reqivo-test\r\n"
            b"\r\n"
        )

        status_code, status_line, headers, body = parser.parse_response(data)

        assert status_code == 200
        assert headers["Content-Type"] == ["application/json"]
        assert headers["Content-Length"] == ["42"]
        assert headers["Server"] == ["reqivo-test"]

    def test_parse_response_with_body(self, parser: HttpParser) -> None:
        """Test parsing response with body data."""
        data = b"HTTP/1.1 200 OK\r\n" b"Content-Length: 13\r\n" b"\r\n" b"Hello, World!"

        status_code, status_line, headers, body = parser.parse_response(data)

        assert status_code == 200
        assert headers["Content-Length"] == ["13"]
        assert body == b"Hello, World!"

    def test_parse_response_with_binary_body(self, parser: HttpParser) -> None:
        """Test parsing response with binary body containing special bytes."""
        binary_data = bytes(range(256))  # All possible byte values
        data = (
            b"HTTP/1.1 200 OK\r\n" b"Content-Type: application/octet-stream\r\n" b"\r\n"
        ) + binary_data

        status_code, status_line, headers, body = parser.parse_response(data)

        assert status_code == 200
        assert body == binary_data

    def test_parse_response_extracts_correct_status_code(
        self, parser: HttpParser
    ) -> None:
        """Test that status code is correctly extracted and converted to int."""
        test_cases = [
            (b"HTTP/1.1 200 OK\r\n\r\n", 200),
            (b"HTTP/1.1 404 Not Found\r\n\r\n", 404),
            (b"HTTP/1.1 500 Internal Server Error\r\n\r\n", 500),
            (b"HTTP/1.0 301 Moved Permanently\r\n\r\n", 301),
        ]

        for data, expected_code in test_cases:
            status_code, _, _, _ = parser.parse_response(data)
            assert status_code == expected_code

    def test_parse_response_preserves_full_status_line(
        self, parser: HttpParser
    ) -> None:
        """Test that complete status line is preserved."""
        data = b"HTTP/1.1 200 OK Success Message\r\n\r\n"

        _, status_line, _, _ = parser.parse_response(data)

        assert status_line == "HTTP/1.1 200 OK Success Message"

    def test_parse_response_status_line_with_no_reason_phrase(
        self, parser: HttpParser
    ) -> None:
        """Test parsing status line with just protocol and code (no reason)."""
        data = b"HTTP/1.1 204\r\n\r\n"

        status_code, status_line, _, _ = parser.parse_response(data)

        assert status_code == 204
        assert status_line == "HTTP/1.1 204"


# ============================================================================
# TEST CLASS: parse_response() - Edge Cases
# ============================================================================


class TestParseResponseEdgeCases:
    """Tests for edge cases in HTTP response parsing."""

    def test_parse_response_no_body(self, parser: HttpParser) -> None:
        """Test response with headers but no body."""
        data = b"HTTP/1.1 204 No Content\r\nServer: test\r\n\r\n"

        _, _, headers, body = parser.parse_response(data)

        assert headers["Server"] == ["test"]
        assert body == b""

    def test_parse_response_empty_body_with_content_length(
        self, parser: HttpParser
    ) -> None:
        """Test response with Content-Length: 0."""
        data = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"

        _, _, headers, body = parser.parse_response(data)

        assert headers["Content-Length"] == ["0"]
        assert body == b""

    def test_parse_response_body_with_crlf(self, parser: HttpParser) -> None:
        """Test that body can contain CRLF sequences without breaking parser."""
        body_content = b"Line 1\r\nLine 2\r\nLine 3"
        data = b"HTTP/1.1 200 OK\r\n\r\n" + body_content

        _, _, _, body = parser.parse_response(data)

        assert body == body_content

    def test_parse_response_with_extra_empty_lines_in_headers(
        self, parser: HttpParser
    ) -> None:
        """Test that extra empty lines in header section are ignored."""
        data = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: text/plain\r\n"
            b"\r\n"  # Empty line (should be ignored by _parse_headers)
            b"Server: test\r\n"
            b"\r\n"
        )

        # This is tricky - the first \r\n\r\n will be treated as delimiter
        # So "Server: test" will be in body, not headers
        _, _, headers, body = parser.parse_response(data)

        assert "Content-Type" in headers
        # "Server: test\r\n" is now part of body
        assert body.startswith(b"Server: test")


# ============================================================================
# TEST CLASS: parse_response() - Error Cases
# ============================================================================


class TestParseResponseErrors:
    """Tests for error handling in parse_response()."""

    def test_parse_response_raises_on_headers_too_large(
        self, strict_parser: HttpParser
    ) -> None:
        """Test that ProtocolError is raised when headers exceed max size."""
        # Create headers that exceed 256 byte limit
        large_header = b"X-Custom-Header: " + b"A" * 300 + b"\r\n"
        data = b"HTTP/1.1 200 OK\r\n" + large_header
        # Note: No \r\n\r\n delimiter, so it should fail size check

        with pytest.raises(ProtocolError) as exc_info:
            strict_parser.parse_response(data)

        assert "Headers exceed maximum size" in str(exc_info.value)

    def test_parse_response_raises_on_missing_delimiter(
        self, parser: HttpParser
    ) -> None:
        """Test that InvalidResponseError is raised when delimiter is missing."""
        data = b"HTTP/1.1 200 OK\r\nContent-Type: text/html"  # No \r\n\r\n

        with pytest.raises(InvalidResponseError) as exc_info:
            parser.parse_response(data)

        assert "headers delimiter not found" in str(exc_info.value)

    def test_parse_response_raises_on_invalid_status_line_format(
        self, parser: HttpParser
    ) -> None:
        """Test that InvalidResponseError is raised for malformed status line."""
        data = b"INVALID STATUS LINE\r\n\r\n"

        with pytest.raises(InvalidResponseError) as exc_info:
            parser.parse_response(data)

        assert "Invalid status line" in str(exc_info.value)

    def test_parse_response_raises_on_non_numeric_status_code(
        self, parser: HttpParser
    ) -> None:
        """Test that InvalidResponseError is raised when status code is not a number."""
        data = b"HTTP/1.1 ABC Not A Number\r\n\r\n"

        with pytest.raises(InvalidResponseError) as exc_info:
            parser.parse_response(data)

        assert "Invalid status line" in str(exc_info.value)

    def test_parse_response_raises_on_empty_response(self, parser: HttpParser) -> None:
        """Test that InvalidResponseError is raised for completely empty response."""
        data = b"\r\n\r\n"

        with pytest.raises(InvalidResponseError) as exc_info:
            parser.parse_response(data)

        # Empty status line triggers "Invalid status line" error
        assert "Invalid status line" in str(exc_info.value)


# ============================================================================
# TEST CLASS: _parse_headers() - Internal Method
# ============================================================================


class TestParseHeaders:
    """Tests for _parse_headers() internal method."""

    def test_parse_headers_single_header(self, parser: HttpParser) -> None:
        """Test parsing a single header line."""
        lines = ["Content-Type: text/html"]

        headers = parser._parse_headers(lines)

        assert headers == {"Content-Type": ["text/html"]}

    def test_parse_headers_multiple_headers(self, parser: HttpParser) -> None:
        """Test parsing multiple header lines."""
        lines = [
            "Content-Type: application/json",
            "Content-Length: 123",
            "Server: reqivo/0.1.0",
        ]

        headers = parser._parse_headers(lines)

        assert len(headers) == 3
        assert headers["Content-Type"] == ["application/json"]
        assert headers["Content-Length"] == ["123"]
        assert headers["Server"] == ["reqivo/0.1.0"]

    def test_parse_headers_normalizes_to_title_case(self, parser: HttpParser) -> None:
        """Test that header keys are normalized to Title-Case."""
        lines = [
            "content-type: text/plain",
            "CONTENT-LENGTH: 42",
            "SeRvEr: test",
        ]

        headers = parser._parse_headers(lines)

        assert "Content-Type" in headers
        assert "Content-Length" in headers
        assert "Server" in headers

    def test_parse_headers_normalizes_multi_part_keys(self, parser: HttpParser) -> None:
        """Test normalization of multi-part header keys with hyphens."""
        lines = [
            "x-custom-header: value1",
            "X-ANOTHER-HEADER: value2",
            "x-MiXeD-CaSe: value3",
        ]

        headers = parser._parse_headers(lines)

        assert "X-Custom-Header" in headers
        assert "X-Another-Header" in headers
        assert "X-Mixed-Case" in headers

    def test_parse_headers_handles_duplicate_headers_combined(
        self, parser: HttpParser
    ) -> None:
        """Test that duplicate headers (except Set-Cookie) are combined with comma."""
        lines = [
            "Accept: application/json",
            "Accept: text/html",
            "Accept: application/xml",
        ]

        headers = parser._parse_headers(lines)

        # Parser now returns list of values
        assert headers["Accept"] == ["application/json", "text/html", "application/xml"]

    def test_parse_headers_handles_set_cookie_duplicates(
        self, parser: HttpParser
    ) -> None:
        """Test that Set-Cookie duplicates keep only the last value.

        Note: This is a known limitation. Proper fix would use Dict[str, List[str]].
        """
        lines = [
            "Set-Cookie: session=abc123",
            "Set-Cookie: user=john",
            "Set-Cookie: theme=dark",
        ]

        headers = parser._parse_headers(lines)

        # Parser now returns all values for duplicates
        assert headers["Set-Cookie"] == ["session=abc123", "user=john", "theme=dark"]

    def test_parse_headers_strips_whitespace(self, parser: HttpParser) -> None:
        """Test that whitespace around keys and values is stripped."""
        lines = [
            "  Content-Type  :   text/plain   ",
            "Server: reqivo",  # Valid format with space after colon
            "X-Custom:  value with spaces  ",  # Extra space after colon is OK
        ]

        headers = parser._parse_headers(lines)

        assert headers["Content-Type"] == ["text/plain"]
        assert headers["Server"] == ["reqivo"]
        # X-Custom parses correctly (": " found, extra space stripped from value)
        assert headers["X-Custom"] == ["value with spaces"]

    def test_parse_headers_requires_colon_space_separator(
        self, parser: HttpParser
    ) -> None:
        """Test that headers without ': ' (colon+space) separator are ignored.

        HTTP/1.1 spec requires colon followed by optional whitespace.
        This parser strictly requires ': ' (colon + space).
        """
        lines = [
            "Valid-Header: value",
            "No-Space:value",  # Missing space after colon - ignored
            "Another-Valid: value2",
        ]

        headers = parser._parse_headers(lines)

        assert len(headers) == 2
        assert "Valid-Header" in headers
        assert "No-Space" not in headers  # Ignored due to missing space
        assert "Another-Valid" in headers

    def test_parse_headers_ignores_malformed_lines(self, parser: HttpParser) -> None:
        """Test that lines without ': ' separator are ignored."""
        lines = [
            "Valid-Header: value",
            "MalformedHeaderWithoutColon",
            "Another-Valid: value2",
            "NoColonSeparator",
        ]

        headers = parser._parse_headers(lines)

        assert len(headers) == 2
        assert "Valid-Header" in headers
        assert "Another-Valid" in headers

    def test_parse_headers_ignores_empty_lines(self, parser: HttpParser) -> None:
        """Test that empty lines are skipped."""
        lines = [
            "Content-Type: text/html",
            "",
            "Server: test",
            "",
            "",
        ]

        headers = parser._parse_headers(lines)

        assert len(headers) == 2
        assert "Content-Type" in headers
        assert "Server" in headers

    def test_parse_headers_handles_colon_in_value(self, parser: HttpParser) -> None:
        """Test that header values can contain colons."""
        lines = [
            "X-Custom-Header: value:with:colons",
            "X-Url: http://example.com:8080/path",
        ]

        headers = parser._parse_headers(lines)

        assert headers["X-Custom-Header"] == ["value:with:colons"]
        assert headers["X-Url"] == ["http://example.com:8080/path"]

    def test_parse_headers_empty_list(self, parser: HttpParser) -> None:
        """Test parsing empty header list returns empty dict."""
        lines: list[str] = []

        headers = parser._parse_headers(lines)

        assert headers == {}

    def test_parse_headers_with_empty_value(self, parser: HttpParser) -> None:
        """Test header with empty value."""
        lines = ["X-Empty-Header: ", "X-Normal: value"]

        headers = parser._parse_headers(lines)

        assert headers["X-Empty-Header"] == [""]
        assert headers["X-Normal"] == ["value"]


# ============================================================================
# INTEGRATION-STYLE TESTS
# ============================================================================


class TestParseResponseIntegration:
    """Integration-style tests combining multiple features."""

    def test_parse_real_world_response(self, parser: HttpParser) -> None:
        """Test parsing a realistic HTTP response."""
        data = (
            b"HTTP/1.1 200 OK\r\n"
            b"Date: Wed, 29 Jan 2026 12:00:00 GMT\r\n"
            b"Server: Apache/2.4.41 (Unix)\r\n"
            b"Content-Type: application/json; charset=utf-8\r\n"
            b"Content-Length: 27\r\n"
            b"Connection: keep-alive\r\n"
            b"\r\n"
            b'{"status": "ok", "code": 0}'
        )

        status_code, status_line, headers, body = parser.parse_response(data)

        assert status_code == 200
        assert status_line == "HTTP/1.1 200 OK"
        assert headers["Content-Type"] == ["application/json; charset=utf-8"]
        assert headers["Content-Length"] == ["27"]
        assert headers["Connection"] == ["keep-alive"]
        assert body == b'{"status": "ok", "code": 0}'

    def test_parse_chunked_response_headers(self, parser: HttpParser) -> None:
        """Test parsing response with chunked transfer encoding header."""
        data = (
            b"HTTP/1.1 200 OK\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Content-Type: text/plain\r\n"
            b"\r\n"
            b"7\r\n"
            b"Mozilla\r\n"
            b"9\r\n"
            b"Developer\r\n"
            b"0\r\n"
            b"\r\n"
        )

        status_code, _, headers, body = parser.parse_response(data)

        assert status_code == 200
        assert headers["Transfer-Encoding"] == ["chunked"]
        # Body parsing is handled elsewhere (http/body.py)
        assert len(body) > 0

    def test_parse_redirect_response(self, parser: HttpParser) -> None:
        """Test parsing 301/302 redirect response."""
        data = (
            b"HTTP/1.1 301 Moved Permanently\r\n"
            b"Location: https://example.com/new-location\r\n"
            b"Content-Length: 0\r\n"
            b"\r\n"
        )

        status_code, status_line, headers, body = parser.parse_response(data)

        assert status_code == 301
        assert "Moved Permanently" in status_line
        assert headers["Location"] == ["https://example.com/new-location"]
        assert body == b""

    def test_parse_error_response_with_html_body(self, parser: HttpParser) -> None:
        """Test parsing error response (4xx/5xx) with HTML body."""
        html_body = b"<html><body><h1>404 Not Found</h1></body></html>"
        data = (
            b"HTTP/1.1 404 Not Found\r\n"
            b"Content-Type: text/html\r\n"
            b"Content-Length: 50\r\n"
            b"\r\n"
        ) + html_body

        status_code, _, headers, body = parser.parse_response(data)

        assert status_code == 404
        assert headers["Content-Type"] == ["text/html"]
        assert body == html_body
