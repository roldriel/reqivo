"""tests/unit/test_websocket_reconnect.py

Unit tests for WebSocket auto-reconnect and configurable frame limits
added in v0.3.0 (Fase 4).

Test Coverage:
    - Auto-reconnect successful after failure (sync and async)
    - Reconnect attempts exhausted raises exception
    - Auto-reconnect disabled by default
    - Backoff exponential delay
    - Configurable max_frame_size
    - Default max_frame_size matches MAX_FRAME_SIZE constant

Testing Strategy:
    - Mock socket/connection to simulate connection failures
    - Verify reconnect attempts and backoff timing
    - Test configurable frame size limit
"""

from unittest import mock

import pytest

from reqivo.client.websocket import (
    MAX_FRAME_SIZE,
    AsyncWebSocket,
    WebSocket,
)
from reqivo.utils.websocket_utils import WebSocketError

# ============================================================================
# TEST CLASS: Default Configuration
# ============================================================================


class TestWebSocketDefaults:
    """Tests for default configuration values."""

    def test_default_max_frame_size(self) -> None:
        """Test that default max_frame_size equals MAX_FRAME_SIZE."""
        ws = WebSocket("ws://example.com/")
        assert ws.max_frame_size == MAX_FRAME_SIZE

    def test_default_auto_reconnect_disabled(self) -> None:
        """Test that auto_reconnect is disabled by default."""
        ws = WebSocket("ws://example.com/")
        assert ws._auto_reconnect is False

    def test_default_max_reconnect_attempts(self) -> None:
        """Test default max_reconnect_attempts is 3."""
        ws = WebSocket("ws://example.com/")
        assert ws._max_reconnect_attempts == 3

    def test_default_reconnect_delay(self) -> None:
        """Test default reconnect_delay is 1.0."""
        ws = WebSocket("ws://example.com/")
        assert ws._reconnect_delay == 1.0

    def test_async_default_max_frame_size(self) -> None:
        """Test AsyncWebSocket default max_frame_size."""
        ws = AsyncWebSocket("ws://example.com/")
        assert ws.max_frame_size == MAX_FRAME_SIZE

    def test_async_default_auto_reconnect_disabled(self) -> None:
        """Test AsyncWebSocket auto_reconnect disabled by default."""
        ws = AsyncWebSocket("ws://example.com/")
        assert ws._auto_reconnect is False


# ============================================================================
# TEST CLASS: Custom Configuration
# ============================================================================


class TestWebSocketCustomConfig:
    """Tests for custom configuration values."""

    def test_custom_max_frame_size(self) -> None:
        """Test setting a custom max_frame_size."""
        ws = WebSocket("ws://example.com/", max_frame_size=1024)
        assert ws.max_frame_size == 1024

    def test_custom_auto_reconnect(self) -> None:
        """Test enabling auto_reconnect."""
        ws = WebSocket(
            "ws://example.com/",
            auto_reconnect=True,
            max_reconnect_attempts=5,
            reconnect_delay=2.0,
        )
        assert ws._auto_reconnect is True
        assert ws._max_reconnect_attempts == 5
        assert ws._reconnect_delay == 2.0

    def test_async_custom_max_frame_size(self) -> None:
        """Test AsyncWebSocket custom max_frame_size."""
        ws = AsyncWebSocket("ws://example.com/", max_frame_size=2048)
        assert ws.max_frame_size == 2048

    def test_async_custom_auto_reconnect(self) -> None:
        """Test AsyncWebSocket custom auto_reconnect settings."""
        ws = AsyncWebSocket(
            "ws://example.com/",
            auto_reconnect=True,
            max_reconnect_attempts=10,
            reconnect_delay=0.5,
        )
        assert ws._auto_reconnect is True
        assert ws._max_reconnect_attempts == 10
        assert ws._reconnect_delay == 0.5


# ============================================================================
# TEST CLASS: Sync Auto-Reconnect
# ============================================================================


class TestSyncAutoReconnect:
    """Tests for sync WebSocket auto-reconnect."""

    @mock.patch("reqivo.client.websocket.time.sleep")
    @mock.patch.object(WebSocket, "connect")
    def test_reconnect_on_send_failure(
        self, mock_connect: mock.Mock, mock_sleep: mock.Mock
    ) -> None:
        """Test that send reconnects after connection failure."""
        ws = WebSocket(
            "ws://example.com/",
            auto_reconnect=True,
            max_reconnect_attempts=3,
            reconnect_delay=1.0,
        )
        ws.connected = True

        mock_sock = mock.Mock()
        call_count = 0

        def sendall_side_effect(data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("broken")

        mock_sock.sendall.side_effect = sendall_side_effect
        ws.sock = mock_sock

        # connect() must restore sock after _reconnect() sets it to None
        def connect_side_effect():
            ws.sock = mock_sock
            ws.connected = True

        mock_connect.side_effect = connect_side_effect

        ws.send("hello")

        mock_connect.assert_called_once()
        mock_sleep.assert_called_once_with(1.0)  # delay * 2^0

    @mock.patch("reqivo.client.websocket.time.sleep")
    @mock.patch.object(WebSocket, "connect")
    def test_reconnect_exhausted_raises(
        self, mock_connect: mock.Mock, mock_sleep: mock.Mock
    ) -> None:
        """Test that exhausted reconnect attempts raise the exception."""
        ws = WebSocket(
            "ws://example.com/",
            auto_reconnect=True,
            max_reconnect_attempts=2,
            reconnect_delay=0.1,
        )
        ws.connected = True

        mock_sock = mock.Mock()
        mock_sock.sendall.side_effect = ConnectionError("broken")
        ws.sock = mock_sock

        def connect_side_effect():
            ws.sock = mock_sock
            ws.connected = True

        mock_connect.side_effect = connect_side_effect

        with pytest.raises(ConnectionError, match="broken"):
            ws.send("hello")

        # Should have attempted 2 reconnects (connect calls)
        assert mock_connect.call_count == 2

    def test_no_reconnect_when_disabled(self) -> None:
        """Test that auto_reconnect=False does not attempt reconnect."""
        ws = WebSocket("ws://example.com/", auto_reconnect=False)
        ws.connected = True

        mock_sock = mock.Mock()
        mock_sock.sendall.side_effect = ConnectionError("broken")
        ws.sock = mock_sock

        with pytest.raises(ConnectionError, match="broken"):
            ws.send("hello")

    @mock.patch("reqivo.client.websocket.time.sleep")
    @mock.patch.object(WebSocket, "connect")
    def test_exponential_backoff(
        self, mock_connect: mock.Mock, mock_sleep: mock.Mock
    ) -> None:
        """Test that reconnect uses exponential backoff delay."""
        ws = WebSocket(
            "ws://example.com/",
            auto_reconnect=True,
            max_reconnect_attempts=3,
            reconnect_delay=1.0,
        )
        ws.connected = True

        mock_sock = mock.Mock()
        call_count = 0

        def sendall_side_effect(data):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ConnectionError(f"fail {call_count}")

        mock_sock.sendall.side_effect = sendall_side_effect
        ws.sock = mock_sock

        def connect_side_effect():
            ws.sock = mock_sock
            ws.connected = True

        mock_connect.side_effect = connect_side_effect

        ws.send("hello")

        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [1.0, 2.0, 4.0]  # 1*2^0, 1*2^1, 1*2^2

    @mock.patch.object(WebSocket, "connect")
    def test_reconnect_resets_buffer(self, mock_connect: mock.Mock) -> None:
        """Test that _reconnect clears the buffer."""
        ws = WebSocket("ws://example.com/")
        ws.connected = True
        ws._buffer = bytearray(b"old data")
        ws.sock = mock.Mock()

        ws._reconnect()

        assert ws._buffer == bytearray()
        mock_connect.assert_called_once()


# ============================================================================
# TEST CLASS: Async Auto-Reconnect
# ============================================================================


class TestAsyncAutoReconnect:
    """Tests for async WebSocket auto-reconnect."""

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.asyncio.sleep", new_callable=mock.AsyncMock)
    @mock.patch.object(AsyncWebSocket, "connect", new_callable=mock.AsyncMock)
    async def test_async_reconnect_on_send_failure(
        self, mock_connect: mock.AsyncMock, mock_sleep: mock.AsyncMock
    ) -> None:
        """Test that async send reconnects after connection failure."""
        ws = AsyncWebSocket(
            "ws://example.com/",
            auto_reconnect=True,
            max_reconnect_attempts=3,
            reconnect_delay=1.0,
        )
        ws.connected = True

        mock_writer = mock.Mock()
        mock_writer.drain = mock.AsyncMock()
        call_count = 0

        def write_side_effect(data):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("broken")

        mock_writer.write.side_effect = write_side_effect
        ws.writer = mock_writer

        # connect() must restore writer after _reconnect() sets it to None
        async def connect_side_effect():
            ws.writer = mock_writer
            ws.connected = True

        mock_connect.side_effect = connect_side_effect

        await ws.send("hello")

        mock_connect.assert_called_once()
        mock_sleep.assert_called_once_with(1.0)

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.asyncio.sleep", new_callable=mock.AsyncMock)
    @mock.patch.object(AsyncWebSocket, "connect", new_callable=mock.AsyncMock)
    async def test_async_reconnect_exhausted_raises(
        self, mock_connect: mock.AsyncMock, mock_sleep: mock.AsyncMock
    ) -> None:
        """Test that exhausted async reconnect attempts raise."""
        ws = AsyncWebSocket(
            "ws://example.com/",
            auto_reconnect=True,
            max_reconnect_attempts=2,
            reconnect_delay=0.1,
        )
        ws.connected = True

        mock_writer = mock.Mock()
        mock_writer.drain = mock.AsyncMock()
        mock_writer.write.side_effect = ConnectionError("broken")
        ws.writer = mock_writer

        async def connect_side_effect():
            ws.writer = mock_writer
            ws.connected = True

        mock_connect.side_effect = connect_side_effect

        with pytest.raises(ConnectionError, match="broken"):
            await ws.send("hello")

        assert mock_connect.call_count == 2

    @pytest.mark.asyncio
    async def test_async_no_reconnect_when_disabled(self) -> None:
        """Test that async auto_reconnect=False does not attempt reconnect."""
        ws = AsyncWebSocket("ws://example.com/", auto_reconnect=False)
        ws.connected = True

        mock_writer = mock.Mock()
        mock_writer.drain = mock.AsyncMock()
        mock_writer.write.side_effect = ConnectionError("broken")
        ws.writer = mock_writer

        with pytest.raises(ConnectionError, match="broken"):
            await ws.send("hello")

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.websocket.asyncio.sleep", new_callable=mock.AsyncMock)
    @mock.patch.object(AsyncWebSocket, "connect", new_callable=mock.AsyncMock)
    async def test_async_exponential_backoff(
        self, mock_connect: mock.AsyncMock, mock_sleep: mock.AsyncMock
    ) -> None:
        """Test async reconnect exponential backoff."""
        ws = AsyncWebSocket(
            "ws://example.com/",
            auto_reconnect=True,
            max_reconnect_attempts=3,
            reconnect_delay=0.5,
        )
        ws.connected = True

        mock_writer = mock.Mock()
        mock_writer.drain = mock.AsyncMock()
        call_count = 0

        def write_side_effect(data):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ConnectionError(f"fail {call_count}")

        mock_writer.write.side_effect = write_side_effect
        ws.writer = mock_writer

        async def connect_side_effect():
            ws.writer = mock_writer
            ws.connected = True

        mock_connect.side_effect = connect_side_effect

        await ws.send("hello")

        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls == [0.5, 1.0, 2.0]  # 0.5*2^0, 0.5*2^1, 0.5*2^2

    @pytest.mark.asyncio
    @mock.patch.object(AsyncWebSocket, "connect", new_callable=mock.AsyncMock)
    async def test_async_reconnect_resets_state(
        self, mock_connect: mock.AsyncMock
    ) -> None:
        """Test that async _reconnect clears buffer and state."""
        ws = AsyncWebSocket("ws://example.com/")
        ws.connected = True
        ws._buffer = bytearray(b"old data")
        ws.connection = mock.AsyncMock()
        ws.reader = mock.Mock()
        ws.writer = mock.Mock()

        await ws._reconnect()

        assert ws._buffer == bytearray()
        assert ws.reader is None
        assert ws.writer is None
        mock_connect.assert_called_once()
