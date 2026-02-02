"""tests/unit/test_body.py"""

from unittest import mock

import pytest

from reqivo.http.body import iter_read_chunked, read_chunked, read_exact


class TestReadExact:
    """Tests for read_exact function."""

    def test_read_exact_single_chunk(self):
        """Test reading exact number of bytes in single chunk."""
        mock_sock = mock.Mock()
        mock_sock.recv.return_value = b"Hello"

        result = read_exact(mock_sock, 5)

        assert result == b"Hello"
        mock_sock.recv.assert_called_once_with(5)

    def test_read_exact_multiple_chunks(self):
        """Test reading exact bytes across multiple chunks."""
        mock_sock = mock.Mock()
        # Simulate receiving data in smaller chunks
        mock_sock.recv.side_effect = [b"Hel", b"lo", b" Wor", b"ld"]

        result = read_exact(mock_sock, 11)

        assert result == b"Hello World"
        assert mock_sock.recv.call_count == 4

    def test_read_exact_socket_closed_prematurely(self):
        """Test read_exact raises EOFError when socket closes early."""
        mock_sock = mock.Mock()
        # Socket closes after only 3 bytes
        mock_sock.recv.side_effect = [b"Hel", b""]

        with pytest.raises(EOFError, match="Socket closed prematurely"):
            read_exact(mock_sock, 10)

    def test_read_exact_zero_bytes(self):
        """Test reading zero bytes."""
        mock_sock = mock.Mock()

        result = read_exact(mock_sock, 0)

        assert result == b""
        mock_sock.recv.assert_not_called()


class TestIterReadChunked:
    """Tests for iter_read_chunked function."""

    def test_iter_read_chunked_single_chunk(self):
        """Test reading single chunk."""
        mock_sock = mock.Mock()
        # Chunk format: "5\r\nHello\r\n0\r\n\r\n"
        mock_sock.recv.side_effect = [
            # Chunk size line
            b"5",
            b"\r",
            b"\n",
            # Chunk data "Hello"
            b"Hello",
            # Chunk trailer
            b"\r\n",
            # Final chunk size 0
            b"0",
            b"\r",
            b"\n",
            # Final trailer
            b"\r\n",
        ]

        chunks = list(iter_read_chunked(mock_sock))

        assert chunks == [b"Hello"]

    def test_iter_read_chunked_multiple_chunks(self):
        """Test reading multiple chunks."""
        mock_sock = mock.Mock()
        # "5\r\nHello\r\n5\r\nWorld\r\n0\r\n\r\n"
        mock_sock.recv.side_effect = [
            # First chunk size
            b"5",
            b"\r",
            b"\n",
            # First chunk data
            b"Hello",
            # First chunk trailer
            b"\r\n",
            # Second chunk size
            b"5",
            b"\r",
            b"\n",
            # Second chunk data
            b"World",
            # Second chunk trailer
            b"\r\n",
            # Final chunk
            b"0",
            b"\r",
            b"\n",
            # Final trailer
            b"\r\n",
        ]

        chunks = list(iter_read_chunked(mock_sock))

        assert chunks == [b"Hello", b"World"]

    def test_iter_read_chunked_with_chunk_extension(self):
        """Test reading chunks with extensions (after semicolon)."""
        mock_sock = mock.Mock()
        # "5;name=value\r\nHello\r\n0\r\n\r\n"
        mock_sock.recv.side_effect = [
            # Chunk size with extension
            b"5",
            b";",
            b"n",
            b"a",
            b"m",
            b"e",
            b"=",
            b"v",
            b"a",
            b"l",
            b"u",
            b"e",
            b"\r",
            b"\n",
            # Chunk data
            b"Hello",
            # Chunk trailer
            b"\r\n",
            # Final chunk
            b"0",
            b"\r",
            b"\n",
            # Final trailer
            b"\r\n",
        ]

        chunks = list(iter_read_chunked(mock_sock))

        assert chunks == [b"Hello"]

    def test_iter_read_chunked_socket_closed_during_header(self):
        """Test iter_read_chunked raises EOFError if socket closes during header."""
        mock_sock = mock.Mock()
        # Socket closes while reading chunk size
        mock_sock.recv.side_effect = [b"5", b""]

        with pytest.raises(EOFError, match="Socket closed during chunk header"):
            list(iter_read_chunked(mock_sock))

    def test_iter_read_chunked_invalid_chunk_size(self):
        """Test iter_read_chunked raises ValueError for invalid chunk size."""
        mock_sock = mock.Mock()
        # Invalid hex chunk size
        mock_sock.recv.side_effect = [b"X", b"Y", b"Z", b"\r", b"\n"]

        with pytest.raises(ValueError, match="Invalid chunk size"):
            list(iter_read_chunked(mock_sock))

    def test_iter_read_chunked_empty_chunks(self):
        """Test reading only terminating zero chunk."""
        mock_sock = mock.Mock()
        # Just "0\r\n\r\n"
        mock_sock.recv.side_effect = [
            b"0",
            b"\r",
            b"\n",
            b"\r\n",
        ]

        chunks = list(iter_read_chunked(mock_sock))

        assert chunks == []

    def test_iter_read_chunked_hex_uppercase(self):
        """Test chunk size in uppercase hex."""
        mock_sock = mock.Mock()
        # "A\r\n1234567890\r\n0\r\n\r\n" (A = 10 in hex)
        mock_sock.recv.side_effect = [
            b"A",
            b"\r",
            b"\n",
            b"1234567890",  # 10 bytes
            b"\r\n",
            b"0",
            b"\r",
            b"\n",
            b"\r\n",
        ]

        chunks = list(iter_read_chunked(mock_sock))

        assert chunks == [b"1234567890"]


class TestReadChunked:
    """Tests for read_chunked function."""

    def test_read_chunked_single_chunk(self):
        """Test read_chunked with single chunk."""
        mock_sock = mock.Mock()
        mock_sock.recv.side_effect = [
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

        result = read_chunked(mock_sock)

        assert result == b"Hello"

    def test_read_chunked_multiple_chunks(self):
        """Test read_chunked combines multiple chunks."""
        mock_sock = mock.Mock()
        mock_sock.recv.side_effect = [
            # "5\r\nHello\r\n"
            b"5",
            b"\r",
            b"\n",
            b"Hello",
            b"\r\n",
            # "1\r\n \r\n"
            b"1",
            b"\r",
            b"\n",
            b" ",
            b"\r\n",
            # "5\r\nWorld\r\n"
            b"5",
            b"\r",
            b"\n",
            b"World",
            b"\r\n",
            # "0\r\n\r\n"
            b"0",
            b"\r",
            b"\n",
            b"\r\n",
        ]

        result = read_chunked(mock_sock)

        assert result == b"Hello World"

    def test_read_chunked_empty_body(self):
        """Test read_chunked with no data chunks."""
        mock_sock = mock.Mock()
        mock_sock.recv.side_effect = [
            b"0",
            b"\r",
            b"\n",
            b"\r\n",
        ]

        result = read_chunked(mock_sock)

        assert result == b""
