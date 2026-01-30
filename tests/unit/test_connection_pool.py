"""Unit tests for reqivo.transport.connection_pool module.

Test Coverage:
    - ConnectionPool and AsyncConnectionPool initialization
    - Connection reuse (LIFO strategy)
    - Dead connection detection and cleanup
    - Pool size limits enforcement
    - Thread safety for sync pool
    - Close operations (individual keys and全部)

Testing Strategy:
    - Mock Connection and AsyncConnection to avoid real network I/O
    - Test pool behavior under various conditions
    - Validate LIFO (Last In, First Out) strategy
"""

import threading
from unittest import mock

import pytest

from reqivo.transport.connection import AsyncConnection, Connection
from reqivo.transport.connection_pool import AsyncConnectionPool, ConnectionPool
from reqivo.utils.timing import Timeout

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def pool() -> ConnectionPool:
    """Create a ConnectionPool with default size."""
    return ConnectionPool(max_size=3)


@pytest.fixture
def async_pool() -> AsyncConnectionPool:
    """Create an AsyncConnectionPool with default size."""
    return AsyncConnectionPool(max_size=3)


@pytest.fixture
def mock_conn() -> mock.Mock:
    """Create a mock Connection."""
    conn = mock.Mock(spec=Connection)
    conn.host = "example.com"
    conn.port = 80
    conn.use_ssl = False
    conn.sock = mock.Mock()
    conn.is_usable.return_value = True
    conn.close = mock.Mock()
    conn.open = mock.Mock()
    return conn


# ============================================================================
# TEST CLASS: ConnectionPool
# ============================================================================


class TestConnectionPoolInit:
    """Tests for ConnectionPool initialization."""

    def test_init_default_max_size(self) -> None:
        """Test ConnectionPool with default max_size."""
        pool = ConnectionPool()
        assert pool.max_size == 10
        assert pool._pool == {}

    def test_init_custom_max_size(self) -> None:
        """Test ConnectionPool with custom max_size."""
        pool = ConnectionPool(max_size=20)
        assert pool.max_size == 20


class TestConnectionPoolGetConnection:
    """Tests for get_connection method."""

    @mock.patch("reqivo.transport.connection_pool.Connection")
    def test_get_connection_creates_new_when_pool_empty(
        self, MockConn: mock.Mock, pool: ConnectionPool
    ) -> None:
        """Test creating new connection when pool is empty."""
        mock_instance = mock.Mock(spec=Connection)
        MockConn.return_value = mock_instance

        result = pool.get_connection("example.com", 80, use_ssl=False)

        MockConn.assert_called_once_with("example.com", 80, False, timeout=None)
        mock_instance.open.assert_called_once()
        assert result == mock_instance

    def test_get_connection_reuses_existing_usable_connection(
        self, pool: ConnectionPool, mock_conn: mock.Mock
    ) -> None:
        """Test reusing existing usable connection from pool."""
        # Put connection in pool
        from collections import deque

        key = ("example.com", 80, False)
        pool._pool[key] = deque([mock_conn])

        result = pool.get_connection("example.com", 80, use_ssl=False)

        mock_conn.is_usable.assert_called_once()
        assert result == mock_conn
        mock_conn.open.assert_not_called()  # Should not re-open

    @mock.patch("reqivo.transport.connection_pool.Connection")
    def test_get_connection_discards_dead_connections(
        self, MockConn: mock.Mock, pool: ConnectionPool
    ) -> None:
        """Test that dead connections are discarded and new one created."""
        dead_conn = mock.Mock(spec=Connection)
        dead_conn.is_usable.return_value = False

        key = ("example.com", 80, False)
        from collections import deque

        pool._pool[key] = deque([dead_conn])

        new_conn = mock.Mock(spec=Connection)
        MockConn.return_value = new_conn

        result = pool.get_connection("example.com", 80, use_ssl=False)

        dead_conn.close.assert_called_once()
        new_conn.open.assert_called_once()
        assert result == new_conn


class TestConnectionPoolPutConnection:
    """Tests for put_connection method."""

    def test_put_connection_adds_usable_connection(
        self, pool: ConnectionPool, mock_conn: mock.Mock
    ) -> None:
        """Test adding usable connection to pool."""
        pool.put_connection(mock_conn)

        key = ("example.com", 80, False)
        assert key in pool._pool
        assert mock_conn in pool._pool[key]

    def test_put_connection_ignores_connection_without_socket(
        self, pool: ConnectionPool, mock_conn: mock.Mock
    ) -> None:
        """Test that connection without socket is not added to pool."""
        mock_conn.sock = None

        pool.put_connection(mock_conn)

        assert len(pool._pool) == 0

    def test_put_connection_closes_unusable_connection(
        self, pool: ConnectionPool, mock_conn: mock.Mock
    ) -> None:
        """Test that unusable connection is closed instead of pooled."""
        mock_conn.is_usable.return_value = False

        pool.put_connection(mock_conn)

        mock_conn.close.assert_called_once()
        assert len(pool._pool) == 0

    def test_put_connection_enforces_max_size_lifo(self, pool: ConnectionPool) -> None:
        """Test that max_size is enforced and oldest connection is removed (LIFO)."""
        # Pool max_size is 3
        connections = [mock.Mock(spec=Connection) for _ in range(4)]
        for conn in connections:
            conn.host = "example.com"
            conn.port = 80
            conn.use_ssl = False
            conn.sock = mock.Mock()
            conn.is_usable.return_value = True

        # Add 4 connections (pool max is 3)
        for conn in connections:
            pool.put_connection(conn)

        # First connection should be closed (oldest)
        connections[0].close.assert_called_once()

        # Last 3 should be in pool
        key = ("example.com", 80, False)
        assert len(pool._pool[key]) == 3
        assert connections[1] in pool._pool[key]
        assert connections[2] in pool._pool[key]
        assert connections[3] in pool._pool[key]


class TestConnectionPoolReleaseAndClose:
    """Tests for release_connection and close_all methods."""

    def test_release_connection_closes_all_for_key(self, pool: ConnectionPool) -> None:
        """Test release_connection closes all connections for given key."""
        conns = [mock.Mock(spec=Connection) for _ in range(3)]
        key = ("example.com", 80, False)
        from collections import deque

        pool._pool[key] = deque(conns)

        pool.release_connection("example.com", 80, use_ssl=False)

        for conn in conns:
            conn.close.assert_called_once()
        assert key not in pool._pool

    def test_release_connection_handles_missing_key(self, pool: ConnectionPool) -> None:
        """Test release_connection handles non-existent key gracefully."""
        # Should not raise
        pool.release_connection("nonexistent.com", 80, use_ssl=False)

    def test_close_all_closes_all_connections(self, pool: ConnectionPool) -> None:
        """Test close_all closes all connections in pool."""
        key1 = ("example.com", 80, False)
        key2 = ("another.com", 443, True)

        conns1 = [mock.Mock(spec=Connection) for _ in range(2)]
        conns2 = [mock.Mock(spec=Connection) for _ in range(2)]

        from collections import deque

        pool._pool[key1] = deque(conns1)
        pool._pool[key2] = deque(conns2)

        pool.close_all()

        for conn in conns1 + conns2:
            conn.close.assert_called_once()
        assert len(pool._pool) == 0


class TestConnectionPoolThreadSafety:
    """Tests for thread safety of ConnectionPool."""

    @mock.patch("reqivo.transport.connection_pool.Connection")
    def test_concurrent_get_connection_is_thread_safe(
        self, MockConn: mock.Mock
    ) -> None:
        """Test that concurrent get_connection calls are thread-safe."""
        pool = ConnectionPool(max_size=10)

        # Mock Connection to return different instances
        created_conns = []

        def create_conn(*args, **kwargs):
            conn = mock.Mock(spec=Connection)
            conn.open = mock.Mock()
            created_conns.append(conn)
            return conn

        MockConn.side_effect = create_conn

        # Run 20 threads concurrently getting connections
        threads = []
        results = []

        def get_conn():
            conn = pool.get_connection("example.com", 80, use_ssl=False)
            results.append(conn)

        for _ in range(20):
            t = threading.Thread(target=get_conn)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should have gotten a connection
        assert len(results) == 20
        # All connections should be valid
        assert all(r is not None for r in results)


# ============================================================================
# TEST CLASS: AsyncConnectionPool
# ============================================================================


class TestAsyncConnectionPoolInit:
    """Tests for AsyncConnectionPool initialization."""

    def test_init_default_max_size(self) -> None:
        """Test AsyncConnectionPool with default max_size."""
        pool = AsyncConnectionPool()
        assert pool.max_size == 10
        assert pool._pool == {}


class TestAsyncConnectionPoolGetConnection:
    """Tests for async get_connection method."""

    @pytest.mark.asyncio
    @mock.patch("reqivo.transport.connection_pool.AsyncConnection")
    async def test_get_connection_creates_new_when_empty(
        self, MockConn: mock.Mock, async_pool: AsyncConnectionPool
    ) -> None:
        """Test creating new async connection when pool is empty."""
        mock_instance = mock.Mock(spec=AsyncConnection)
        mock_instance.open = mock.AsyncMock()
        MockConn.return_value = mock_instance

        result = await async_pool.get_connection("example.com", 80, use_ssl=False)

        MockConn.assert_called_once()
        mock_instance.open.assert_awaited_once()
        assert result == mock_instance

    @pytest.mark.asyncio
    async def test_get_connection_reuses_existing(
        self, async_pool: AsyncConnectionPool
    ) -> None:
        """Test reusing existing async connection."""
        mock_conn = mock.Mock(spec=AsyncConnection)
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_conn.use_ssl = False
        mock_conn.is_usable.return_value = True

        key = ("example.com", 80, False)
        async_pool._pool[key] = [mock_conn]

        result = await async_pool.get_connection("example.com", 80, use_ssl=False)

        assert result == mock_conn
        mock_conn.is_usable.assert_called_once()

    @pytest.mark.asyncio
    @mock.patch("reqivo.transport.connection_pool.AsyncConnection")
    async def test_get_connection_discards_dead_connections(
        self, MockConn: mock.Mock, async_pool: AsyncConnectionPool
    ) -> None:
        """Test discarding dead async connections."""
        dead_conn = mock.Mock(spec=AsyncConnection)
        dead_conn.is_usable.return_value = False
        dead_conn.close = mock.AsyncMock()

        key = ("example.com", 80, False)
        async_pool._pool[key] = [dead_conn]

        new_conn = mock.Mock(spec=AsyncConnection)
        new_conn.open = mock.AsyncMock()
        MockConn.return_value = new_conn

        result = await async_pool.get_connection("example.com", 80, use_ssl=False)

        dead_conn.close.assert_awaited_once()
        new_conn.open.assert_awaited_once()
        assert result == new_conn


class TestAsyncConnectionPoolPutConnection:
    """Tests for async put_connection method."""

    @pytest.mark.asyncio
    async def test_put_connection_adds_usable_connection(
        self, async_pool: AsyncConnectionPool
    ) -> None:
        """Test adding usable async connection to pool."""
        mock_conn = mock.Mock(spec=AsyncConnection)
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_conn.use_ssl = False
        mock_conn.is_usable.return_value = True

        await async_pool.put_connection(mock_conn)

        key = ("example.com", 80, False)
        assert key in async_pool._pool
        assert mock_conn in async_pool._pool[key]

    @pytest.mark.asyncio
    async def test_put_connection_closes_unusable(
        self, async_pool: AsyncConnectionPool
    ) -> None:
        """Test that unusable async connection is closed."""
        mock_conn = mock.Mock(spec=AsyncConnection)
        mock_conn.is_usable.return_value = False
        mock_conn.close = mock.AsyncMock()

        await async_pool.put_connection(mock_conn)

        mock_conn.close.assert_awaited_once()
        assert len(async_pool._pool) == 0

    @pytest.mark.asyncio
    async def test_put_connection_enforces_max_size(
        self, async_pool: AsyncConnectionPool
    ) -> None:
        """Test max_size enforcement for async pool."""
        # Pool max_size is 3
        connections = []
        for _ in range(4):
            conn = mock.Mock(spec=AsyncConnection)
            conn.host = "example.com"
            conn.port = 80
            conn.use_ssl = False
            conn.is_usable.return_value = True
            conn.close = mock.AsyncMock()
            connections.append(conn)

        for conn in connections:
            await async_pool.put_connection(conn)

        # First (oldest) should be closed
        connections[0].close.assert_awaited_once()

        # Last 3 should be in pool
        key = ("example.com", 80, False)
        assert len(async_pool._pool[key]) == 3


class TestAsyncConnectionPoolClose:
    """Tests for async close operations."""

    @pytest.mark.asyncio
    async def test_release_connection_closes_all_for_key(
        self, async_pool: AsyncConnectionPool
    ) -> None:
        """Test async release_connection closes all for key."""
        conns = []
        for _ in range(3):
            conn = mock.Mock(spec=AsyncConnection)
            conn.close = mock.AsyncMock()
            conns.append(conn)

        key = ("example.com", 80, False)
        async_pool._pool[key] = conns

        await async_pool.release_connection("example.com", 80, use_ssl=False)

        for conn in conns:
            conn.close.assert_awaited_once()
        assert key not in async_pool._pool

    @pytest.mark.asyncio
    async def test_close_all_closes_all_connections(
        self, async_pool: AsyncConnectionPool
    ) -> None:
        """Test async close_all closes all connections."""
        key1 = ("example.com", 80, False)
        key2 = ("another.com", 443, True)

        conns1 = [
            mock.Mock(spec=AsyncConnection, close=mock.AsyncMock()) for _ in range(2)
        ]
        conns2 = [
            mock.Mock(spec=AsyncConnection, close=mock.AsyncMock()) for _ in range(2)
        ]

        async_pool._pool[key1] = conns1
        async_pool._pool[key2] = conns2

        await async_pool.close_all()

        for conn in conns1 + conns2:
            conn.close.assert_awaited_once()
        assert len(async_pool._pool) == 0
