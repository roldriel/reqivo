"""Unit tests for reqivo.http.url module."""

from reqivo.http.url import URL


class TestURL:
    """Tests for URL class."""

    def test_parse_http_url(self):
        """Test parsing basic HTTP URL."""
        url = URL("http://example.com/path")
        assert url.scheme == "http"
        assert url.host == "example.com"
        assert url.port is None  # Default HTTP port not explicitly set
        assert url.path == "/path"

    def test_parse_https_url(self):
        """Test parsing HTTPS URL."""
        url = URL("https://secure.example.com/api")
        assert url.scheme == "https"
        assert url.host == "secure.example.com"
        assert url.port is None
        assert url.path == "/api"

    def test_parse_url_with_port(self):
        """Test parsing URL with explicit port."""
        url = URL("http://example.com:8080/path")
        assert url.scheme == "http"
        assert url.host == "example.com"
        assert url.port == 8080
        assert url.path == "/path"

    def test_parse_url_without_path(self):
        """Test parsing URL without path."""
        url = URL("http://example.com")
        assert url.scheme == "http"
        assert url.host == "example.com"
        assert url.path == ""

    def test_parse_url_with_query(self):
        """Test URL parsing preserves query string in parsed object."""
        url = URL("http://example.com/path?key=value")
        assert url.parsed.query == "key=value"
        assert url.path == "/path"
