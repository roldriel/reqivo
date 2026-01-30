"""Unit tests for reqivo.transport.connection module.

This module provides comprehensive test coverage for Connection and AsyncConnection classes,
which handle low-level TCP and TLS connection management.

Test Coverage:
    - Connection initialization (sync and async)
    - TCP connection establishment (with and without TLS)
    - Timeout handling (connect and read timeouts)
    - Error handling (network errors, TLS errors, timeouts)
    - Connection lifecycle (open, close, context manager)
    - Connection health checks (is_usable)

Testing Strategy:
    - Uses unittest.mock to simulate socket operations
    - Tests both synchronous (Connection) and asynchronous (AsyncConnection) variants
    - Validates proper exception raising and error messages
"""

import asyncio
import socket
import ssl
from typing import Any
from unittest import mock

import pytest

from reqivo.exceptions import ConnectTimeout, NetworkError, TlsError
from reqivo.transport.connection import AsyncConnection, Connection
from reqivo.utils.timing import Timeout

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def basic_connection() -> Connection:
    """Create a basic TCP Connection instance for testing.

    Returns:
        Connection: Connection to localhost:80 without TLS.
    """
    return Connection("localhost", 80, use_ssl=False)


@pytest.fixture
def ssl_connection() -> Connection:
    """Create a TLS-enabled Connection instance for testing.

    Returns:
        Connection: Connection to example.com:443 with TLS.
    """
    return Connection("example.com", 443, use_ssl=True)


@pytest.fixture
def async_connection() -> AsyncConnection:
    """Create a basic AsyncConnection instance for testing.

    Returns:
        AsyncConnection: Async connection to localhost:80 without TLS.
    """
    return AsyncConnection("localhost", 80, use_ssl=False)


@pytest.fixture
def mock_socket() -> mock.Mock:
    """Create a mock socket object for testing.

    Returns:
        mock.Mock: Mock socket with common methods stubbed.
    """
    sock = mock.Mock(spec=socket.socket)
    sock.settimeout = mock.Mock()
    sock.close = mock.Mock()
    sock.recv = mock.Mock(return_value=b"")
    return sock


# ============================================================================
# TEST CLASS: Connection Initialization
# ============================================================================


class TestConnectionInit:
    """Tests for Connection.__init__() method."""

    def test_init_basic_parameters(self) -> None:
        """Test Connection initialization with basic parameters."""
        conn = Connection("example.com", 8080)

        assert conn.host == "example.com"
        assert conn.port == 8080
        assert conn.use_ssl is False
        assert conn.timeout is None
        assert conn.sock is None

    def test_init_with_ssl_enabled(self) -> None:
        """Test Connection initialization with TLS enabled."""
        conn = Connection("secure.example.com", 443, use_ssl=True)

        assert conn.host == "secure.example.com"
        assert conn.port == 443
        assert conn.use_ssl is True

    def test_init_with_float_timeout(self) -> None:
        """Test Connection initialization with float timeout."""
        conn = Connection("example.com", 80, timeout=30.0)

        assert conn.timeout is not None
        assert isinstance(conn.timeout, Timeout)
        assert conn.timeout.total == 30.0

    def test_init_with_timeout_object(self) -> None:
        """Test Connection initialization with Timeout object."""
        timeout_obj = Timeout(connect=5.0, read=10.0, total=30.0)
        conn = Connection("example.com", 80, timeout=timeout_obj)

        assert conn.timeout == timeout_obj
        assert conn.timeout.connect == 5.0
        assert conn.timeout.read == 10.0

    def test_init_with_none_timeout(self) -> None:
        """Test Connection initialization with explicit None timeout."""
        conn = Connection("example.com", 80, timeout=None)

        assert conn.timeout is None


# ============================================================================
# TEST CLASS: Connection.open() - Success Cases
# ============================================================================


class TestConnectionOpen:
    """Tests for successful connection establishment."""

    @mock.patch("socket.create_connection")
    def test_open_tcp_connection_success(
        self,
        mock_create: mock.Mock,
        basic_connection: Connection,
        mock_socket: mock.Mock,
    ) -> None:
        """Test successful TCP connection establishment."""
        mock_create.return_value = mock_socket

        result = basic_connection.open()

        mock_create.assert_called_once_with(("localhost", 80), timeout=None)
        assert result == mock_socket
        assert basic_connection.sock == mock_socket
        mock_socket.settimeout.assert_called_once_with(None)

    @mock.patch("ssl.create_default_context")
    @mock.patch("socket.create_connection")
    def test_open_tls_connection_success(
        self,
        mock_create: mock.Mock,
        mock_ssl_context: mock.Mock,
        ssl_connection: Connection,
        mock_socket: mock.Mock,
    ) -> None:
        """Test successful TLS connection establishment."""
        raw_sock = mock.Mock(spec=socket.socket)
        mock_create.return_value = raw_sock

        wrapped_sock = mock.Mock(spec=ssl.SSLSocket)
        mock_context = mock.Mock()
        mock_context.wrap_socket.return_value = wrapped_sock
        mock_ssl_context.return_value = mock_context

        result = ssl_connection.open()

        mock_create.assert_called_once_with(("example.com", 443), timeout=None)
        mock_ssl_context.assert_called_once()
        mock_context.wrap_socket.assert_called_once_with(
            raw_sock, server_hostname="example.com"
        )
        assert result == wrapped_sock
        assert ssl_connection.sock == wrapped_sock

    @mock.patch("socket.create_connection")
    def test_open_with_connect_timeout(
        self, mock_create: mock.Mock, mock_socket: mock.Mock
    ) -> None:
        """Test connection with connect timeout specified."""
        timeout_obj = Timeout(connect=5.0, read=30.0)
        conn = Connection("example.com", 80, timeout=timeout_obj)
        mock_create.return_value = mock_socket

        conn.open()

        # Should use connect timeout for socket.create_connection
        mock_create.assert_called_once_with(("example.com", 80), timeout=5.0)
        # Should set read timeout after connection
        mock_socket.settimeout.assert_called_once_with(30.0)

    @mock.patch("socket.create_connection")
    def test_open_with_total_timeout_only(
        self, mock_create: mock.Mock, mock_socket: mock.Mock
    ) -> None:
        """Test connection with only total timeout (no connect/read split)."""
        timeout_obj = Timeout(total=20.0)
        conn = Connection("example.com", 80, timeout=timeout_obj)
        mock_create.return_value = mock_socket

        conn.open()

        # Should use total for both connect and read
        mock_create.assert_called_once_with(("example.com", 80), timeout=20.0)
        mock_socket.settimeout.assert_called_once_with(20.0)

    @mock.patch("socket.create_connection")
    def test_open_sets_read_timeout_after_connection(
        self, mock_create: mock.Mock, mock_socket: mock.Mock
    ) -> None:
        """Test that read timeout is set on socket after connection."""
        timeout_obj = Timeout(connect=5.0, read=30.0)
        conn = Connection("example.com", 80, timeout=timeout_obj)
        mock_create.return_value = mock_socket

        conn.open()

        # Verify settimeout was called with read timeout
        mock_socket.settimeout.assert_called_once_with(30.0)


# ============================================================================
# TEST CLASS: Connection.open() - Error Cases
# ============================================================================


class TestConnectionOpenErrors:
    """Tests for connection establishment error handling."""

    @mock.patch("socket.create_connection")
    def test_open_raises_connect_timeout_on_socket_timeout(
        self, mock_create: mock.Mock, basic_connection: Connection
    ) -> None:
        """Test that ConnectTimeout is raised when socket.timeout occurs."""
        mock_create.side_effect = socket.timeout("Connection timed out")

        with pytest.raises(ConnectTimeout) as exc_info:
            basic_connection.open()

        assert "Timeout connecting to localhost:80" in str(exc_info.value)

    @mock.patch("socket.create_connection")
    def test_open_raises_network_error_on_socket_error(
        self, mock_create: mock.Mock, basic_connection: Connection
    ) -> None:
        """Test that NetworkError is raised on general socket errors."""
        mock_create.side_effect = socket.error("Connection refused")

        with pytest.raises(NetworkError) as exc_info:
            basic_connection.open()

        assert "Connection error to localhost:80" in str(exc_info.value)

    @mock.patch("ssl.create_default_context")
    @mock.patch("socket.create_connection")
    def test_open_raises_tls_error_on_ssl_error(
        self, mock_create: mock.Mock, mock_ssl_context: mock.Mock
    ) -> None:
        """Test that TlsError is raised on SSL/TLS errors."""
        raw_sock = mock.Mock(spec=socket.socket)
        mock_create.return_value = raw_sock

        mock_context = mock.Mock()
        mock_context.wrap_socket.side_effect = ssl.SSLError("Certificate verify failed")
        mock_ssl_context.return_value = mock_context

        conn = Connection("badssl.com", 443, use_ssl=True)

        with pytest.raises(TlsError) as exc_info:
            conn.open()

        assert "TLS Verification Error" in str(exc_info.value)

    @mock.patch("ssl.create_default_context")
    @mock.patch("socket.create_connection")
    def test_open_raises_connect_timeout_on_tls_handshake_timeout(
        self, mock_create: mock.Mock, mock_ssl_context: mock.Mock
    ) -> None:
        """Test that ConnectTimeout is raised when TLS handshake times out."""
        raw_sock = mock.Mock(spec=socket.socket)
        mock_create.return_value = raw_sock

        mock_context = mock.Mock()
        mock_context.wrap_socket.side_effect = socket.timeout("TLS handshake timeout")
        mock_ssl_context.return_value = mock_context

        conn = Connection("example.com", 443, use_ssl=True)

        with pytest.raises(ConnectTimeout) as exc_info:
            conn.open()

        assert "Timeout during TLS handshake" in str(exc_info.value)

    @mock.patch("socket.create_connection")
    def test_open_handles_socket_timeout_as_network_error_subtype(
        self, mock_create: mock.Mock
    ) -> None:
        """Test that socket.timeout (subclass of OSError) is handled correctly."""
        # socket.timeout is a subclass of socket.error/OSError
        mock_create.side_effect = socket.timeout("Timeout")

        conn = Connection("example.com", 80)

        with pytest.raises(ConnectTimeout):
            conn.open()


# ============================================================================
# TEST CLASS: Connection.close()
# ============================================================================


class TestConnectionClose:
    """Tests for connection closing."""

    def test_close_with_open_socket(
        self, basic_connection: Connection, mock_socket: mock.Mock
    ) -> None:
        """Test closing an open connection."""
        basic_connection.sock = mock_socket

        basic_connection.close()

        mock_socket.close.assert_called_once()
        assert basic_connection.sock is None

    def test_close_with_no_socket(self, basic_connection: Connection) -> None:
        """Test closing when no socket exists (no-op)."""
        basic_connection.sock = None

        # Should not raise any exception
        basic_connection.close()

        assert basic_connection.sock is None

    def test_close_handles_socket_error_gracefully(
        self, basic_connection: Connection
    ) -> None:
        """Test that close handles socket errors during close gracefully."""
        mock_sock = mock.Mock(spec=socket.socket)
        mock_sock.close.side_effect = OSError("Socket already closed")
        basic_connection.sock = mock_sock

        # Should not raise exception
        basic_connection.close()

        assert basic_connection.sock is None


# ============================================================================
# TEST CLASS: Connection Context Manager
# ============================================================================


class TestConnectionContextManager:
    """Tests for Connection as context manager."""

    @mock.patch("socket.create_connection")
    def test_context_manager_opens_and_closes(
        self, mock_create: mock.Mock, mock_socket: mock.Mock
    ) -> None:
        """Test that context manager opens connection on enter and closes on exit."""
        mock_create.return_value = mock_socket
        conn = Connection("example.com", 80)

        with conn as context_conn:
            assert context_conn is conn
            assert conn.sock == mock_socket

        # Verify close was called
        mock_socket.close.assert_called_once()
        assert conn.sock is None

    @mock.patch("socket.create_connection")
    def test_context_manager_closes_even_on_exception(
        self, mock_create: mock.Mock, mock_socket: mock.Mock
    ) -> None:
        """Test that connection is closed even if exception occurs in with block."""
        mock_create.return_value = mock_socket
        conn = Connection("example.com", 80)

        with pytest.raises(ValueError):
            with conn:
                raise ValueError("Test exception")

        # Should still close connection
        mock_socket.close.assert_called_once()
        assert conn.sock is None


# ============================================================================
# TEST CLASS: Connection.is_usable()
# ============================================================================


class TestConnectionIsUsable:
    """Tests for connection health checks."""

    def test_is_usable_returns_false_when_no_socket(
        self, basic_connection: Connection
    ) -> None:
        """Test that is_usable returns False when sock is None."""
        basic_connection.sock = None

        assert basic_connection.is_usable() is False

    @mock.patch("select.select")
    def test_is_usable_returns_true_for_healthy_connection(
        self,
        mock_select: mock.Mock,
        basic_connection: Connection,
        mock_socket: mock.Mock,
    ) -> None:
        """Test that is_usable returns True for healthy connection."""
        basic_connection.sock = mock_socket
        # select returns empty lists (socket not readable)
        mock_select.return_value = ([], [], [])

        assert basic_connection.is_usable() is True
        mock_select.assert_called_once_with([mock_socket], [], [], 0)

    @mock.patch("select.select")
    def test_is_usable_returns_false_when_connection_closed_by_peer(
        self,
        mock_select: mock.Mock,
        basic_connection: Connection,
        mock_socket: mock.Mock,
    ) -> None:
        """Test that is_usable returns False when peer closed connection."""
        basic_connection.sock = mock_socket
        # Socket is readable
        mock_select.return_value = ([mock_socket], [], [])
        # recv with MSG_PEEK returns empty (connection closed)
        mock_socket.recv.return_value = b""

        assert basic_connection.is_usable() is False

    @mock.patch("select.select")
    def test_is_usable_returns_false_when_socket_has_pending_data(
        self,
        mock_select: mock.Mock,
        basic_connection: Connection,
        mock_socket: mock.Mock,
    ) -> None:
        """Test that is_usable returns False when socket has unexpected pending data.

        Pooled connections should not have pending data. If they do, it's stale data
        from a previous request and the connection should be considered unusable.
        """
        basic_connection.sock = mock_socket
        # Socket is readable
        mock_select.return_value = ([mock_socket], [], [])
        # recv with MSG_PEEK finds data (stale data in buffer)
        mock_socket.recv.return_value = b"unexpected data"

        assert basic_connection.is_usable() is False

    @mock.patch("select.select")
    def test_is_usable_returns_false_on_socket_error_during_peek(
        self,
        mock_select: mock.Mock,
        basic_connection: Connection,
        mock_socket: mock.Mock,
    ) -> None:
        """Test that is_usable returns False when socket error occurs during recv."""
        basic_connection.sock = mock_socket
        mock_select.return_value = ([mock_socket], [], [])
        mock_socket.recv.side_effect = socket.error("Connection reset by peer")

        assert basic_connection.is_usable() is False

    @mock.patch("select.select")
    def test_is_usable_returns_false_on_select_error(
        self,
        mock_select: mock.Mock,
        basic_connection: Connection,
        mock_socket: mock.Mock,
    ) -> None:
        """Test that is_usable returns False when select() raises error."""
        basic_connection.sock = mock_socket
        mock_select.side_effect = OSError("Bad file descriptor")

        assert basic_connection.is_usable() is False


# ============================================================================
# TEST CLASS: AsyncConnection Initialization
# ============================================================================


class TestAsyncConnectionInit:
    """Tests for AsyncConnection.__init__() method."""

    def test_init_basic_parameters(self) -> None:
        """Test AsyncConnection initialization with basic parameters."""
        conn = AsyncConnection("example.com", 8080)

        assert conn.host == "example.com"
        assert conn.port == 8080
        assert conn.use_ssl is False
        assert conn.timeout is None
        assert conn.reader is None
        assert conn.writer is None

    def test_init_with_ssl(self) -> None:
        """Test AsyncConnection initialization with TLS."""
        conn = AsyncConnection("secure.example.com", 443, use_ssl=True)

        assert conn.use_ssl is True

    def test_init_with_timeout_object(self) -> None:
        """Test AsyncConnection initialization with Timeout object."""
        timeout_obj = Timeout(connect=5.0, read=10.0)
        conn = AsyncConnection("example.com", 80, timeout=timeout_obj)

        assert conn.timeout == timeout_obj

    def test_init_with_float_timeout(self) -> None:
        """Test AsyncConnection initialization with float timeout."""
        conn = AsyncConnection("example.com", 80, timeout=5.0)

        # Should convert float to Timeout using Timeout.from_float()
        assert conn.timeout is not None
        assert conn.timeout.connect == 5.0
        assert conn.timeout.read == 5.0
        assert conn.timeout.total == 5.0


# ============================================================================
# TEST CLASS: AsyncConnection.open()
# ============================================================================


class TestAsyncConnectionOpen:
    """Tests for asynchronous connection establishment."""

    @pytest.mark.asyncio
    async def test_async_open_success(self, async_connection: AsyncConnection) -> None:
        """Test successful async connection establishment."""
        mock_reader = mock.Mock(spec=asyncio.StreamReader)
        mock_writer = mock.Mock(spec=asyncio.StreamWriter)

        with mock.patch("asyncio.open_connection") as mock_open:
            mock_open.return_value = (mock_reader, mock_writer)

            await async_connection.open()

            mock_open.assert_called_once_with("localhost", 80, ssl=None)
            assert async_connection.reader == mock_reader
            assert async_connection.writer == mock_writer

    @pytest.mark.asyncio
    async def test_async_open_with_ssl(self) -> None:
        """Test async connection with TLS."""
        conn = AsyncConnection("example.com", 443, use_ssl=True)
        mock_reader = mock.Mock()
        mock_writer = mock.Mock()

        with mock.patch("asyncio.open_connection") as mock_open:
            with mock.patch("ssl.create_default_context") as mock_ssl:
                mock_context = mock.Mock()
                mock_ssl.return_value = mock_context
                mock_open.return_value = (mock_reader, mock_writer)

                await conn.open()

                mock_ssl.assert_called_once()
                mock_open.assert_called_once_with("example.com", 443, ssl=mock_context)

    @pytest.mark.asyncio
    async def test_async_open_with_timeout(self) -> None:
        """Test async connection with connect timeout."""
        timeout_obj = Timeout(connect=5.0)
        conn = AsyncConnection("example.com", 80, timeout=timeout_obj)
        mock_reader = mock.Mock()
        mock_writer = mock.Mock()

        with mock.patch("asyncio.open_connection") as mock_open:
            with mock.patch("asyncio.wait_for") as mock_wait:
                mock_wait.return_value = (mock_reader, mock_writer)

                await conn.open()

                # Verify wait_for was called with timeout
                assert mock_wait.called
                call_args = mock_wait.call_args
                assert call_args[1]["timeout"] == 5.0

    @pytest.mark.asyncio
    async def test_async_open_raises_connect_timeout_on_timeout_error(
        self, async_connection: AsyncConnection
    ) -> None:
        """Test that ConnectTimeout is raised on asyncio.TimeoutError."""
        with mock.patch("asyncio.open_connection") as mock_open:
            mock_open.side_effect = asyncio.TimeoutError()

            with pytest.raises(ConnectTimeout) as exc_info:
                await async_connection.open()

            assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_async_open_raises_tls_error_on_ssl_error(self) -> None:
        """Test that TlsError is raised on SSL errors during async connection."""
        conn = AsyncConnection("badssl.com", 443, use_ssl=True)

        with mock.patch("asyncio.open_connection") as mock_open:
            with mock.patch("ssl.create_default_context"):
                mock_open.side_effect = ssl.SSLError("Certificate verification failed")

                with pytest.raises(TlsError):
                    await conn.open()

    @pytest.mark.asyncio
    async def test_async_open_raises_network_error_on_general_exception(
        self, async_connection: AsyncConnection
    ) -> None:
        """Test that NetworkError is raised on other exceptions."""
        with mock.patch("asyncio.open_connection") as mock_open:
            mock_open.side_effect = OSError("Connection refused")

            with pytest.raises(NetworkError) as exc_info:
                await async_connection.open()

            assert "Failed to connect" in str(exc_info.value)


# ============================================================================
# TEST CLASS: AsyncConnection.close() and is_usable()
# ============================================================================


class TestAsyncConnectionClose:
    """Tests for async connection closing and health checks."""

    @pytest.mark.asyncio
    async def test_async_close(self) -> None:
        """Test async connection close."""
        conn = AsyncConnection("example.com", 80)
        mock_writer = mock.Mock(spec=asyncio.StreamWriter)
        mock_writer.close = mock.Mock()
        mock_writer.wait_closed = mock.AsyncMock()

        conn.reader = mock.Mock()
        conn.writer = mock_writer

        await conn.close()

        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_awaited_once()
        assert conn.reader is None
        assert conn.writer is None

    @pytest.mark.asyncio
    async def test_async_close_with_no_writer(self) -> None:
        """Test async close when writer is None (no-op)."""
        conn = AsyncConnection("example.com", 80)
        conn.writer = None

        # Should not raise
        await conn.close()

        assert conn.writer is None

    @pytest.mark.asyncio
    async def test_async_close_handles_exception_gracefully(self) -> None:
        """Test that async close handles exceptions during wait_closed."""
        conn = AsyncConnection("example.com", 80)
        mock_writer = mock.Mock(spec=asyncio.StreamWriter)
        mock_writer.close = mock.Mock()
        mock_writer.wait_closed = mock.AsyncMock(
            side_effect=Exception("Already closed")
        )

        conn.writer = mock_writer

        # Should not raise
        await conn.close()

        assert conn.writer is None

    def test_async_is_usable_returns_false_when_no_writer(self) -> None:
        """Test that is_usable returns False when writer is None."""
        conn = AsyncConnection("example.com", 80)
        conn.writer = None

        assert conn.is_usable() is False

    def test_async_is_usable_returns_true_when_writer_open(self) -> None:
        """Test that is_usable returns True when writer is open."""
        conn = AsyncConnection("example.com", 80)
        mock_writer = mock.Mock(spec=asyncio.StreamWriter)
        mock_writer.is_closing.return_value = False

        conn.writer = mock_writer

        assert conn.is_usable() is True

    def test_async_is_usable_returns_false_when_writer_closing(self) -> None:
        """Test that is_usable returns False when writer is closing."""
        conn = AsyncConnection("example.com", 80)
        mock_writer = mock.Mock(spec=asyncio.StreamWriter)
        mock_writer.is_closing.return_value = True

        conn.writer = mock_writer

        assert conn.is_usable() is False
