"""src/reqivo/http/body.py

HTTP body management (chunked, fixed-length, streaming) for Reqivo.
"""

import asyncio
import socket
from typing import IO, AsyncIterator, Generator, Iterator

__all__ = [
    "read_exact",
    "iter_read_chunked",
    "read_chunked",
    "iter_write_chunked",
    "async_iter_write_chunked",
    "file_to_iterator",
]


def read_exact(sock: socket.socket, n: int) -> bytes:
    """Read exactly n bytes from the socket."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise EOFError("Socket closed prematurely")

        data += chunk
    return data


def iter_read_chunked(sock: socket.socket) -> Generator[bytes, None, None]:
    """Iterate over chunked transfer-encoded response."""
    while True:
        line = b""
        while not line.endswith(b"\r\n"):
            chunk = sock.recv(1)
            if not chunk:
                raise EOFError("Socket closed during chunk header")
            line += chunk

        try:
            size_hex = line.split(b";")[0].strip()
            size = int(size_hex, 16)

        except ValueError as exc:
            raise ValueError(f"Invalid chunk size: {line!r}") from exc

        if size == 0:
            # End of chunks
            # Consume trailing CRLF
            read_exact(sock, 2)
            break

        data = read_exact(sock, size)
        yield data

        # Consume chunk trailer CRLF
        read_exact(sock, 2)


def read_chunked(sock: socket.socket) -> bytes:
    """Read full chunked body into memory."""
    return b"".join(iter_read_chunked(sock))


def iter_write_chunked(sock: socket.socket, chunks: Iterator[bytes]) -> None:
    """
    Write an iterable of bytes chunks using HTTP chunked transfer encoding.

    Each chunk is sent as ``{hex_size}\\r\\n{data}\\r\\n``.
    A final ``0\\r\\n\\r\\n`` terminator is sent after all chunks.

    Args:
        sock: Socket to write to.
        chunks: Iterator yielding bytes chunks.
    """
    for chunk in chunks:
        if not chunk:
            continue
        size_line = f"{len(chunk):x}\r\n".encode("ascii")
        sock.sendall(size_line + chunk + b"\r\n")
    # Terminating chunk
    sock.sendall(b"0\r\n\r\n")


async def async_iter_write_chunked(
    writer: asyncio.StreamWriter, chunks: AsyncIterator[bytes]
) -> None:
    """
    Write an async iterable of bytes chunks using HTTP chunked transfer encoding.

    Each chunk is sent as ``{hex_size}\\r\\n{data}\\r\\n``.
    A final ``0\\r\\n\\r\\n`` terminator is sent after all chunks.

    Args:
        writer: asyncio StreamWriter to write to.
        chunks: AsyncIterator yielding bytes chunks.
    """
    async for chunk in chunks:
        if not chunk:
            continue
        size_line = f"{len(chunk):x}\r\n".encode("ascii")
        writer.write(size_line + chunk + b"\r\n")
        await writer.drain()
    # Terminating chunk
    writer.write(b"0\r\n\r\n")
    await writer.drain()


def file_to_iterator(fileobj: IO[bytes], chunk_size: int = 8192) -> Iterator[bytes]:
    """
    Convert a file-like object into a bytes iterator.

    Args:
        fileobj: File-like object opened in binary mode.
        chunk_size: Number of bytes per chunk.

    Yields:
        Chunks of bytes read from the file.
    """
    while True:
        chunk = fileobj.read(chunk_size)
        if not chunk:
            break
        yield chunk
