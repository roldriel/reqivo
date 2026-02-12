"""tests/unit/test_response_duplicates.py"""

from reqivo.client.response import Response


def test_response_duplicate_headers_joined():
    """Test that duplicate headers are joined by comma when accessed via dict/get."""
    raw = (
        b"HTTP/1.1 200 OK\r\n"
        b"Accept: text/html\r\n"
        b"Accept: application/json\r\n"
        b"\r\n"
    )
    resp = Response(raw)

    # Standard access joins them
    assert resp.headers["Accept"] == "text/html, application/json"
    assert resp.headers.get("Accept") == "text/html, application/json"


def test_response_duplicate_headers_get_all():
    """Test accessing raw list of duplicate headers."""
    raw = (
        b"HTTP/1.1 200 OK\r\n"
        b"Accept: text/html\r\n"
        b"Accept: application/json\r\n"
        b"\r\n"
    )
    resp = Response(raw)

    # get_all returns list
    assert resp.headers.get_all("Accept") == ["text/html", "application/json"]


def test_response_set_cookie_duplicates():
    """Test that Set-Cookie duplicates are NOT joined but accessible via get_all."""
    raw = (
        b"HTTP/1.1 200 OK\r\n"
        b"Set-Cookie: session=123\r\n"
        b"Set-Cookie: theme=dark\r\n"
        b"\r\n"
    )
    resp = Response(raw)

    # .get() returns only the first one (standard behavior for non-joinable headers)
    assert resp.headers["Set-Cookie"] == "session=123"

    # .get_all() returns all of them
    cookies = resp.headers.get_all("Set-Cookie")
    assert len(cookies) == 2
    assert "session=123" in cookies
    assert "theme=dark" in cookies
