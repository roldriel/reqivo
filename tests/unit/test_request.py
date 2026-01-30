"""tests/unit/test_request.py"""

from unittest.mock import MagicMock, patch

import pytest

from reqivo.client.request import AsyncRequest, Request
from reqivo.exceptions import NetworkError, RequestError
from reqivo.transport.connection import AsyncConnection, Connection


def test_build_request_basic():
    """Test standard GET request building."""
    raw = Request.build_request("GET", "/", "example.com", {}, None)
    assert b"GET / HTTP/1.1\r\n" in raw
    assert b"Host: example.com\r\n" in raw
    assert b"User-Agent: reqivo/0.1\r\n" in raw
    assert b"Connection: close\r\n" in raw


def test_build_request_with_body():
    """Test POST request building with body and Content-Length."""
    body = "hello"
    raw = Request.build_request(
        "POST", "/api", "api.com", {"Content-Type": "text/plain"}, body
    )
    assert b"POST /api HTTP/1.1\r\n" in raw
    assert b"Content-Type: text/plain\r\n" in raw
    assert b"Content-Length: 5\r\n" in raw
    assert b"\r\n\r\nhello" in raw


def test_build_request_invalid_headers():
    """Test validation of header characters."""
    with pytest.raises(ValueError, match="Invalid character in header"):
        Request.build_request("GET", "/", "host", {"X-Broken": "val\nline"}, None)


def test_send_basic_mock():
    """Test send() with mocked Connection and Socket."""
    mock_response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nhi"

    with patch("reqivo.client.request.Connection") as mock_conn_cls:
        mock_conn = mock_conn_cls.return_value
        mock_sock = MagicMock()

        # Initially no socket
        mock_conn.sock = None

        # When open() is called, set the socket
        def open_side_effect():
            mock_conn.sock = mock_sock

        mock_conn.open.side_effect = open_side_effect

        # Mock sock.recv to return data then empty
        mock_sock.recv.side_effect = [mock_response, b""]

        resp = Request.send("GET", "http://example.com/")

        assert resp.status_code == 200
        assert resp.body == b"hi"
        mock_sock.sendall.assert_called()
        mock_conn.open.assert_called_once()
        mock_conn.close.assert_called_once()


def test_send_invalid_url():
    """Test send() with invalid host."""
    with pytest.raises(RequestError, match="Invalid URL"):
        Request.send("GET", "not-a-url")


def test_send_server_closed_immediately():
    """Test handling of empty response."""
    with patch("reqivo.client.request.Connection") as mock_conn_cls:
        mock_conn = mock_conn_cls.return_value
        mock_sock = MagicMock()
        mock_conn.sock = None

        def open_side_effect():
            mock_conn.sock = mock_sock

        mock_conn.open.side_effect = open_side_effect
        mock_sock.recv.return_value = b""

        with pytest.raises(NetworkError, match="Server closed connection"):
            Request.send("GET", "http://example.com/")


def test_send_failed_to_open_connection():
    """Test NetworkError when connection fails to open (sock remains None)."""
    with patch("reqivo.client.request.Connection") as mock_conn_cls:
        mock_conn = mock_conn_cls.return_value
        mock_conn.sock = None

        # open() is called but sock remains None (connection failed silently)
        def open_no_sock():
            pass  # sock remains None

        mock_conn.open.side_effect = open_no_sock

        with pytest.raises(NetworkError, match="Failed to open connection"):
            Request.send("GET", "http://example.com/")


def test_convenience_methods():
    """Test get() and post() wrappers."""
    with patch.object(Request, "send") as mock_send:
        Request.get("http://ex.com/get", headers={"X-A": "1"})
        mock_send.assert_called_with(
            "GET", "http://ex.com/get", headers={"X-A": "1"}, timeout=5, connection=None
        )

        Request.post("http://ex.com/post", body="data")
        mock_send.assert_called_with(
            "POST",
            "http://ex.com/post",
            headers=None,
            body="data",
            timeout=5,
            connection=None,
        )


def test_build_request_null_byte_in_header():
    """Test that null bytes in headers raise ValueError."""
    with pytest.raises(ValueError, match="Null byte in header"):
        Request.build_request("GET", "/", "host", {"X-Bad": "value\x00bad"}, None)


def test_build_request_with_bytes_body():
    """Test building request with bytes body."""
    body = b"binary data"
    raw = Request.build_request("POST", "/api", "api.com", {}, body)
    assert b"Content-Length: 11\r\n" in raw
    assert b"\r\n\r\nbinary data" in raw


def test_send_with_query_string():
    """Test send() with URL containing query parameters."""
    mock_response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"

    with patch("reqivo.client.request.Connection") as mock_conn_cls:
        mock_conn = mock_conn_cls.return_value
        mock_sock = MagicMock()
        mock_conn.sock = None

        def open_side_effect():
            mock_conn.sock = mock_sock

        mock_conn.open.side_effect = open_side_effect
        mock_sock.recv.side_effect = [mock_response, b""]

        resp = Request.send("GET", "http://example.com/path?foo=bar&baz=qux")

        # Verify query string was included in request
        call_args = mock_sock.sendall.call_args[0][0]
        assert b"GET /path?foo=bar&baz=qux HTTP/1.1\r\n" in call_args


def test_send_with_timeout_object():
    """Test send() with Timeout object instead of float."""
    from reqivo.utils.timing import Timeout

    mock_response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"

    with patch("reqivo.client.request.Connection") as mock_conn_cls:
        mock_conn = mock_conn_cls.return_value
        mock_sock = MagicMock()
        mock_conn.sock = None

        def open_side_effect():
            mock_conn.sock = mock_sock

        mock_conn.open.side_effect = open_side_effect
        mock_sock.recv.side_effect = [mock_response, b""]

        timeout_obj = Timeout(connect=5.0, read=10.0, total=30.0)
        resp = Request.send("GET", "http://example.com/", timeout=timeout_obj)

        assert resp.status_code == 200


def test_send_with_existing_connection():
    """Test send() with pre-existing connection (reuse)."""
    mock_response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"

    # Create a mock connection that already has matching host/port
    mock_conn = MagicMock(spec=Connection)
    mock_conn.host = "example.com"
    mock_conn.port = 80
    mock_sock = MagicMock()
    mock_conn.sock = mock_sock
    mock_sock.recv.side_effect = [mock_response, b""]

    resp = Request.send("GET", "http://example.com/", connection=mock_conn)

    assert resp.status_code == 200
    # Verify connection was reused, not created new
    mock_conn.open.assert_not_called()


def test_send_with_session_cookie_update():
    """Test that session cookies are updated from response."""
    from reqivo.client.session import Session

    mock_response = b"HTTP/1.1 200 OK\r\nSet-Cookie: session=abc123\r\n\r\n"

    with patch("reqivo.client.request.Connection") as mock_conn_cls:
        mock_conn = mock_conn_cls.return_value
        mock_sock = MagicMock()
        mock_conn.sock = None

        def open_side_effect():
            mock_conn.sock = mock_sock

        mock_conn.open.side_effect = open_side_effect
        mock_sock.recv.side_effect = [mock_response, b""]

        # Create a mock session
        mock_session = MagicMock(spec=Session)
        Request.set_session_instance(mock_session)

        try:
            resp = Request.send("GET", "http://example.com/")

            # Verify session's cookie update method was called
            mock_session._update_cookies_from_response.assert_called_once()
        finally:
            Request.set_session_instance(None)


# ============================================================================
# TEST CLASS: AsyncRequest
# ============================================================================


class TestAsyncRequest:
    """Tests for AsyncRequest async methods."""

    @pytest.mark.asyncio
    @patch("reqivo.client.request.AsyncConnection")
    async def test_async_send_basic(self, mock_conn_cls):
        """Test async send with basic GET request."""
        mock_response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"

        # Mock async connection
        mock_conn = MagicMock(spec=AsyncConnection)
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer
        mock_conn_cls.return_value = mock_conn

        # Mock async methods
        mock_conn.open = MagicMock(return_value=None)
        mock_conn.open.__name__ = "open"  # For async mock

        async def async_open():
            mock_conn.reader = mock_reader
            mock_conn.writer = mock_writer

        mock_conn.open = async_open
        mock_conn.close = MagicMock(return_value=None)

        async def async_close():
            pass

        mock_conn.close = async_close

        # Mock writer.drain
        async def async_drain():
            pass

        mock_writer.drain = async_drain

        # Mock reader.read to return response then empty
        call_count = [0]

        async def async_read(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_response
            return b""

        mock_reader.read = async_read

        resp = await AsyncRequest.send("GET", "http://example.com/")

        assert resp.status_code == 200
        assert resp.body == b"OK"
        mock_writer.write.assert_called_once()

    @pytest.mark.asyncio
    @patch("reqivo.client.request.AsyncConnection")
    async def test_async_send_with_body(self, mock_conn_cls):
        """Test async send with POST request and body."""
        mock_response = b"HTTP/1.1 201 Created\r\nContent-Length: 7\r\n\r\nCreated"

        mock_conn = MagicMock(spec=AsyncConnection)
        mock_conn.host = "api.example.com"
        mock_conn.port = 443
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer
        mock_conn_cls.return_value = mock_conn

        async def async_open():
            mock_conn.reader = mock_reader
            mock_conn.writer = mock_writer

        mock_conn.open = async_open

        async def async_close():
            pass

        mock_conn.close = async_close

        async def async_drain():
            pass

        mock_writer.drain = async_drain

        call_count = [0]

        async def async_read(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_response
            return b""

        mock_reader.read = async_read

        resp = await AsyncRequest.send(
            "POST", "https://api.example.com/data", body="test_data"
        )

        assert resp.status_code == 201
        mock_writer.write.assert_called_once()
        # Verify body was included in request
        request_data = mock_writer.write.call_args[0][0]
        assert b"test_data" in request_data

    @pytest.mark.asyncio
    async def test_async_send_invalid_url(self):
        """Test async send with invalid URL."""
        with pytest.raises(RequestError, match="Invalid URL"):
            await AsyncRequest.send("GET", "not-a-valid-url")

    @pytest.mark.asyncio
    @patch("reqivo.client.request.AsyncConnection")
    async def test_async_send_server_closed_immediately(self, mock_conn_cls):
        """Test async send when server closes without response."""
        mock_conn = MagicMock(spec=AsyncConnection)
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer
        mock_conn_cls.return_value = mock_conn

        async def async_open():
            mock_conn.reader = mock_reader
            mock_conn.writer = mock_writer

        mock_conn.open = async_open

        async def async_close():
            pass

        mock_conn.close = async_close

        async def async_drain():
            pass

        mock_writer.drain = async_drain

        async def async_read(size):
            return b""  # Server closes immediately

        mock_reader.read = async_read

        with pytest.raises(NetworkError, match="Server closed connection"):
            await AsyncRequest.send("GET", "http://example.com/")

    @pytest.mark.asyncio
    @patch("reqivo.client.request.AsyncConnection")
    async def test_async_send_with_timeout_object(self, mock_conn_cls):
        """Test async send with Timeout object."""
        from reqivo.utils.timing import Timeout

        mock_response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"

        mock_conn = MagicMock(spec=AsyncConnection)
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer
        mock_conn_cls.return_value = mock_conn

        async def async_open():
            mock_conn.reader = mock_reader
            mock_conn.writer = mock_writer

        mock_conn.open = async_open

        async def async_close():
            pass

        mock_conn.close = async_close

        async def async_drain():
            pass

        mock_writer.drain = async_drain

        call_count = [0]

        async def async_read(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_response
            return b""

        mock_reader.read = async_read

        timeout_obj = Timeout(connect=5.0, read=10.0, total=30.0)
        resp = await AsyncRequest.send(
            "GET", "http://example.com/", timeout=timeout_obj
        )

        assert resp.status_code == 200
        # Verify timeout object was used
        mock_conn_cls.assert_called_once()
        call_kwargs = mock_conn_cls.call_args[1]
        assert call_kwargs["timeout"] == timeout_obj

    @pytest.mark.asyncio
    @patch("reqivo.client.request.AsyncConnection")
    async def test_async_send_with_existing_connection(self, mock_conn_cls):
        """Test async send with pre-existing connection reuse."""
        mock_response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"

        # Create existing connection
        mock_conn = MagicMock(spec=AsyncConnection)
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer

        async def async_close():
            pass

        mock_conn.close = async_close

        async def async_drain():
            pass

        mock_writer.drain = async_drain

        call_count = [0]

        async def async_read(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_response
            return b""

        mock_reader.read = async_read

        resp = await AsyncRequest.send(
            "GET", "http://example.com/", connection=mock_conn
        )

        assert resp.status_code == 200
        # Verify new connection was NOT created
        mock_conn_cls.assert_not_called()

    @pytest.mark.asyncio
    @patch("reqivo.client.request.AsyncConnection")
    async def test_async_send_with_query_string(self, mock_conn_cls):
        """Test async send with URL containing query parameters."""
        mock_response = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK"

        mock_conn = MagicMock(spec=AsyncConnection)
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer
        mock_conn_cls.return_value = mock_conn

        async def async_open():
            mock_conn.reader = mock_reader
            mock_conn.writer = mock_writer

        mock_conn.open = async_open

        async def async_close():
            pass

        mock_conn.close = async_close

        async def async_drain():
            pass

        mock_writer.drain = async_drain

        call_count = [0]

        async def async_read(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_response
            return b""

        mock_reader.read = async_read

        resp = await AsyncRequest.send("GET", "http://example.com/path?foo=bar&baz=qux")

        # Verify query string was included in request
        request_data = mock_writer.write.call_args[0][0]
        assert b"GET /path?foo=bar&baz=qux HTTP/1.1\r\n" in request_data

    @pytest.mark.asyncio
    @patch("reqivo.client.request.AsyncConnection")
    async def test_async_send_connection_fails_to_open(self, mock_conn_cls):
        """Test async send when connection fails to establish streams."""
        mock_conn = MagicMock(spec=AsyncConnection)
        mock_conn.reader = None
        mock_conn.writer = None
        mock_conn_cls.return_value = mock_conn

        async def async_open():
            # Simulate streams not being established
            pass

        mock_conn.open = async_open

        async def async_close():
            pass

        mock_conn.close = async_close

        with pytest.raises(NetworkError, match="Failed to establish stream connection"):
            await AsyncRequest.send("GET", "http://example.com/")

    @pytest.mark.asyncio
    @patch.object(AsyncRequest, "send")
    async def test_async_get_convenience_method(self, mock_send):
        """Test async get() convenience method."""
        mock_send.return_value = MagicMock(status_code=200)

        await AsyncRequest.get("http://example.com/get", headers={"X-Test": "1"})

        mock_send.assert_called_once_with(
            "GET",
            "http://example.com/get",
            headers={"X-Test": "1"},
            timeout=5,
            connection=None,
        )

    @pytest.mark.asyncio
    @patch.object(AsyncRequest, "send")
    async def test_async_post_convenience_method(self, mock_send):
        """Test async post() convenience method."""
        mock_send.return_value = MagicMock(status_code=201)

        await AsyncRequest.post("http://example.com/post", body="data", timeout=10)

        mock_send.assert_called_once_with(
            "POST",
            "http://example.com/post",
            headers=None,
            body="data",
            timeout=10,
            connection=None,
        )

    def test_async_set_session_instance(self):
        """Test AsyncRequest.set_session_instance() sets class variable."""
        from reqivo.client.session import AsyncSession

        mock_session = MagicMock(spec=AsyncSession)

        # Initially None
        assert AsyncRequest._session_instance is None

        # Set session instance (covers line 219)
        AsyncRequest.set_session_instance(mock_session)
        assert AsyncRequest._session_instance == mock_session

        # Clear it
        AsyncRequest.set_session_instance(None)
        assert AsyncRequest._session_instance is None

    @pytest.mark.asyncio
    @patch("reqivo.client.request.AsyncConnection")
    async def test_async_send_updates_session_cookies(self, mock_conn_cls):
        """Test that AsyncRequest.send() updates session cookies when session is set."""
        from reqivo.client.session import AsyncSession

        mock_response = b"HTTP/1.1 200 OK\r\nSet-Cookie: session=abc123\r\n\r\nOK"

        # Create real session instance
        mock_session = MagicMock(spec=AsyncSession)
        mock_session._update_cookies_from_response = MagicMock()

        # Mock connection
        mock_conn = MagicMock(spec=AsyncConnection)
        mock_reader = MagicMock()
        mock_writer = MagicMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer
        mock_conn_cls.return_value = mock_conn

        async def async_drain():
            pass

        mock_writer.drain = async_drain

        call_count = [0]

        async def async_read(size):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_response
            return b""

        mock_reader.read = async_read

        async def async_close():
            pass

        mock_conn.close = async_close

        # Set session instance
        AsyncRequest.set_session_instance(mock_session)

        try:
            # Send request
            resp = await AsyncRequest.send("GET", "http://example.com/")

            # Verify session cookies were updated (covers line 290)
            mock_session._update_cookies_from_response.assert_called_once()
            assert resp.status_code == 200

        finally:
            # Clean up
            AsyncRequest.set_session_instance(None)
