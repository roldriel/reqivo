"""tests/unit/test_websocket.py

Unit tests for reqivo.client.websocket module.

Test Coverage:
    - WebSocket handshake (RFC 6455 compliance)
    - Frame sending (TEXT, BINARY, control frames)
    - Frame receiving with fragmentation
    - Control frame handling (PING, PONG, CLOSE)
    - Error conditions and edge cases
    - AsyncWebSocket async implementation
"""

import asyncio
import base64
import hashlib
from unittest import mock

import pytest

from reqivo.client.request import Request
from reqivo.client.response import Response
from reqivo.client.websocket import AsyncWebSocket, WebSocket, _compute_accept_key
from reqivo.transport.connection import AsyncConnection, Connection
from reqivo.utils.websocket_utils import (
    OPCODE_BINARY,
    OPCODE_CLOSE,
    OPCODE_CONTINUATION,
    OPCODE_PING,
    OPCODE_PONG,
    OPCODE_TEXT,
    WebSocketError,
    apply_mask,
    create_frame,
)

# ============================================================================
# TEST HELPER FUNCTIONS
# ============================================================================


def test_compute_accept_key_rfc6455_example():
    """Test _compute_accept_key with RFC 6455 example."""
    # RFC 6455 Section 1.3 example
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    expected = "s3pPLMBiTxaQ9kYGzzhZRbK+xOo="
    assert _compute_accept_key(key) == expected


def test_compute_accept_key_different_input():
    """Test _compute_accept_key with different input."""
    key = "x3JJHMbDL1EzLkh9GBhXDw=="
    # Manually compute expected value
    magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    sha1 = hashlib.sha1((key + magic).encode("utf-8"), usedforsecurity=False).digest()
    expected = base64.b64encode(sha1).decode("ascii")
    assert _compute_accept_key(key) == expected


# ============================================================================
# TEST CLASS: WebSocket Initialization
# ============================================================================


class TestWebSocketInit:
    """Tests for WebSocket initialization."""

    def test_init_minimal_params(self):
        """Test WebSocket initialization with minimal parameters."""
        ws = WebSocket("ws://example.com/")
        assert ws.url == "ws://example.com/"
        assert ws.timeout is None
        assert ws.headers == {}
        assert ws.subprotocols == []
        assert ws.sock is None
        assert ws.connected is False

    def test_init_all_params(self):
        """Test WebSocket initialization with all parameters."""
        headers = {"X-Custom": "value"}
        subprotocols = ["chat", "superchat"]
        ws = WebSocket(
            "ws://example.com/socket",
            timeout=10.0,
            headers=headers,
            subprotocols=subprotocols,
        )
        assert ws.url == "ws://example.com/socket"
        assert ws.timeout == 10.0
        assert ws.headers == {"X-Custom": "value"}
        assert ws.subprotocols == ["chat", "superchat"]


# ============================================================================
# TEST CLASS: WebSocket Connect (Handshake)
# ============================================================================


class TestWebSocketConnect:
    """Tests for WebSocket handshake."""

    @mock.patch("reqivo.client.websocket.Connection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    def test_connect_success_ws_scheme(self, mock_build, mock_conn_cls):
        """Test successful WebSocket handshake with ws:// scheme."""
        ws = WebSocket("ws://example.com/socket")

        # Mock connection
        mock_conn = mock.Mock(spec=Connection)
        mock_sock = mock.Mock()
        mock_conn_cls.return_value = mock_conn
        mock_conn.open.return_value = mock_sock  # open() returns socket

        # Mock handshake response
        handshake_response = (
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n"
            b"\r\n"
        )
        mock_sock.recv.side_effect = [handshake_response, b""]

        # Mock build_request to return a valid request
        mock_build.return_value = b"GET /socket HTTP/1.1\r\n\r\n"

        # Patch os.urandom to return predictable key
        with mock.patch("os.urandom", return_value=b"the sample nonce"):
            ws.connect()

        # Verify connection was established
        mock_conn_cls.assert_called_once_with(
            "example.com", 80, use_ssl=False, timeout=None
        )
        mock_conn.open.assert_called_once()
        assert ws.connected is True
        assert ws.sock == mock_sock

    @mock.patch("reqivo.client.websocket.Connection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    def test_connect_success_wss_scheme(self, mock_build, mock_conn_cls):
        """Test successful WebSocket handshake with wss:// scheme (SSL)."""
        ws = WebSocket("wss://secure.example.com/socket")

        mock_conn = mock.Mock(spec=Connection)
        mock_sock = mock.Mock()
        mock_conn_cls.return_value = mock_conn
        mock_conn.open.return_value = mock_sock  # open() returns socket

        handshake_response = (
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n"
            b"\r\n"
        )
        mock_sock.recv.side_effect = [handshake_response, b""]
        mock_build.return_value = b"GET /socket HTTP/1.1\r\n\r\n"

        with mock.patch("os.urandom", return_value=b"the sample nonce"):
            ws.connect()

        # Verify SSL was enabled (use_ssl=True for wss, port 443)
        mock_conn_cls.assert_called_once_with(
            "secure.example.com", 443, use_ssl=True, timeout=None
        )
        assert ws.connected is True

    def test_connect_invalid_scheme(self):
        """Test connect with invalid URL scheme."""
        ws = WebSocket("http://example.com/")
        with pytest.raises(ValueError, match="URL must use ws:// or wss:// scheme"):
            ws.connect()

    def test_connect_missing_hostname(self):
        """Test connect with URL missing hostname."""
        ws = WebSocket("ws:///path")
        with pytest.raises(ValueError, match="Invalid URL: Hostname missing"):
            ws.connect()

    @mock.patch("reqivo.client.websocket.Connection")
    def test_connect_connection_failure(self, mock_conn_cls):
        """Test connect when connection fails to open."""
        ws = WebSocket("ws://example.com/")

        mock_conn = mock.Mock(spec=Connection)
        mock_conn_cls.return_value = mock_conn
        mock_conn.open.side_effect = ConnectionError("Connection refused")

        # Sync version doesn't wrap exception, async version does
        with pytest.raises(ConnectionError, match="Connection refused"):
            ws.connect()

    @mock.patch("reqivo.client.websocket.Connection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    def test_connect_non_101_status(self, mock_build, mock_conn_cls):
        """Test connect with non-101 HTTP status."""
        ws = WebSocket("ws://example.com/")

        mock_conn = mock.Mock(spec=Connection)
        mock_sock = mock.Mock()
        mock_conn_cls.return_value = mock_conn
        mock_conn.open.return_value = mock_sock  # open() returns socket

        # Server responds with 404 instead of 101
        handshake_response = b"HTTP/1.1 404 Not Found\r\n\r\n"
        mock_sock.recv.side_effect = [handshake_response, b""]
        mock_build.return_value = b"GET / HTTP/1.1\r\n\r\n"

        with mock.patch("os.urandom", return_value=b"test_key_1234567"):
            with pytest.raises(
                WebSocketError, match="WebSocket handshake failed with status 404"
            ):
                ws.connect()

    @mock.patch("reqivo.client.websocket.Connection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    def test_connect_invalid_accept_key(self, mock_build, mock_conn_cls):
        """Test connect with invalid Sec-WebSocket-Accept header."""
        ws = WebSocket("ws://example.com/")

        mock_conn = mock.Mock(spec=Connection)
        mock_sock = mock.Mock()
        mock_conn_cls.return_value = mock_conn
        mock_conn.open.return_value = mock_sock  # open() returns socket

        # Server responds with wrong accept key
        handshake_response = (
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: WRONG_KEY_HERE\r\n"
            b"\r\n"
        )
        mock_sock.recv.side_effect = [handshake_response, b""]
        mock_build.return_value = b"GET / HTTP/1.1\r\n\r\n"

        with mock.patch("os.urandom", return_value=b"the sample nonce"):
            with pytest.raises(WebSocketError, match="Invalid Sec-WebSocket-Accept"):
                ws.connect()

    @mock.patch("reqivo.client.websocket.Connection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    def test_connect_with_custom_headers_and_subprotocols(
        self, mock_build, mock_conn_cls
    ):
        """Test connect with custom headers and subprotocols."""
        headers = {"Authorization": "Bearer token123"}
        subprotocols = ["chat", "superchat"]
        ws = WebSocket("ws://example.com/", headers=headers, subprotocols=subprotocols)

        mock_conn = mock.Mock(spec=Connection)
        mock_sock = mock.Mock()
        mock_conn_cls.return_value = mock_conn
        mock_conn.open.return_value = mock_sock  # open() returns socket

        handshake_response = (
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n"
            b"\r\n"
        )
        mock_sock.recv.side_effect = [handshake_response, b""]
        mock_build.return_value = b"GET / HTTP/1.1\r\n\r\n"

        with mock.patch("os.urandom", return_value=b"the sample nonce"):
            ws.connect()

        # Verify build_request was called with custom headers and subprotocols
        call_args = mock_build.call_args[0]
        headers_arg = call_args[3]
        assert headers_arg["Authorization"] == "Bearer token123"
        assert headers_arg["Sec-WebSocket-Protocol"] == "chat, superchat"

    @mock.patch("reqivo.client.websocket.Connection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    def test_connect_with_query_string(self, mock_build, mock_conn_cls):
        """Test connect with URL containing query string."""
        ws = WebSocket("ws://example.com/socket?token=abc123")

        mock_conn = mock.Mock(spec=Connection)
        mock_sock = mock.Mock()
        mock_conn_cls.return_value = mock_conn
        mock_conn.open.return_value = mock_sock  # open() returns socket

        handshake_response = (
            b"HTTP/1.1 101 Switching Protocols\r\n"
            b"Upgrade: websocket\r\n"
            b"Connection: Upgrade\r\n"
            b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n"
            b"\r\n"
        )
        mock_sock.recv.side_effect = [handshake_response, b""]
        mock_build.return_value = b"GET /socket?token=abc123 HTTP/1.1\r\n\r\n"

        with mock.patch("os.urandom", return_value=b"the sample nonce"):
            ws.connect()

        # Verify path with query string was used
        call_args = mock_build.call_args[0]
        path = call_args[1]
        assert path == "/socket?token=abc123"


# ============================================================================
# TEST CLASS: WebSocket Send
# ============================================================================


class TestWebSocketSend:
    """Tests for WebSocket send method."""

    def test_send_text_data(self):
        """Test sending text data."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        ws.send("Hello, WebSocket!")

        # Verify sendall was called
        mock_sock.sendall.assert_called_once()
        # Verify it's a TEXT frame (opcode 0x1)
        frame_data = mock_sock.sendall.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_TEXT

    def test_send_binary_data(self):
        """Test sending binary data."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        ws.send(b"\x00\x01\x02\x03")

        mock_sock.sendall.assert_called_once()
        # Verify it's a BINARY frame (opcode 0x2)
        frame_data = mock_sock.sendall.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_BINARY

    def test_send_not_connected(self):
        """Test send when not connected."""
        ws = WebSocket("ws://example.com/")
        ws.connected = False

        with pytest.raises(ConnectionError, match="WebSocket is not connected"):
            ws.send("data")

    def test_send_no_socket(self):
        """Test send when socket is None."""
        ws = WebSocket("ws://example.com/")
        ws.connected = True
        ws.sock = None

        with pytest.raises(ConnectionError, match="WebSocket is not connected"):
            ws.send("data")


# ============================================================================
# TEST CLASS: WebSocket Recv
# ============================================================================


class TestWebSocketRecv:
    """Tests for WebSocket recv method."""

    def test_recv_text_frame(self):
        """Test receiving a complete TEXT frame."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # Create a TEXT frame with "Hello" (unmasked, as server sends)
        payload = b"Hello"
        frame = create_frame(payload, opcode=OPCODE_TEXT, mask=False)
        mock_sock.recv.side_effect = [frame, b""]

        result = ws.recv()

        assert result == "Hello"

    def test_recv_binary_frame(self):
        """Test receiving a BINARY frame with non-UTF8 data."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # Use non-UTF8 bytes to force binary return
        payload = b"\xff\xfe\x00\x01\x02\x03"
        frame = create_frame(payload, opcode=OPCODE_BINARY, mask=False)
        mock_sock.recv.side_effect = [frame, b""]

        result = ws.recv()

        assert result == b"\xff\xfe\x00\x01\x02\x03"

    def test_recv_fragmented_message(self):
        """Test receiving a fragmented message with CONTINUATION frames."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # First frame: TEXT, FIN=0
        frame1_data = b"\x01\x05Hello"  # opcode=1, fin=0, len=5, payload="Hello"
        # Second frame: CONTINUATION, FIN=1
        frame2_data = b"\x80\x06 World"  # opcode=0, fin=1, len=6, payload=" World"

        mock_sock.recv.side_effect = [frame1_data, frame2_data, b""]

        result = ws.recv()

        assert result == "Hello World"

    def test_recv_ping_auto_pong(self):
        """Test receiving PING frame auto-responds with PONG."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # PING frame followed by TEXT frame
        ping_frame = create_frame(b"ping_payload", opcode=OPCODE_PING, mask=False)
        text_frame = create_frame(b"message", opcode=OPCODE_TEXT, mask=False)
        mock_sock.recv.side_effect = [ping_frame, text_frame, b""]

        result = ws.recv()

        # Verify PONG was sent
        assert mock_sock.sendall.call_count == 1
        pong_data = mock_sock.sendall.call_args[0][0]
        opcode = pong_data[0] & 0x0F
        assert opcode == OPCODE_PONG

        # Verify TEXT message was received
        assert result == "message"

    def test_recv_pong_ignored(self):
        """Test receiving PONG frame is silently ignored."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # PONG frame followed by TEXT frame
        pong_frame = create_frame(b"pong_payload", opcode=OPCODE_PONG, mask=False)
        text_frame = create_frame(b"message", opcode=OPCODE_TEXT, mask=False)
        mock_sock.recv.side_effect = [pong_frame, text_frame, b""]

        result = ws.recv()

        # PONG should be silently ignored, return next message
        assert result == "message"

    def test_recv_close_frame(self):
        """Test receiving CLOSE frame raises ConnectionError."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        close_frame = create_frame(b"", opcode=OPCODE_CLOSE, mask=False)
        mock_sock.recv.side_effect = [close_frame, b""]

        with pytest.raises(ConnectionError, match="WebSocket closed by server"):
            ws.recv()

        # Verify connection was closed
        assert ws.connected is False

    def test_recv_not_connected(self):
        """Test recv when not connected."""
        ws = WebSocket("ws://example.com/")
        ws.connected = False

        # Sync recv raises ConnectionError, not WebSocketError
        with pytest.raises(ConnectionError, match="WebSocket is not connected"):
            ws.recv()

    def test_recv_connection_closed_during_recv(self):
        """Test recv when connection closes during receive."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # Simulate connection closed (empty recv)
        mock_sock.recv.return_value = b""

        with pytest.raises(ConnectionError, match="Connection closed"):
            ws.recv()

    def test_recv_unknown_opcode(self):
        """Test recv with unknown opcode raises WebSocketError."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # Frame with invalid opcode (e.g., 0x0F)
        invalid_frame = b"\x8f\x05Hello"  # opcode=15, fin=1, len=5
        mock_sock.recv.side_effect = [invalid_frame, b""]

        with pytest.raises(WebSocketError, match="Unknown opcode"):
            ws.recv()

    def test_recv_masked_frame_from_server(self):
        """Test receiving masked frame from server."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # Create a masked frame (server shouldn't send masked, but let's test)
        payload = b"secret"
        frame = create_frame(payload, opcode=OPCODE_TEXT, mask=True)
        mock_sock.recv.side_effect = [frame, b""]

        # Should still be able to unmask and receive
        result = ws.recv()
        assert result == "secret"

    def test_recv_extended_payload_length_126(self):
        """Test receiving frame with extended payload length (126 bytes)."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # Payload of exactly 126 bytes triggers 16-bit length encoding
        payload = b"A" * 126
        frame = create_frame(payload, opcode=OPCODE_TEXT, mask=False)
        mock_sock.recv.side_effect = [frame, b""]

        result = ws.recv()

        assert result == "A" * 126

    def test_recv_extended_payload_length_65536(self):
        """Test receiving frame with 64-bit extended length."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # Payload larger than 65535 triggers 64-bit length encoding
        # Use TEXT opcode with ASCII data (which is valid UTF-8)
        payload = b"B" * 70000
        frame = create_frame(payload, opcode=OPCODE_TEXT, mask=False)
        mock_sock.recv.side_effect = [frame, b""]

        result = ws.recv()

        # TEXT frames with valid UTF-8 return strings
        assert result == "B" * 70000

    def test_recv_frame_exceeds_max_size(self):
        """Test receiving frame exceeding MAX_FRAME_SIZE raises error."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        # Manually craft a frame header claiming huge payload
        # FIN=1, opcode=TEXT, payload_len=127 (64-bit extended)
        # Payload size = 11MB (exceeds MAX_FRAME_SIZE of 10MB)
        huge_size = 11 * 1024 * 1024
        frame_header = b"\x81\x7f" + huge_size.to_bytes(8, "big")
        mock_sock.recv.side_effect = [frame_header, b""]

        with pytest.raises(WebSocketError, match="Frame payload too large"):
            ws.recv()


# ============================================================================
# TEST CLASS: WebSocket Control Frames
# ============================================================================


class TestWebSocketControlFrames:
    """Tests for WebSocket control frame methods."""

    def test_ping(self):
        """Test sending PING frame."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        ws.ping(b"ping_data")

        mock_sock.sendall.assert_called_once()
        frame_data = mock_sock.sendall.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_PING

    def test_ping_no_socket(self):
        """Test ping when socket is None."""
        ws = WebSocket("ws://example.com/")
        ws.sock = None

        with pytest.raises(ConnectionError, match="WebSocket is not connected"):
            ws.ping()

    def test_pong(self):
        """Test sending PONG frame."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        ws.pong(b"pong_data")

        mock_sock.sendall.assert_called_once()
        frame_data = mock_sock.sendall.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_PONG

    def test_pong_no_socket(self):
        """Test pong when socket is None."""
        ws = WebSocket("ws://example.com/")
        ws.sock = None

        with pytest.raises(ConnectionError, match="WebSocket is not connected"):
            ws.pong()


# ============================================================================
# TEST CLASS: WebSocket Close
# ============================================================================


class TestWebSocketClose:
    """Tests for WebSocket close method."""

    def test_close_sends_close_frame(self):
        """Test close sends CLOSE frame and closes socket."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True

        ws.close()

        # Verify CLOSE frame was sent
        mock_sock.sendall.assert_called_once()
        frame_data = mock_sock.sendall.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_CLOSE

        # Verify socket was closed
        mock_sock.close.assert_called_once()
        assert ws.connected is False

    def test_close_when_not_connected(self):
        """Test close when already disconnected."""
        ws = WebSocket("ws://example.com/")
        ws.connected = False
        mock_sock = mock.Mock()
        ws.sock = mock_sock

        ws.close()

        # Should not try to send CLOSE frame
        mock_sock.sendall.assert_not_called()
        mock_sock.close.assert_not_called()

    def test_close_handles_sendall_failure(self):
        """Test close gracefully handles sendall failure."""
        ws = WebSocket("ws://example.com/")
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws.connected = True
        mock_sock.sendall.side_effect = OSError("Connection reset")

        # Should not raise, suppresses exception
        ws.close()

        # Verify socket was still closed
        mock_sock.close.assert_called_once()
        assert ws.connected is False

    def test_close_with_none_socket(self):
        """Test close when socket is None."""
        ws = WebSocket("ws://example.com/")
        ws.sock = None
        ws.connected = True

        # Should handle gracefully
        ws.close()
        assert ws.connected is False


# ============================================================================
# TEST CLASS: AsyncWebSocket
# ============================================================================


class TestAsyncWebSocketInit:
    """Tests for AsyncWebSocket initialization."""

    def test_async_init(self):
        """Test AsyncWebSocket initialization."""
        ws = AsyncWebSocket("ws://example.com/")
        assert ws.url == "ws://example.com/"
        assert ws.timeout is None
        assert ws.headers == {}
        assert ws.subprotocols == []
        assert ws.connection is None
        assert ws.connected is False
        assert ws.reader is None
        assert ws.writer is None


class TestAsyncWebSocketConnect:
    """Tests for AsyncWebSocket connect method."""

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    async def test_async_connect_success(self, mock_build, mock_conn_cls):
        """Test successful async WebSocket handshake."""
        ws = AsyncWebSocket("ws://example.com/socket")

        # Mock async connection
        mock_conn = mock.Mock(spec=AsyncConnection)
        mock_conn.open = mock.AsyncMock()
        mock_reader = mock.AsyncMock()
        mock_writer = mock.AsyncMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer
        mock_conn_cls.return_value = mock_conn

        # Mock handshake response
        handshake_lines = [
            b"HTTP/1.1 101 Switching Protocols\r\n",
            b"Upgrade: websocket\r\n",
            b"Connection: Upgrade\r\n",
            b"Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=\r\n",
            b"\r\n",
        ]
        mock_reader.readuntil.side_effect = handshake_lines
        mock_build.return_value = b"GET /socket HTTP/1.1\r\n\r\n"

        with mock.patch("os.urandom", return_value=b"the sample nonce"):
            await ws.connect()

        mock_conn.open.assert_awaited_once()
        mock_writer.write.assert_called()
        mock_writer.drain.assert_awaited()
        assert ws.connected is True

    @pytest.mark.asyncio
    async def test_async_connect_invalid_scheme(self):
        """Test async connect with invalid scheme."""
        ws = AsyncWebSocket("http://example.com/")
        with pytest.raises(ValueError, match="URL must use ws:// or wss:// scheme"):
            await ws.connect()

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    async def test_async_connect_connection_failure(self, mock_conn_cls):
        """Test async connect when connection fails."""
        ws = AsyncWebSocket("ws://example.com/")

        mock_conn = mock.Mock(spec=AsyncConnection)
        mock_conn.open = mock.AsyncMock(side_effect=OSError("Connection refused"))
        mock_conn_cls.return_value = mock_conn

        with pytest.raises(WebSocketError, match="Connection failed"):
            await ws.connect()

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    async def test_async_connect_timeout(self, mock_build, mock_conn_cls):
        """Test async connect with timeout."""
        ws = AsyncWebSocket("ws://example.com/", timeout=1.0)

        mock_conn = mock.Mock(spec=AsyncConnection)
        mock_conn.open = mock.AsyncMock()
        mock_reader = mock.AsyncMock()
        mock_writer = mock.AsyncMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer
        mock_conn_cls.return_value = mock_conn

        # Simulate timeout during handshake
        mock_reader.readuntil.side_effect = asyncio.TimeoutError()
        mock_build.return_value = b"GET / HTTP/1.1\r\n\r\n"

        with mock.patch("os.urandom", return_value=b"test_key"):
            with pytest.raises(WebSocketError, match="Connection timeout"):
                await ws.connect()

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    async def test_async_connect_incomplete_read(self, mock_build, mock_conn_cls):
        """Test async connect with incomplete read during handshake."""
        ws = AsyncWebSocket("ws://example.com/")

        mock_conn = mock.Mock(spec=AsyncConnection)
        mock_conn.open = mock.AsyncMock()
        mock_reader = mock.AsyncMock()
        mock_writer = mock.AsyncMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer
        mock_conn_cls.return_value = mock_conn

        mock_reader.readuntil.side_effect = asyncio.IncompleteReadError(b"", 100)
        mock_build.return_value = b"GET / HTTP/1.1\r\n\r\n"

        with mock.patch("os.urandom", return_value=b"test_key"):
            with pytest.raises(
                WebSocketError, match="Connection closed during handshake"
            ):
                await ws.connect()

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    async def test_async_connect_no_streams(self, mock_build, mock_conn_cls):
        """Test async connect when streams are not established."""
        ws = AsyncWebSocket("ws://example.com/")

        mock_conn = mock.Mock(spec=AsyncConnection)
        mock_conn.open = mock.AsyncMock()
        mock_conn.reader = None
        mock_conn.writer = None
        mock_conn_cls.return_value = mock_conn

        with pytest.raises(
            WebSocketError, match="Failed to establish stream connection"
        ):
            await ws.connect()


class TestAsyncWebSocketSend:
    """Tests for AsyncWebSocket send method."""

    @pytest.mark.asyncio
    async def test_async_send_text(self):
        """Test async send with text data."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_writer = mock.AsyncMock()
        ws.writer = mock_writer
        ws.connected = True

        await ws.send("Hello async")

        mock_writer.write.assert_called_once()
        mock_writer.drain.assert_awaited_once()
        frame_data = mock_writer.write.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_TEXT

    @pytest.mark.asyncio
    async def test_async_send_binary(self):
        """Test async send with binary data."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_writer = mock.AsyncMock()
        ws.writer = mock_writer
        ws.connected = True

        await ws.send(b"\x00\x01\x02")

        frame_data = mock_writer.write.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_BINARY

    @pytest.mark.asyncio
    async def test_async_send_not_connected(self):
        """Test async send when not connected."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.connected = False

        with pytest.raises(ConnectionError, match="WebSocket is not connected"):
            await ws.send("data")


class TestAsyncWebSocketRecv:
    """Tests for AsyncWebSocket recv method."""

    @pytest.mark.asyncio
    async def test_async_recv_text_frame(self):
        """Test async recv text frame."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        # TEXT frame: FIN=1, opcode=1, unmasked, len=5, payload="Hello"
        mock_reader.readexactly.side_effect = [
            b"\x81\x05",  # Header
            b"Hello",  # Payload
        ]

        result = await ws.recv()

        assert result == "Hello"

    @pytest.mark.asyncio
    async def test_async_recv_binary_frame(self):
        """Test async recv binary frame with non-UTF8 data."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        # Use non-UTF8 bytes to force binary return
        payload = b"\xff\xfe\x00\x01\x02"
        mock_reader.readexactly.side_effect = [
            b"\x82\x05",  # BINARY, len=5
            payload,
        ]

        result = await ws.recv()

        assert result == b"\xff\xfe\x00\x01\x02"

    @pytest.mark.asyncio
    async def test_async_recv_fragmented_message(self):
        """Test async recv fragmented message."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        # First frame: TEXT, FIN=0
        # Second frame: CONTINUATION, FIN=1
        mock_reader.readexactly.side_effect = [
            b"\x01\x05",  # TEXT, FIN=0, len=5
            b"Hello",
            b"\x80\x06",  # CONTINUATION, FIN=1, len=6
            b" World",
        ]

        result = await ws.recv()

        assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_async_recv_ping_auto_pong(self):
        """Test async recv PING auto-responds with PONG."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        mock_writer = mock.AsyncMock()
        ws.reader = mock_reader
        ws.writer = mock_writer
        ws.connected = True

        # PING frame followed by TEXT frame
        mock_reader.readexactly.side_effect = [
            b"\x89\x04",  # PING, len=4
            b"ping",
            b"\x81\x02",  # TEXT, len=2
            b"hi",
        ]

        result = await ws.recv()

        # Verify PONG was sent
        assert mock_writer.write.call_count >= 1
        # Verify message was received
        assert result == "hi"

    @pytest.mark.asyncio
    async def test_async_recv_close_frame(self):
        """Test async recv CLOSE frame."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        mock_writer = mock.Mock()  # Regular mock, not AsyncMock for write
        mock_writer.write = mock.Mock()  # write is sync
        mock_writer.drain = mock.AsyncMock()  # drain is async
        ws.reader = mock_reader
        ws.writer = mock_writer
        ws.connected = True

        # Mock connection.close
        ws.connection = mock.Mock(spec=AsyncConnection)
        ws.connection.close = mock.AsyncMock()

        mock_reader.readexactly.side_effect = [
            b"\x88\x00",  # CLOSE header: opcode=8, len=0
            b"",  # Empty payload (0 bytes)
        ]

        with pytest.raises(WebSocketError, match="WebSocket closed by server"):
            await ws.recv()

        # Verify close was called
        ws.connection.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_async_recv_not_connected(self):
        """Test async recv when not connected."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.connected = False

        with pytest.raises(WebSocketError, match="WebSocket is not connected"):
            await ws.recv()

    @pytest.mark.asyncio
    async def test_async_recv_incomplete_read_header(self):
        """Test async recv with incomplete read during header."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        mock_reader.readexactly.side_effect = asyncio.IncompleteReadError(b"", 2)

        with pytest.raises(
            WebSocketError, match="Connection closed while reading frame header"
        ):
            await ws.recv()

    @pytest.mark.asyncio
    async def test_async_recv_incomplete_read_payload(self):
        """Test async recv with incomplete read during payload."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        mock_reader.readexactly.side_effect = [
            b"\x81\x05",  # Valid header
            asyncio.IncompleteReadError(b"", 5),  # Incomplete payload
        ]

        with pytest.raises(
            WebSocketError, match="Connection closed while reading frame payload"
        ):
            await ws.recv()

    @pytest.mark.asyncio
    async def test_async_recv_extended_length_126(self):
        """Test async recv with extended payload length (16-bit)."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        payload_len = 200
        mock_reader.readexactly.side_effect = [
            b"\x81\x7e",  # TEXT, extended len=126
            payload_len.to_bytes(2, "big"),  # 16-bit length
            b"A" * 200,
        ]

        result = await ws.recv()

        assert result == "A" * 200

    @pytest.mark.asyncio
    async def test_async_recv_extended_length_127(self):
        """Test async recv with extended payload length (64-bit)."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        payload_len = 70000
        mock_reader.readexactly.side_effect = [
            b"\x81\x7f",  # TEXT, extended len=127
            payload_len.to_bytes(8, "big"),  # 64-bit length
            b"B" * 70000,
        ]

        result = await ws.recv()

        # TEXT frames with valid UTF-8 return strings
        assert result == "B" * 70000

    @pytest.mark.asyncio
    async def test_async_recv_frame_exceeds_max_size(self):
        """Test async recv frame exceeding MAX_FRAME_SIZE."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        huge_size = 11 * 1024 * 1024  # 11MB
        mock_reader.readexactly.side_effect = [
            b"\x81\x7f",
            huge_size.to_bytes(8, "big"),
        ]

        with pytest.raises(WebSocketError, match="Frame payload too large"):
            await ws.recv()

    @pytest.mark.asyncio
    async def test_async_recv_masked_frame(self):
        """Test async recv masked frame from server."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        # Masked TEXT frame
        mask_key = b"\x12\x34\x56\x78"
        payload = b"test"
        masked_payload = apply_mask(payload, mask_key)

        mock_reader.readexactly.side_effect = [
            b"\x81\x84",  # TEXT, masked, len=4
            mask_key,
            masked_payload,
        ]

        result = await ws.recv()

        assert result == "test"


class TestAsyncWebSocketControlFrames:
    """Tests for AsyncWebSocket control frame methods."""

    @pytest.mark.asyncio
    async def test_async_ping(self):
        """Test async ping."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_writer = mock.AsyncMock()
        ws.writer = mock_writer

        await ws.ping(b"ping_data")

        mock_writer.write.assert_called_once()
        frame_data = mock_writer.write.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_PING

    @pytest.mark.asyncio
    async def test_async_pong(self):
        """Test async pong."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_writer = mock.AsyncMock()
        ws.writer = mock_writer

        await ws.pong(b"pong_data")

        mock_writer.write.assert_called_once()
        frame_data = mock_writer.write.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_PONG


class TestAsyncWebSocketClose:
    """Tests for AsyncWebSocket close method."""

    @pytest.mark.asyncio
    async def test_async_close(self):
        """Test async close."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_writer = mock.AsyncMock()
        ws.writer = mock_writer
        ws.connected = True
        ws.connection = mock.Mock(spec=AsyncConnection)
        ws.connection.close = mock.AsyncMock()

        await ws.close()

        # Verify CLOSE frame was sent
        mock_writer.write.assert_called()
        frame_data = mock_writer.write.call_args[0][0]
        opcode = frame_data[0] & 0x0F
        assert opcode == OPCODE_CLOSE

        # Verify connection was closed
        ws.connection.close.assert_awaited_once()
        assert ws.connected is False

    @pytest.mark.asyncio
    async def test_async_close_not_connected(self):
        """Test async close when not connected."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.connected = False
        mock_writer = mock.AsyncMock()
        ws.writer = mock_writer

        await ws.close()

        # Should not try to send CLOSE frame
        mock_writer.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_close_handles_exception(self):
        """Test async close gracefully handles exceptions."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_writer = mock.AsyncMock()
        ws.writer = mock_writer
        ws.connected = True
        ws.connection = mock.Mock(spec=AsyncConnection)
        ws.connection.close = mock.AsyncMock()
        mock_writer.write.side_effect = OSError("Connection reset")

        # Should not raise, suppresses exception
        await ws.close()

        # Verify connection was still closed
        ws.connection.close.assert_awaited_once()
        assert ws.connected is False


# ============================================================================
# TEST CLASS: AsyncWebSocket Additional Edge Cases
# ============================================================================


class TestAsyncWebSocketEdgeCases:
    """Tests for AsyncWebSocket edge cases to improve coverage."""

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    async def test_async_connect_with_query_string(self, mock_conn_cls):
        """Test async connect with URL containing query string (line 323)."""
        ws = AsyncWebSocket("ws://example.com/path?key=value&foo=bar")

        mock_conn = mock_conn_cls.return_value
        mock_conn.open = mock.AsyncMock()
        mock_reader = mock.AsyncMock()
        mock_writer = mock.AsyncMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer

        key = base64.b64encode(b"test_key_16bytes").decode("ascii")
        accept_key = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("utf-8"),
                usedforsecurity=False,
            ).digest()
        ).decode("ascii")

        # Mock handshake response - readuntil returns lines WITH \r\n
        handshake_lines = [
            b"HTTP/1.1 101 Switching Protocols\r\n",
            b"Upgrade: websocket\r\n",
            b"Connection: Upgrade\r\n",
            f"Sec-WebSocket-Accept: {accept_key}\r\n".encode(),
            b"\r\n",
        ]
        mock_reader.readuntil.side_effect = handshake_lines

        with mock.patch(
            "reqivo.client.websocket.os.urandom", return_value=b"test_key_16bytes"
        ):
            await ws.connect()

        # Verify query string was included in request path
        request_sent = mock_writer.write.call_args[0][0].decode()
        assert "GET /path?key=value&foo=bar HTTP/1.1" in request_sent
        assert ws.connected is True

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    async def test_async_connect_with_custom_headers(self, mock_conn_cls):
        """Test async connect with custom headers (lines 334-335)."""
        custom_headers = {"X-Custom": "test", "Authorization": "Bearer token"}
        ws = AsyncWebSocket("ws://example.com/", headers=custom_headers)

        mock_conn = mock_conn_cls.return_value
        mock_conn.open = mock.AsyncMock()
        mock_reader = mock.AsyncMock()
        mock_writer = mock.AsyncMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer

        key = base64.b64encode(b"test_key_16bytes").decode("ascii")
        accept_key = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("utf-8"),
                usedforsecurity=False,
            ).digest()
        ).decode("ascii")

        handshake_lines = [
            b"HTTP/1.1 101 Switching Protocols\r\n",
            f"Sec-WebSocket-Accept: {accept_key}\r\n".encode(),
            b"\r\n",
        ]
        mock_reader.readuntil.side_effect = handshake_lines

        with mock.patch(
            "reqivo.client.websocket.os.urandom", return_value=b"test_key_16bytes"
        ):
            await ws.connect()

        # Verify custom headers were included
        request_sent = mock_writer.write.call_args[0][0].decode()
        assert "X-Custom: test" in request_sent
        assert "Authorization: Bearer token" in request_sent
        assert ws.connected is True

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    async def test_async_connect_with_subprotocols(self, mock_conn_cls):
        """Test async connect with subprotocols (line 338)."""
        ws = AsyncWebSocket("ws://example.com/", subprotocols=["chat", "superchat"])

        mock_conn = mock_conn_cls.return_value
        mock_conn.open = mock.AsyncMock()
        mock_reader = mock.AsyncMock()
        mock_writer = mock.AsyncMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer

        key = base64.b64encode(b"test_key_16bytes").decode("ascii")
        accept_key = base64.b64encode(
            hashlib.sha1(
                (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("utf-8"),
                usedforsecurity=False,
            ).digest()
        ).decode("ascii")

        handshake_lines = [
            b"HTTP/1.1 101 Switching Protocols\r\n",
            f"Sec-WebSocket-Accept: {accept_key}\r\n".encode(),
            b"\r\n",
        ]
        mock_reader.readuntil.side_effect = handshake_lines

        with mock.patch(
            "reqivo.client.websocket.os.urandom", return_value=b"test_key_16bytes"
        ):
            await ws.connect()

        # Verify Sec-WebSocket-Protocol header was included
        request_sent = mock_writer.write.call_args[0][0].decode()
        assert "Sec-WebSocket-Protocol: chat, superchat" in request_sent
        assert ws.connected is True

    @pytest.mark.asyncio
    async def test_async_connect_missing_hostname(self):
        """Test async connect with missing hostname (line 304)."""
        ws = AsyncWebSocket("ws:///path")  # No hostname

        with pytest.raises(ValueError, match="Invalid URL: Hostname missing"):
            await ws.connect()

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    async def test_async_connect_handshake_failed_status(self, mock_conn_cls):
        """Test async connect when handshake returns non-101 status (line 367)."""
        ws = AsyncWebSocket("ws://example.com/")

        mock_conn = mock_conn_cls.return_value
        mock_conn.open = mock.AsyncMock()
        mock_reader = mock.AsyncMock()
        mock_writer = mock.AsyncMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer

        # Return 400 Bad Request instead of 101
        handshake_lines = [
            b"HTTP/1.1 400 Bad Request\r\n",
            b"Content-Length: 0\r\n",
            b"\r\n",
        ]
        mock_reader.readuntil.side_effect = handshake_lines

        with pytest.raises(
            WebSocketError, match="WebSocket handshake failed with status 400"
        ):
            with mock.patch(
                "reqivo.client.websocket.os.urandom", return_value=b"test_key_16bytes"
            ):
                await ws.connect()

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.AsyncConnection")
    async def test_async_connect_invalid_accept_header(self, mock_conn_cls):
        """Test async connect with invalid Sec-WebSocket-Accept header (line 375)."""
        ws = AsyncWebSocket("ws://example.com/")

        mock_conn = mock_conn_cls.return_value
        mock_conn.open = mock.AsyncMock()
        mock_reader = mock.AsyncMock()
        mock_writer = mock.AsyncMock()
        mock_conn.reader = mock_reader
        mock_conn.writer = mock_writer

        # Return wrong accept key
        handshake_lines = [
            b"HTTP/1.1 101 Switching Protocols\r\n",
            b"Sec-WebSocket-Accept: invalid_key_here\r\n",
            b"\r\n",
        ]
        mock_reader.readuntil.side_effect = handshake_lines

        with pytest.raises(WebSocketError, match="Invalid Sec-WebSocket-Accept header"):
            with mock.patch(
                "reqivo.client.websocket.os.urandom", return_value=b"test_key_16bytes"
            ):
                await ws.connect()

    @pytest.mark.asyncio
    async def test_async_recv_pong_opcode(self):
        """Test async recv handling PONG opcode (line 471)."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        # Send PONG frame followed by TEXT frame
        mock_reader.readexactly.side_effect = [
            b"\x8a\x00",  # PONG header: FIN=1, opcode=10, len=0
            b"",  # PONG payload (empty, len=0)
            b"\x81\x04",  # TEXT header: FIN=1, opcode=1, len=4
            b"test",  # TEXT payload
        ]

        result = await ws.recv()

        # Should skip PONG and return TEXT message
        assert result == "test"

    @pytest.mark.asyncio
    async def test_async_recv_unknown_opcode(self):
        """Test async recv with unknown opcode raises error (line 484)."""
        ws = AsyncWebSocket("ws://example.com/")
        mock_reader = mock.AsyncMock()
        ws.reader = mock_reader
        ws.connected = True

        # Send frame with unknown opcode (e.g., 0x0F which is reserved)
        mock_reader.readexactly.side_effect = [
            b"\x8f\x00",  # Header: FIN=1, opcode=0x0F (unknown), len=0
            b"",  # Payload (empty, len=0)
        ]

        with pytest.raises(WebSocketError, match="Unknown opcode: 15"):
            await ws.recv()

    @pytest.mark.asyncio
    async def test_async_recv_reader_none_checks(self):
        """Test async recv reader=None checks (lines 405, 424, 431, 445, 450)."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.reader = None  # Simulate reader being None
        ws.connected = True

        # Should raise error when trying to read
        with pytest.raises(WebSocketError, match="WebSocket is not connected"):
            await ws.recv()

    @pytest.mark.asyncio
    async def test_async_send_writer_none(self):
        """Test async send when writer is None (branch 391->exit)."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.writer = None
        ws.connected = True

        # Should not raise, just exits early
        await ws.send("test")

    @pytest.mark.asyncio
    async def test_async_ping_writer_none(self):
        """Test async ping when writer is None (branch 495->exit)."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.writer = None

        # Should not raise, just exits early
        await ws.ping(b"test")

    @pytest.mark.asyncio
    async def test_async_pong_writer_none(self):
        """Test async pong when writer is None (branch 502->exit)."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.writer = None

        # Should not raise, just exits early
        await ws.pong(b"test")

    @pytest.mark.asyncio
    async def test_async_close_writer_none(self):
        """Test async close when writer is None (branch 513->517)."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.writer = None
        ws.connected = True
        ws.connection = mock.Mock(spec=AsyncConnection)
        ws.connection.close = mock.AsyncMock()

        await ws.close()

        # Should still close connection
        ws.connection.close.assert_awaited_once()
        assert ws.connected is False

    @pytest.mark.asyncio
    async def test_async_close_connection_none(self):
        """Test async close when connection is None (branch 517->520)."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.writer = mock.AsyncMock()
        ws.connected = True
        ws.connection = None  # No connection

        await ws.close()

        # Should not raise, just sets connected=False
        assert ws.connected is False


# ============================================================================
# TEST CLASS: Sync WebSocket Additional Edge Cases
# ============================================================================


class TestSyncWebSocketEdgeCases:
    """Tests for sync WebSocket edge cases to improve coverage."""

    @mock.patch("reqivo.client.websocket.Connection")
    def test_sync_connect_sock_none_after_open(self, mock_conn_cls):
        """Test sync connect when sock is None after open (line 109)."""
        ws = WebSocket("ws://example.com/")

        mock_conn = mock_conn_cls.return_value

        # Simulate connection open succeeding but sock remaining None
        def open_side_effect():
            pass  # sock stays None

        mock_conn.open = mock.Mock(side_effect=open_side_effect)
        mock_conn.sock = None  # Simulate failed connection

        with pytest.raises(WebSocketError, match="Failed to open connection"):
            ws.connect()

    @mock.patch("reqivo.client.websocket.Connection")
    @mock.patch("reqivo.client.websocket.Request.build_request")
    def test_sync_connect_connection_closed_during_handshake(
        self, mock_build, mock_conn_cls
    ):
        """Test sync connect when connection closes during handshake (line 116)."""
        ws = WebSocket("ws://example.com/")

        # Create mock socket that will be returned by conn.open()
        mock_sock = mock.Mock()
        mock_sock.sendall = mock.Mock()
        mock_sock.recv.return_value = b""  # Connection closed

        # Mock connection to return the socket
        mock_conn = mock_conn_cls.return_value
        mock_conn.open.return_value = mock_sock

        mock_build.return_value = b"GET / HTTP/1.1\r\n\r\n"

        with pytest.raises(WebSocketError, match="Connection closed during handshake"):
            with mock.patch(
                "reqivo.client.websocket.os.urandom", return_value=b"test_key_16bytes"
            ):
                ws.connect()

    def test_sync_recv_sock_none(self):
        """Test sync recv when sock is None (line 164)."""
        ws = WebSocket("ws://example.com/")
        ws.connected = True
        ws.sock = None
        ws._buffer = bytearray()

        with pytest.raises(ConnectionError, match="WebSocket is not connected"):
            ws.recv()

    @mock.patch("reqivo.client.websocket.parse_frame_header")
    def test_sync_recv_incomplete_frame_header(self, mock_parse):
        """Test sync recv when parse_frame_header returns None (lines 174-182)."""
        ws = WebSocket("ws://example.com/")
        ws.connected = True
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws._buffer = bytearray(b"\x81")  # Incomplete header (only 1 byte)

        # First call: parse returns None (incomplete)
        # Second call: parse returns valid header
        mock_parse.side_effect = [
            None,  # Incomplete - triggers lines 173-182
            (
                2,
                4,
                1,
                0,
                0,
                0,
                OPCODE_TEXT,
                False,
            ),  # Complete: header_len=2, payload_len=4
        ]

        # Mock socket to return complete frame data in one recv
        mock_sock.recv.return_value = b"\x04test"  # Length byte + payload

        result = ws.recv()

        # Should successfully read after getting more data
        assert result == "test"

    def test_sync_recv_buffer_needs_more_data(self):
        """Test sync recv when buffer needs more data for payload (lines 195-203)."""
        ws = WebSocket("ws://example.com/")
        ws.connected = True
        mock_sock = mock.Mock()
        ws.sock = mock_sock

        # Start with just the header
        ws._buffer = bytearray(b"\x81\x05")  # TEXT, len=5

        # Mock socket to return payload in chunks
        mock_sock.recv.side_effect = [
            b"he",  # First chunk
            b"llo",  # Second chunk
            b"",  # End
        ]

        result = ws.recv()

        assert result == "hello"

    def test_sync_recv_connection_closed_while_reading_payload(self):
        """Test sync recv when connection closes while reading payload (line 201)."""
        ws = WebSocket("ws://example.com/")
        ws.connected = True
        mock_sock = mock.Mock()
        ws.sock = mock_sock

        # Header indicates 10 bytes, but socket closes after partial data
        ws._buffer = bytearray(b"\x81\x0a")  # TEXT, len=10

        # Mock socket to return incomplete data then close
        mock_sock.recv.side_effect = [
            b"part",  # Only 4 bytes
            b"",  # Connection closed
        ]

        with pytest.raises(ConnectionError, match="Connection closed"):
            ws.recv()

    def test_sync_recv_sock_none_while_reading_payload(self):
        """Test sync recv when sock becomes None while reading payload (line 196)."""
        ws = WebSocket("ws://example.com/")
        ws.connected = True
        ws.sock = mock.Mock()

        # Header indicates more data needed
        ws._buffer = bytearray(b"\x81\x0a")  # TEXT, len=10

        # Set sock to None to simulate disconnection
        ws.sock = None

        with pytest.raises(ConnectionError, match="WebSocket is not connected"):
            ws.recv()

    def test_sync_recv_sock_none_on_incomplete_header(self):
        """Test sync recv when sock is None with incomplete header (line 174)."""
        ws = WebSocket("ws://example.com/")
        ws.connected = True
        ws._buffer = bytearray(b"\x81")  # Incomplete header
        ws.sock = None

        with pytest.raises(ConnectionError, match="WebSocket is not connected"):
            ws.recv()

    def test_sync_recv_connection_closed_on_incomplete_header(self):
        """Test sync recv when connection closes on incomplete header (line 178)."""
        ws = WebSocket("ws://example.com/")
        ws.connected = True
        mock_sock = mock.Mock()
        ws.sock = mock_sock
        ws._buffer = bytearray(b"\x81")  # Incomplete header

        # Mock parse_frame_header to return None
        with mock.patch(
            "reqivo.client.websocket.parse_frame_header", return_value=None
        ):
            # Socket closes when trying to get more data
            mock_sock.recv.return_value = b""

            with pytest.raises(ConnectionError, match="Connection closed"):
                ws.recv()
