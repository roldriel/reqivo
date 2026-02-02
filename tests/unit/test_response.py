"""tests/unit/test_response.py"""

import json
from unittest import mock

import pytest

from reqivo.client.response import Response, ResponseParseError
from reqivo.exceptions import InvalidResponseError


def test_response_initialization():
    """Test basic initialization and parsing."""
    raw = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 13\r\n\r\nHello, World!"
    resp = Response(raw)

    assert resp.status_code == 200
    assert resp.status == 200
    assert resp.status_line == "HTTP/1.1 200 OK"
    assert resp.headers["Content-Type"] == "text/plain"
    assert resp.headers["Content-Length"] == "13"
    assert resp.body == b"Hello, World!"


def test_response_headers_normalization():
    """Test that headers are normalized to Title-Case."""
    raw = (
        b"HTTP/1.1 200 OK\r\ncontent-type: text/plain\r\nX-CUSTOM-HEADER: value\r\n\r\n"
    )
    resp = Response(raw)

    assert "Content-Type" in resp.headers
    assert "X-Custom-Header" in resp.headers
    assert resp.headers["Content-Type"] == "text/plain"
    assert resp.headers["X-Custom-Header"] == "value"


def test_response_text_default_encoding():
    """Test text() with default UTF-8 encoding."""
    raw = b"HTTP/1.1 200 OK\r\n\r\n\xc3\xa1"  # 'á' in UTF-8
    resp = Response(raw)
    assert resp.text() == "á"


def test_response_text_custom_encoding():
    """Test text() with custom encoding from headers."""
    raw = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=iso-8859-1\r\n\r\n\xe1"  # 'á' in ISO-8859-1
    resp = Response(raw)
    assert resp.text() == "á"


def test_response_json():
    """Test json() parsing."""
    data = {"key": "value", "number": 123}
    raw = f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{json.dumps(data)}".encode()
    resp = Response(raw)
    assert resp.json() == data


def test_response_json_invalid():
    """Test json() with invalid content."""
    raw = b"HTTP/1.1 200 OK\r\n\r\nNot JSON"
    resp = Response(raw)
    with pytest.raises(InvalidResponseError, match="Failed to decode JSON response"):
        resp.json()


def test_response_parse_error():
    """Test handling of malformed HTTP responses."""
    raw = b"Not an HTTP response"
    with pytest.raises(ResponseParseError):
        Response(raw)


def test_response_iter_content_non_streamed():
    """Test iter_content() for non-streamed responses."""
    raw = b"HTTP/1.1 200 OK\r\n\r\nBody Content"
    resp = Response(raw)
    chunks = list(resp.iter_content())
    assert chunks == [b"Body Content"]

    # Test second call (should return buffered body if not cleared, but Response clears it)
    # Actually Response.iter_content clears self.body if consumed.
    assert b"".join(resp.iter_content()) == b""


def test_response_slots():
    """Verify that Response uses __slots__ to save memory."""
    raw = b"HTTP/1.1 200 OK\r\n\r\n"
    resp = Response(raw)
    with pytest.raises(AttributeError):
        resp.arbitrary_attribute = "oops"


def test_response_unexpected_parse_error(monkeypatch):
    """Test handling of unexpected errors during parsing."""
    from reqivo.http.http11 import HttpParser

    def mock_parse(self, data):
        raise RuntimeError("Unexpected boom")

    monkeypatch.setattr(HttpParser, "parse_response", mock_parse)

    with pytest.raises(ResponseParseError, match="Unexpected error parsing response"):
        Response(b"some data")


def test_response_iter_content_double_iteration():
    """Test calling iter_content twice on non-streamed response."""
    raw = b"HTTP/1.1 200 OK\r\n\r\nContent"
    resp = Response(raw)

    # First iteration yields content
    chunks1 = list(resp.iter_content())
    assert chunks1 == [b"Content"]

    # Second iteration yields nothing (buffer cleared)
    chunks2 = list(resp.iter_content())
    assert chunks2 == []


def test_response_close():
    """Test closing the response closes the connection."""

    class MockConnection:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    conn = MockConnection()
    raw = b"HTTP/1.1 200 OK\r\n\r\n"
    resp = Response(raw, connection=conn)

    resp.close()
    assert conn.closed is True
    assert resp._connection is None


def test_response_iter_content_chunked_encoding():
    """Test iter_content with chunked transfer encoding."""

    class MockConnection:
        def __init__(self):
            self.sock = mock.Mock()
            # Chunked response: "5\r\nHello\r\n0\r\n\r\n"
            self.sock.recv.side_effect = [
                b"5",
                b"\r",
                b"\n",
                b"Hello",
                b"\r\n",
                b"0",
                b"\r",
                b"\n",
                b"\r\n",
            ]

        def close(self):
            pass

    conn = MockConnection()
    raw = b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n"
    resp = Response(raw, connection=conn, stream=True)

    chunks = list(resp.iter_content())
    assert chunks == [b"Hello"]
    assert resp._consumed is True


def test_response_iter_content_with_content_length():
    """Test iter_content with Content-Length header."""

    class MockConnection:
        def __init__(self):
            self.sock = mock.Mock()
            # Simulate reading additional content
            self.sock.recv.side_effect = [b"More ", b"data", b""]

        def close(self):
            pass

    conn = MockConnection()
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: 9\r\n\r\n"
    resp = Response(raw, connection=conn, stream=True)

    chunks = list(resp.iter_content())
    # Should read until the socket closes
    assert b"".join(chunks) == b"More data"


def test_response_iter_content_no_length_no_chunked():
    """Test iter_content with no Content-Length and no chunked encoding."""

    class MockConnection:
        def __init__(self):
            self.sock = mock.Mock()
            # Read until the connection closes
            self.sock.recv.side_effect = [b"Some ", b"content", b""]

        def close(self):
            pass

    conn = MockConnection()
    raw = b"HTTP/1.1 200 OK\r\n\r\n"
    resp = Response(raw, connection=conn, stream=True)

    chunks = list(resp.iter_content(chunk_size=1024))
    assert b"".join(chunks) == b"Some content"


def test_response_text_streaming():
    """Test text() method on streaming response consumes it."""

    class MockConnection:
        def __init__(self):
            self.sock = mock.Mock()
            self.sock.recv.side_effect = [b"Stream ", b"data", b""]

        def close(self):
            pass

    conn = MockConnection()
    raw = b"HTTP/1.1 200 OK\r\n\r\n"
    resp = Response(raw, connection=conn, stream=True)

    # Calling text() should consume the stream
    text = resp.text()
    assert text == "Stream data"
    assert resp._consumed is True
    # Body should now contain the full content
    assert resp.body == b"Stream data"


def test_response_iter_content_invalid_content_length():
    """Test iter_content with invalid Content-Length value."""

    class MockConnection:
        def __init__(self):
            self.sock = mock.Mock()
            self.sock.recv.side_effect = [b"data", b""]

        def close(self):
            pass

    conn = MockConnection()
    raw = b"HTTP/1.1 200 OK\r\nContent-Length: invalid\r\n\r\n"
    resp = Response(raw, connection=conn, stream=True)

    # Should handle invalid content-length gracefully
    chunks = list(resp.iter_content())
    assert b"".join(chunks) == b"data"


def test_response_iter_content_custom_chunk_size():
    """Test iter_content with custom chunk_size parameter."""

    class MockConnection:
        def __init__(self):
            self.sock = mock.Mock()
            self.sock.recv.side_effect = [b"AB", b"CD", b""]
            self.closed = False

        def close(self):
            self.closed = True

    conn = MockConnection()
    raw = b"HTTP/1.1 200 OK\r\n\r\n"
    resp = Response(raw, connection=conn, stream=True)

    # Request custom chunk size
    chunks = list(resp.iter_content(chunk_size=2))
    assert chunks == [b"AB", b"CD"]


def test_response_stream_property():
    """Test the stream property getter."""
    raw = b"HTTP/1.1 200 OK\r\n\r\nBody"

    # Non-streamed response
    resp = Response(raw, stream=False)
    assert resp.stream is False

    # Streamed response
    resp_stream = Response(raw, stream=True)
    assert resp_stream.stream is True


def test_response_iter_content_when_already_consumed():
    """Test iter_content when already consumed yields remaining body."""

    class MockConnection:
        def __init__(self):
            self.sock = mock.Mock()
            self.sock.recv.side_effect = [b"StreamData", b""]

        def close(self):
            pass

    conn = MockConnection()
    raw = b"HTTP/1.1 200 OK\r\n\r\n"
    resp = Response(raw, connection=conn, stream=True)

    # Call text() to consume stream and populate body
    text_result = resp.text()
    assert text_result == "StreamData"
    assert resp._consumed is True
    assert resp.body == b"StreamData"

    # Now calling iter_content() on consumed response should yield body (lines 125-126)
    chunks = list(resp.iter_content())
    assert chunks == [b"StreamData"]
