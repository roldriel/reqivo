"""tests/unit/test_headers.py"""

import pytest

from reqivo.http.headers import Headers


class TestHeaders:
    """Tests for Headers class."""

    def test_init_empty(self):
        """Test Headers initialization with no arguments."""
        headers = Headers()
        assert headers._headers == {}
        assert len(headers) == 0

    def test_init_with_dict(self):
        """Test Headers initialization with string dictionary."""
        headers = Headers({"Content-Type": "application/json", "Accept": "text/html"})
        # Internal storage should be lists
        assert headers._headers == {
            "content-type": ["application/json"],
            "accept": ["text/html"],
        }

    def test_init_with_lists(self):
        """Test Headers initialization with list dictionary."""
        headers = Headers(
            {
                "Cache-Control": ["no-cache", "no-store"],
                "Accept": ["text/html", "application/json"],
            }
        )
        assert headers._headers == {
            "cache-control": ["no-cache", "no-store"],
            "accept": ["text/html", "application/json"],
        }

    def test_case_insensitive_storage(self):
        """Test that header names are stored in lowercase."""
        headers = Headers({"Content-Type": "text/plain", "USER-AGENT": "test"})
        assert "content-type" in headers._headers
        assert "user-agent" in headers._headers

    def test_get_simple(self):
        """Test getting a simple header value."""
        headers = Headers({"Content-Type": "application/json"})
        assert headers.get("Content-Type") == "application/json"
        assert headers["Content-Type"] == "application/json"

    def test_get_duplicate_headers_joined(self):
        """Test that get() joins duplicates with commas."""
        headers = Headers({"Accept": ["text/html", "application/json"]})
        assert headers.get("Accept") == "text/html, application/json"
        assert headers["Accept"] == "text/html, application/json"

    def test_get_set_cookie_special_handling(self):
        """Test that get() for Set-Cookie returns only first value (no join)."""
        headers = Headers({"Set-Cookie": ["session=123", "user=alice"]})
        # Should NOT join with comma
        assert headers.get("Set-Cookie") == "session=123"
        assert headers["Set-Cookie"] == "session=123"

    def test_get_all(self):
        """Test get_all() returns all values."""
        headers = Headers({"Set-Cookie": ["session=123", "user=alice"]})
        assert headers.get_all("Set-Cookie") == ["session=123", "user=alice"]
        assert headers.get_all("Non-Existent") == []

    def test_getitem_raises_keyerror(self):
        """Test __getitem__ raises KeyError for missing header."""
        headers = Headers()
        with pytest.raises(KeyError):
            _ = headers["Missing"]

    def test_iteration(self):
        """Test iteration over headers."""
        headers = Headers({"A": "1", "B": "2"})
        keys = list(headers)
        assert "a" in keys
        assert "b" in keys
        assert len(keys) == 2

    def test_len(self):
        """Test len() returns number of headers."""
        headers = Headers({"A": "1", "B": "2"})
        assert len(headers) == 2
