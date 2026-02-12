"""tests/unit/test_timeouts.py

Unit tests for timeout enforcement in Request.
"""

import socket
from unittest import mock

import pytest

from reqivo.client.request import Request
from reqivo.exceptions import ConnectTimeout, ReadTimeout
from reqivo.transport.connection import Connection
from reqivo.utils.timing import Timeout


class TestSyncTimeouts:
    """Tests for synchronous timeout handling."""

    @mock.patch("reqivo.client.request.Connection")
    def test_connect_timeout_passed_to_connection(self, MockConnection):
        """Test that connect timeout is passed to Connection."""
        # Setup
        mock_conn = mock.Mock(spec=Connection)
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_sock = mock.Mock()
        mock_conn.sock = mock_sock
        mock_sock.recv.side_effect = [b"HTTP/1.1 200 OK\r\n\r\n", b""]

        MockConnection.return_value = mock_conn

        # Execute
        Request.get("http://example.com", timeout=Timeout(connect=2.0, read=5.0))

        # Verify Connection init
        args, kwargs = MockConnection.call_args
        assert kwargs["timeout"].connect == 2.0
        assert kwargs["timeout"].read == 5.0

    @mock.patch("reqivo.client.request.Connection")
    def test_read_timeout_raises_read_timeout(self, MockConnection):
        """Test that socket.timeout during recv raises ReadTimeout."""
        # Setup
        mock_conn = mock.Mock(spec=Connection)
        mock_conn.host = "example.com"
        mock_conn.port = 80
        mock_sock = mock.Mock()
        mock_conn.sock = mock_sock

        # Mock sendall (request)
        mock_sock.sendall.return_value = None

        # Mock recv to raise socket.timeout
        mock_sock.recv.side_effect = socket.timeout("timed out")

        MockConnection.return_value = mock_conn

        # Execute
        with pytest.raises(ReadTimeout):
            Request.get("http://example.com", timeout=1.0)
