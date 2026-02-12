"""tests/unit/test_limits.py

Unit tests for size limit enforcement in Response and HttpParser.
"""

import pytest

from reqivo.client.response import Response, ResponseParseError
from reqivo.http.http11 import HttpParser, ProtocolError


class TestHeightLimits:
    """Tests for configurable size limits."""

    def test_status_line_limit(self):
        """Test that exceeding max_line_size in status line raises error."""
        long_status = "HTTP/1.1 200 " + "O" * 5000
        raw = f"{long_status}\r\nContent-Length: 0\r\n\r\n".encode("iso-8859-1")

        limits = {"max_line_size": 100}

        with pytest.raises(ResponseParseError) as exc:
            Response(raw, limits=limits)

        assert "Status line too long" in str(exc.value)

    def test_header_line_limit(self):
        """Test that exceeding max_line_size in header line raises error."""
        long_header = "X-Loop: " + "A" * 5000
        raw = f"HTTP/1.1 200 OK\r\n{long_header}\r\n\r\n".encode("iso-8859-1")

        limits = {"max_line_size": 100}

        with pytest.raises(ResponseParseError) as exc:
            Response(raw, limits=limits)

        assert "Header line too long" in str(exc.value)

    def test_field_count_limit(self):
        """Test that exceeding max_field_count raises error."""
        headers = "\r\n".join([f"H-{i}: v" for i in range(15)])
        raw = f"HTTP/1.1 200 OK\r\n{headers}\r\n\r\n".encode("iso-8859-1")

        limits = {"max_field_count": 10}

        with pytest.raises(ResponseParseError) as exc:
            Response(raw, limits=limits)

        assert "Too many header fields" in str(exc.value)

    def test_parse_response_success_within_limits(self):
        """Test that parsing succeeds when within limits."""
        raw = b"HTTP/1.1 200 OK\r\nH1: 1\r\nH2: 2\r\n\r\n"

        limits = {"max_field_count": 5, "max_line_size": 100}

        try:
            resp = Response(raw, limits=limits)
            assert resp.status_code == 200
        except ResponseParseError:
            pytest.fail("Should not raise error within limits")
