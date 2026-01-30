"""Unit tests for reqivo.http.headers module."""

from reqivo.http.headers import Headers


class TestHeaders:
    """Tests for Headers class."""

    def test_init_empty(self):
        """Test Headers initialization with no arguments."""
        headers = Headers()
        assert headers._headers == {}

    def test_init_with_headers(self):
        """Test Headers initialization with dictionary."""
        headers = Headers({"Content-Type": "application/json", "Accept": "text/html"})
        assert headers._headers == {
            "content-type": "application/json",
            "accept": "text/html",
        }

    def test_case_insensitive_storage(self):
        """Test that header names are stored in lowercase."""
        headers = Headers({"Content-Type": "text/plain", "USER-AGENT": "test"})
        assert headers._headers == {"content-type": "text/plain", "user-agent": "test"}

    def test_get_existing_header(self):
        """Test getting an existing header value."""
        headers = Headers({"Content-Type": "application/json"})
        assert headers.get("Content-Type") == "application/json"
        assert headers.get("content-type") == "application/json"
        assert headers.get("CONTENT-TYPE") == "application/json"

    def test_get_nonexistent_header(self):
        """Test getting a non-existent header returns None."""
        headers = Headers()
        assert headers.get("X-Custom") is None

    def test_get_with_default(self):
        """Test get with default value for non-existent header."""
        headers = Headers()
        assert headers.get("X-Custom", "default_value") == "default_value"
