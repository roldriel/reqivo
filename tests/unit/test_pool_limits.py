"""tests/unit/test_pool_limits.py

Unit tests for strict connection pool limits and blocking behavior.
"""

import threading
import time
from unittest import mock

import pytest

from reqivo.transport.connection import Connection
from reqivo.transport.connection_pool import ConnectionPool


class TestPoolLimits:
    """Tests for blocking connection pool."""

    @mock.patch("reqivo.transport.connection_pool.Connection")
    def test_pool_limit_blocking(self, MockConnection, timeout_context):
        """Test that get_connection blocks when limit is reached."""
        with timeout_context(5):
            # Setup
            pool = ConnectionPool(max_size=1)
            mock_conn = mock.Mock(spec=Connection)
            mock_conn.is_usable.return_value = True
            mock_conn.sock = mock.Mock()
            mock_conn.host = "example.com"
            mock_conn.port = 80
            mock_conn.use_ssl = False

            MockConnection.return_value = mock_conn

            # Take the only slot
            conn1 = pool.get_connection("example.com", 80, False)

            # Function to try getting second connection
            got_second = False

            def get_second():
                nonlocal got_second
                c = pool.get_connection("example.com", 80, False)
                got_second = True
                pool.put_connection(c)

            # Start thread
            t = threading.Thread(target=get_second)
            t.start()

            # Wait a bit to ensure it blocked
            time.sleep(0.1)
            assert not got_second, "Thread should be blocked waiting for connection"

            # Release first connection
            pool.put_connection(conn1)

            # Wait for thread to finish
            t.join(timeout=1.0)

            assert got_second, "Thread should have acquired connection after release"
            assert not t.is_alive()

    @mock.patch("reqivo.transport.connection_pool.Connection")
    def test_limit_per_host(self, MockConnection):
        """Test that limits are enforcing per host."""
        pool = ConnectionPool(max_size=1)
        mock_conn = mock.Mock(spec=Connection)
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_conn.use_ssl = False
        mock_conn.is_usable.return_value = True
        mock_conn.sock = mock.Mock()
        MockConnection.return_value = mock_conn

        # Take slot for host A
        pool.get_connection("hostA", 80, False)

        # Try getting slot for host B (should succeed)
        mock_conn_b = mock.Mock(spec=Connection)
        mock_conn_b.host = "hostB"
        mock_conn_b.port = 80
        mock_conn_b.use_ssl = False
        # Adjust mock return for second call?
        # MockConnection called twice.

        try:
            conn2 = pool.get_connection("hostB", 80, False)
            assert conn2 is not None
        except Exception:
            pytest.fail("Should not block for different host")

    @mock.patch("reqivo.transport.connection_pool.Connection")
    def test_discard_releases_semaphore(self, MockConnection):
        """Test that discard_connection releases the semaphore."""
        pool = ConnectionPool(max_size=1)
        mock_conn = mock.Mock(spec=Connection)
        mock_conn.is_usable.return_value = True
        mock_conn.sock = mock.Mock()
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_conn.use_ssl = False

        MockConnection.return_value = mock_conn

        # Take slot
        conn = pool.get_connection("example.com", 80, False)

        # Discard it
        pool.discard_connection(conn)

        # Should be able to get another one immediately (non-blocking)
        # Verify by getting in main thread
        conn2 = pool.get_connection("example.com", 80, False)
        assert conn2 is not None
