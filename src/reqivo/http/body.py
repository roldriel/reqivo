"""src/reqivo/http/body.py

HTTP body management (chunked, fixed-length, streaming) for Reqivo.
"""

import socket
from typing import Generator


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
