"""tests/unit/test_pool_cleanup.py

Unit tests for connection pool cleanup mechanism.
"""

import time
from unittest import mock

import pytest

from reqivo.transport.connection import Connection
from reqivo.transport.connection_pool import ConnectionPool


class TestPoolCleanup:
    """Tests for connection pool cleanup mechanism."""

    @mock.patch("reqivo.transport.connection_pool.Connection")
    def test_expired_connections_cleaned_up(self, MockConnection):
        """Test that expired connections are removed from pool."""
        # Setup pool with very short idle time
        pool = ConnectionPool(max_size=5, max_idle_time=0.1)

        mock_conn = mock.Mock(spec=Connection)
        mock_conn.is_usable.return_value = True
        mock_conn.sock = mock.Mock()
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_conn.use_ssl = False

        MockConnection.return_value = mock_conn

        # Get and return a connection
        conn1 = pool.get_connection("example.com", 80, False)
        pool.put_connection(conn1)

        # Wait for it to expire
        time.sleep(0.15)

        # Get another connection - should trigger cleanup
        # The expired one should be closed
        conn2 = pool.get_connection("example.com", 80, False)

        # Verify the expired connection was closed
        assert mock_conn.close.called

        # Clean up
        pool.put_connection(conn2)

    @mock.patch("reqivo.transport.connection_pool.Connection")
    def test_fresh_connections_not_cleaned(self, MockConnection):
        """Test that fresh connections are not removed."""
        pool = ConnectionPool(max_size=5, max_idle_time=10.0)

        mock_conn = mock.Mock(spec=Connection)
        mock_conn.is_usable.return_value = True
        mock_conn.sock = mock.Mock()
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_conn.use_ssl = False

        MockConnection.return_value = mock_conn

        # Get and return a connection
        conn1 = pool.get_connection("example.com", 80, False)
        pool.put_connection(conn1)

        # Immediately get it back
        conn2 = pool.get_connection("example.com", 80, False)

        # Should be the same connection (reused)
        assert conn2 is conn1

        # Clean up
        pool.put_connection(conn2)

    @mock.patch("reqivo.transport.connection_pool.Connection")
    def test_cleanup_per_host(self, MockConnection):
        """Test that cleanup is per-host."""
        pool = ConnectionPool(max_size=2, max_idle_time=0.1)

        mock_conn_a = mock.Mock(spec=Connection)
        mock_conn_a.is_usable.return_value = True
        mock_conn_a.sock = mock.Mock()
        mock_conn_a.host = "hostA"
        mock_conn_a.port = 80
        mock_conn_a.use_ssl = False

        mock_conn_b = mock.Mock(spec=Connection)
        mock_conn_b.is_usable.return_value = True
        mock_conn_b.sock = mock.Mock()
        mock_conn_b.host = "hostB"
        mock_conn_b.port = 80
        mock_conn_b.use_ssl = False

        # Return different mocks for different hosts
        def side_effect(*args, **kwargs):
            host = args[0] if args else kwargs.get("host")
            if host == "hostA":
                return mock_conn_a
            return mock_conn_b

        MockConnection.side_effect = side_effect

        # Get connections for both hosts
        connA = pool.get_connection("hostA", 80, False)
        connB = pool.get_connection("hostB", 80, False)

        # Return them
        pool.put_connection(connA)
        pool.put_connection(connB)

        # Wait for expiry
        time.sleep(0.15)

        # Get from hostA - should trigger cleanup for hostA only
        pool.get_connection("hostA", 80, False)

        # Verify hostA connection was closed
        assert mock_conn_a.close.called

        # hostB connection should not be closed yet
        # (it will be closed when we get from hostB)
