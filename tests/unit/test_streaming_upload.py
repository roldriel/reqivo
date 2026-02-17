"""tests/unit/test_streaming_upload.py

Unit tests for streaming uploads (chunked transfer encoding) added in v0.3.0.

Test Coverage:
    - iter_write_chunked with mock socket
    - async_iter_write_chunked with mock writer
    - file_to_iterator with BytesIO
    - build_request_headers with chunked=True
    - Request._perform_request with iterable body
    - Request._perform_request with file-like body
    - AsyncRequest._perform_request with AsyncIterator body

Testing Strategy:
    - Mock sockets and writers for I/O verification
    - Use BytesIO as file-like test objects
    - Verify chunked encoding format: {hex_size}\\r\\n{data}\\r\\n ... 0\\r\\n\\r\\n
"""

import io
from unittest import mock

import pytest

from reqivo.client.request import Request
from reqivo.client.response import Response
from reqivo.client.session import Session
from reqivo.http.body import (
    async_iter_write_chunked,
    file_to_iterator,
    iter_write_chunked,
)
from reqivo.http.headers import Headers

# ============================================================================
# TEST CLASS: iter_write_chunked (sync)
# ============================================================================


class TestIterWriteChunked:
    """Tests for iter_write_chunked function."""

    def test_single_chunk(self) -> None:
        """Test writing a single chunk."""
        sock = mock.Mock()
        chunks = iter([b"hello"])

        iter_write_chunked(sock, chunks)

        calls = sock.sendall.call_args_list
        # First call: chunk header + data + CRLF
        assert calls[0] == mock.call(b"5\r\nhello\r\n")
        # Second call: terminator
        assert calls[1] == mock.call(b"0\r\n\r\n")

    def test_multiple_chunks(self) -> None:
        """Test writing multiple chunks."""
        sock = mock.Mock()
        chunks = iter([b"hello", b"world!"])

        iter_write_chunked(sock, chunks)

        calls = sock.sendall.call_args_list
        assert calls[0] == mock.call(b"5\r\nhello\r\n")
        assert calls[1] == mock.call(b"6\r\nworld!\r\n")
        assert calls[2] == mock.call(b"0\r\n\r\n")

    def test_empty_chunks_skipped(self) -> None:
        """Test that empty chunks are skipped."""
        sock = mock.Mock()
        chunks = iter([b"data", b"", b"more"])

        iter_write_chunked(sock, chunks)

        calls = sock.sendall.call_args_list
        assert len(calls) == 3  # 2 data chunks + terminator
        assert calls[0] == mock.call(b"4\r\ndata\r\n")
        assert calls[1] == mock.call(b"4\r\nmore\r\n")
        assert calls[2] == mock.call(b"0\r\n\r\n")

    def test_empty_iterator(self) -> None:
        """Test writing from an empty iterator."""
        sock = mock.Mock()
        chunks = iter([])

        iter_write_chunked(sock, chunks)

        calls = sock.sendall.call_args_list
        assert len(calls) == 1
        assert calls[0] == mock.call(b"0\r\n\r\n")

    def test_hex_encoding_large_chunk(self) -> None:
        """Test that chunk size is properly hex-encoded for larger chunks."""
        sock = mock.Mock()
        data = b"x" * 256
        chunks = iter([data])

        iter_write_chunked(sock, chunks)

        calls = sock.sendall.call_args_list
        # 256 = 0x100
        assert calls[0] == mock.call(b"100\r\n" + data + b"\r\n")


# ============================================================================
# TEST CLASS: async_iter_write_chunked
# ============================================================================


class TestAsyncIterWriteChunked:
    """Tests for async_iter_write_chunked function."""

    @staticmethod
    def _make_writer() -> mock.Mock:
        """Create a mock writer with sync write() and async drain()."""
        writer = mock.Mock()
        writer.drain = mock.AsyncMock()
        return writer

    @pytest.mark.asyncio
    async def test_single_chunk(self) -> None:
        """Test writing a single async chunk."""
        writer = self._make_writer()

        async def gen():
            yield b"hello"

        await async_iter_write_chunked(writer, gen())

        write_calls = writer.write.call_args_list
        assert write_calls[0] == mock.call(b"5\r\nhello\r\n")
        assert write_calls[1] == mock.call(b"0\r\n\r\n")

    @pytest.mark.asyncio
    async def test_multiple_chunks(self) -> None:
        """Test writing multiple async chunks."""
        writer = self._make_writer()

        async def gen():
            yield b"abc"
            yield b"defgh"

        await async_iter_write_chunked(writer, gen())

        write_calls = writer.write.call_args_list
        assert write_calls[0] == mock.call(b"3\r\nabc\r\n")
        assert write_calls[1] == mock.call(b"5\r\ndefgh\r\n")
        assert write_calls[2] == mock.call(b"0\r\n\r\n")

    @pytest.mark.asyncio
    async def test_empty_chunks_skipped(self) -> None:
        """Test that empty async chunks are skipped."""
        writer = self._make_writer()

        async def gen():
            yield b"data"
            yield b""
            yield b"more"

        await async_iter_write_chunked(writer, gen())

        write_calls = writer.write.call_args_list
        assert len(write_calls) == 3  # 2 data + terminator

    @pytest.mark.asyncio
    async def test_empty_async_iterator(self) -> None:
        """Test writing from an empty async iterator."""
        writer = self._make_writer()

        async def gen():
            return
            yield  # type: ignore[misc]  # noqa: unreachable

        await async_iter_write_chunked(writer, gen())

        write_calls = writer.write.call_args_list
        assert len(write_calls) == 1
        assert write_calls[0] == mock.call(b"0\r\n\r\n")


# ============================================================================
# TEST CLASS: file_to_iterator
# ============================================================================


class TestFileToIterator:
    """Tests for file_to_iterator function."""

    def test_basic_file(self) -> None:
        """Test converting a BytesIO to iterator."""
        data = b"hello world"
        fileobj = io.BytesIO(data)

        chunks = list(file_to_iterator(fileobj))

        assert b"".join(chunks) == data

    def test_custom_chunk_size(self) -> None:
        """Test file_to_iterator with custom chunk size."""
        data = b"abcdefghij"  # 10 bytes
        fileobj = io.BytesIO(data)

        chunks = list(file_to_iterator(fileobj, chunk_size=3))

        assert chunks == [b"abc", b"def", b"ghi", b"j"]

    def test_empty_file(self) -> None:
        """Test file_to_iterator with empty file."""
        fileobj = io.BytesIO(b"")

        chunks = list(file_to_iterator(fileobj))

        assert chunks == []

    def test_exact_chunk_size(self) -> None:
        """Test file_to_iterator when file is exactly one chunk."""
        data = b"exact"
        fileobj = io.BytesIO(data)

        chunks = list(file_to_iterator(fileobj, chunk_size=5))

        assert chunks == [b"exact"]


# ============================================================================
# TEST CLASS: build_request_headers
# ============================================================================


class TestBuildRequestHeaders:
    """Tests for Request.build_request_headers."""

    def test_basic_headers(self) -> None:
        """Test building request headers without chunked."""
        result = Request.build_request_headers("POST", "/upload", "example.com", {})
        assert b"POST /upload HTTP/1.1\r\n" in result
        assert b"Host: example.com\r\n" in result
        assert b"Transfer-Encoding" not in result
        assert result.endswith(b"\r\n\r\n")

    def test_chunked_header(self) -> None:
        """Test that chunked=True adds Transfer-Encoding header."""
        result = Request.build_request_headers(
            "POST", "/upload", "example.com", {}, chunked=True
        )
        assert b"Transfer-Encoding: chunked\r\n" in result

    def test_custom_headers_preserved(self) -> None:
        """Test that custom headers are included."""
        result = Request.build_request_headers(
            "PUT",
            "/data",
            "example.com",
            {"Content-Type": "text/plain"},
            chunked=True,
        )
        assert b"Content-Type: text/plain\r\n" in result
        assert b"Transfer-Encoding: chunked\r\n" in result

    def test_header_injection_rejected(self) -> None:
        """Test that header injection is rejected."""
        with pytest.raises(ValueError, match="Invalid character"):
            Request.build_request_headers(
                "POST", "/", "example.com", {"Bad\r\nHeader": "value"}
            )


# ============================================================================
# TEST CLASS: Streaming in _perform_request (sync)
# ============================================================================


class TestStreamingPerformRequest:
    """Tests for streaming body detection in Request._perform_request."""

    @mock.patch("reqivo.client.request.Connection")
    def test_iterator_body_uses_chunked(self, MockConnection: mock.Mock) -> None:
        """Test that iterator body triggers chunked encoding."""
        mock_conn = mock.Mock()
        mock_conn.host = "example.com"
        mock_conn.port = 443
        mock_sock = mock.Mock()
        mock_conn.sock = mock_sock

        # Mock socket recv to return a valid HTTP response
        response_bytes = b"HTTP/1.1 200 OK\r\n" b"Content-Length: 2\r\n" b"\r\n" b"OK"
        mock_sock.recv.side_effect = [response_bytes, b""]

        MockConnection.return_value = mock_conn

        chunks = iter([b"part1", b"part2"])

        from reqivo.utils.timing import Timeout

        Request._perform_request(
            "POST",
            "https://example.com/upload",
            {},
            chunks,
            Timeout.from_float(5),
            mock_conn,
        )

        # Verify sendall was called - first with headers, then chunked data
        sendall_calls = mock_sock.sendall.call_args_list
        # First call is the headers (with Transfer-Encoding: chunked)
        header_bytes = sendall_calls[0][0][0]
        assert b"Transfer-Encoding: chunked" in header_bytes
        # Subsequent calls are the chunked data
        assert any(b"part1" in call[0][0] for call in sendall_calls)

    @mock.patch("reqivo.client.request.Connection")
    def test_file_body_uses_chunked(self, MockConnection: mock.Mock) -> None:
        """Test that file-like body triggers chunked encoding."""
        mock_conn = mock.Mock()
        mock_conn.host = "example.com"
        mock_conn.port = 443
        mock_sock = mock.Mock()
        mock_conn.sock = mock_sock

        response_bytes = b"HTTP/1.1 200 OK\r\n" b"Content-Length: 2\r\n" b"\r\n" b"OK"
        mock_sock.recv.side_effect = [response_bytes, b""]

        MockConnection.return_value = mock_conn

        fileobj = io.BytesIO(b"file content here")

        from reqivo.utils.timing import Timeout

        Request._perform_request(
            "PUT",
            "https://example.com/upload",
            {},
            fileobj,
            Timeout.from_float(5),
            mock_conn,
        )

        sendall_calls = mock_sock.sendall.call_args_list
        header_bytes = sendall_calls[0][0][0]
        assert b"Transfer-Encoding: chunked" in header_bytes

    @mock.patch("reqivo.client.request.Connection")
    def test_string_body_uses_content_length(self, MockConnection: mock.Mock) -> None:
        """Test that string body uses Content-Length (not chunked)."""
        mock_conn = mock.Mock()
        mock_conn.host = "example.com"
        mock_conn.port = 443
        mock_sock = mock.Mock()
        mock_conn.sock = mock_sock

        response_bytes = b"HTTP/1.1 200 OK\r\n" b"Content-Length: 2\r\n" b"\r\n" b"OK"
        mock_sock.recv.side_effect = [response_bytes, b""]

        MockConnection.return_value = mock_conn

        from reqivo.utils.timing import Timeout

        Request._perform_request(
            "POST",
            "https://example.com/api",
            {},
            "simple body",
            Timeout.from_float(5),
            mock_conn,
        )

        sendall_calls = mock_sock.sendall.call_args_list
        request_bytes = sendall_calls[0][0][0]
        assert b"Content-Length:" in request_bytes
        assert b"Transfer-Encoding: chunked" not in request_bytes


# ============================================================================
# TEST CLASS: Session with streaming body
# ============================================================================


class TestSessionStreamingUpload:
    """Tests for Session methods with streaming body."""

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_session_post_with_iterator_body(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
    ) -> None:
        """Test that Session.post passes iterator body through to Request.send."""
        session = Session()

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        mock_resp = mock.Mock(spec=Response)
        mock_resp.headers = Headers()
        MockRequest.send.return_value = mock_resp
        MockRequest.set_session_instance = mock.Mock()

        chunks = iter([b"chunk1", b"chunk2"])
        session.post("https://example.com/upload", body=chunks)

        call_kwargs = MockRequest.send.call_args[1]
        assert call_kwargs["body"] is chunks

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_session_put_with_file_body(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
    ) -> None:
        """Test that Session.put passes file-like body through to Request.send."""
        session = Session()

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        mock_resp = mock.Mock(spec=Response)
        mock_resp.headers = Headers()
        MockRequest.send.return_value = mock_resp
        MockRequest.set_session_instance = mock.Mock()

        fileobj = io.BytesIO(b"file data")
        session.put("https://example.com/upload", body=fileobj)

        call_kwargs = MockRequest.send.call_args[1]
        assert call_kwargs["body"] is fileobj
