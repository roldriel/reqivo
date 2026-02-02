"""src/reqivo/transport/connection.py

TCP and TLS connection management module.

This module provides low-level connection handling with support for
TLS encryption, proxy connections, and proper error handling for
network operations.
"""

import asyncio
import contextlib
import select
import socket
import ssl
from typing import Any, Optional, Union

# pylint: disable=unused-import
# pylint: disable=redefined-builtin
from reqivo.exceptions import (
    ConnectTimeout,
    NetworkError,
    ReadTimeout,
    TimeoutError,
    TlsError,
)
from reqivo.utils.timing import Timeout


class Connection:
    """
    Manages TCP and TLS connection creation and lifecycle.

    Attributes:
        host: The target hostname or IP address.
        port: The target port number.
        use_ssl: Whether to use TLS encryption.
        timeout: Connection timeout configuration.
        sock: The underlying socket object.
    """

    __slots__ = ("host", "port", "use_ssl", "timeout", "sock")

    def __init__(
        self,
        host: str,
        port: int,
        use_ssl: bool = False,
        timeout: Union[float, Timeout, None] = None,
    ) -> None:
        """
        Initialize connection parameters.
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl

        if timeout is None:
            self.timeout = None

        elif isinstance(timeout, Timeout):
            self.timeout = timeout

        else:
            self.timeout = Timeout.from_float(timeout)

        self.sock: Optional[socket.socket] = None

    def open(self) -> socket.socket:
        """
        Open TCP connection with optional TLS encryption.
        """
        if self.timeout:
            connect_to = (
                self.timeout.connect
                if self.timeout.connect is not None
                else self.timeout.total
            )

        else:
            connect_to = None

        try:
            raw_sock = socket.create_connection(
                (self.host, self.port), timeout=connect_to
            )
            if self.use_ssl:
                context = ssl.create_default_context()
                try:
                    self.sock = context.wrap_socket(raw_sock, server_hostname=self.host)

                except socket.timeout as e:
                    raise ConnectTimeout(f"Timeout during TLS handshake: {e}") from e

            else:
                self.sock = raw_sock

            # After connection is established, switch timeout to 'read_timeout'
            if self.timeout:
                read_to = (
                    self.timeout.read
                    if self.timeout.read is not None
                    else self.timeout.total
                )
                self.sock.settimeout(read_to)
            else:
                self.sock.settimeout(None)

            return self.sock

        except socket.timeout as e:
            raise ConnectTimeout(
                f"Timeout connecting to {self.host}:{self.port}"
            ) from e

        except ssl.SSLError as e:
            raise TlsError(f"TLS Verification Error: {e}") from e

        except socket.error as e:
            if isinstance(e, socket.timeout):
                raise ConnectTimeout(
                    f"Timeout connecting to {self.host}:{self.port}"
                ) from e
            raise NetworkError(
                f"Connection error to {self.host}:{self.port} - {e}"
            ) from e

    def close(self) -> None:
        """
        Close the connection if it is open.
        """
        if self.sock:
            try:
                self.sock.close()
            except (OSError, socket.error):
                pass
            self.sock = None

    def __enter__(self) -> "Connection":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        self.close()

    def is_usable(self) -> bool:
        """
        Check if the connection appears usable (not closed by peer).
        """
        if not self.sock:
            return False

        try:
            readable, _, _ = select.select([self.sock], [], [], 0)
            if readable:
                try:
                    chunk = self.sock.recv(1, socket.MSG_PEEK)
                    if not chunk:
                        # Connection closed by peer
                        return False
                    # If we can peek data, connection has pending data
                    # This should not happen in pooled connections
                    # Consider this unusable to avoid reading stale data
                    return False

                except (socket.error, OSError):
                    return False

            return True

        except (socket.error, OSError):
            return False


class AsyncConnection:
    """
    Manages asynchronous TCP and TLS connection creation and lifecycle.
    """

    __slots__ = ("host", "port", "use_ssl", "timeout", "reader", "writer")

    def __init__(
        self,
        host: str,
        port: int,
        use_ssl: bool = False,
        timeout: Union[float, Timeout, None] = None,
    ) -> None:
        self.host = host
        self.port = port
        self.use_ssl = use_ssl

        if timeout is None:
            self.timeout = None

        elif isinstance(timeout, Timeout):
            self.timeout = timeout

        else:
            self.timeout = Timeout.from_float(timeout)

        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def open(self) -> None:
        """Async open."""
        ssl_context = ssl.create_default_context() if self.use_ssl else None

        if self.timeout:
            connect_to = (
                self.timeout.connect
                if self.timeout.connect is not None
                else self.timeout.total
            )

        else:
            connect_to = None

        try:
            coro = asyncio.open_connection(self.host, self.port, ssl=ssl_context)
            if connect_to:
                self.reader, self.writer = await asyncio.wait_for(
                    coro, timeout=connect_to
                )

            else:
                self.reader, self.writer = await coro

        except asyncio.TimeoutError as e:
            raise ConnectTimeout(
                f"Connection to {self.host}:{self.port} timed out"
            ) from e

        except ssl.SSLError as e:
            raise TlsError(f"TLS connection failed: {e}") from e

        except Exception as e:  # pylint: disable=broad-exception-caught
            raise NetworkError(
                f"Failed to connect to {self.host}:{self.port}: {e}"
            ) from e

    def is_usable(self) -> bool:
        """Check if connection is usable."""
        if not self.writer:
            return False

        return not self.writer.is_closing()

    async def close(self) -> None:
        """Async close."""
        if self.writer:
            self.writer.close()
            with contextlib.suppress(Exception):
                await self.writer.wait_closed()

            self.reader = None
            self.writer = None
