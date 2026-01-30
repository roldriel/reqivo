"""transport/connection_pool.py

Connection pooling module.

This module provides connection pool management for efficient reuse of
TCP/TLS connections across multiple HTTP requests.
"""

import threading
from collections import deque
from typing import Deque, Dict, List, Tuple, Union

from reqivo.transport.connection import AsyncConnection, Connection
from reqivo.utils.timing import Timeout


class ConnectionPool:
    """
    Pool of reusable open connections.

    Maintains a cache of open connections keyed by (host, port, ssl, proxy)
    to enable connection reuse across multiple requests.

    This implementation is thread-safe and supports multiple connections
    per host.
    """

    def __init__(self, max_size: int = 10) -> None:
        """
        Initialize connection pool.

        Args:
            max_size: Maximum number of connections to keep per host.
        """
        # Key -> List of connections (LIFO stack for reuse)
        self._pool: Dict[Tuple[str, int, bool], Deque[Connection]] = {}
        self._lock = threading.Lock()
        self.max_size = max_size

    def get_connection(
        self,
        host: str,
        port: int,
        use_ssl: bool,
        timeout: Union[float, Timeout, None] = None,
    ) -> Connection:
        """
        Get an existing connection or create a new one.

        Args:
            host: Target hostname.
            port: Target port.
            use_ssl: Whether to use TLS.
            timeout: Connection timeout.

        Returns:
            Open connection ready for use.
        """
        key = (host, port, use_ssl)

        with self._lock:
            connections = self._pool.get(key)
            if connections:
                # Iterate to find a valid connection
                while connections:
                    conn = connections.pop()  # Pop from right (LIFO)
                    if conn.is_usable():
                        return conn
                    # Close silently if dead
                    conn.close()

        # Create new connection
        conn = Connection(host, port, use_ssl, timeout=timeout)
        conn.open()
        return conn

    def put_connection(self, conn: Connection) -> None:
        """
        Return a connection to the pool.

        Args:
            conn: Connection object to return.
        """
        if not conn.sock:
            return

        if not conn.is_usable():
            conn.close()
            return

        key = (conn.host, conn.port, conn.use_ssl)

        with self._lock:
            if key not in self._pool:
                self._pool[key] = deque()

            queue = self._pool[key]

            # If full, drop oldest
            if len(queue) >= self.max_size:
                oldest = queue.popleft()
                oldest.close()

            queue.append(conn)

    def release_connection(self, host: str, port: int, use_ssl: bool) -> None:
        """
        Deprecated: Manual release by key.
        """
        key = (host, port, use_ssl)
        with self._lock:
            if key in self._pool:
                connections = self._pool.pop(key)
                for conn in connections:
                    conn.close()

    def close_all(self) -> None:
        """
        Close all connections in the pool.
        """
        with self._lock:
            for connections in self._pool.values():
                for conn in connections:
                    conn.close()
            self._pool.clear()


class AsyncConnectionPool:
    """
    Pool of reusable asynchronous connections.
    """

    def __init__(self, max_size: int = 10):
        # Key -> List of connections
        self._pool: Dict[Tuple[str, int, bool], List[AsyncConnection]] = {}
        self.max_size = max_size

    async def get_connection(
        self,
        host: str,
        port: int,
        use_ssl: bool,
        timeout: Union[float, Timeout, None] = None,
    ) -> AsyncConnection:
        """
        Returns an existing connection or creates a new one.
        """
        key = (host, port, use_ssl)

        if key in self._pool:
            connections = self._pool[key]
            while connections:
                conn = connections.pop()
                if conn.is_usable():
                    return conn
                await conn.close()

        # Create new connection
        conn = AsyncConnection(host, port, use_ssl, timeout=timeout)
        await conn.open()
        return conn

    async def put_connection(self, conn: AsyncConnection) -> None:
        """
        Returns a connection to the pool for reuse.
        """
        if not conn.is_usable():
            await conn.close()
            return

        key = (conn.host, conn.port, conn.use_ssl)
        if key not in self._pool:
            self._pool[key] = []

        connections = self._pool[key]
        if len(connections) >= self.max_size:
            oldest = connections.pop(0)
            await oldest.close()

        connections.append(conn)

    async def release_connection(self, host: str, port: int, use_ssl: bool) -> None:
        """
        Closes and removes all connections for the key.
        """
        key = (host, port, use_ssl)
        if key in self._pool:
            connections = self._pool.pop(key)
            for conn in connections:
                await conn.close()

    async def close_all(self) -> None:
        """
        Closes all connections in the pool.
        """
        for connections in self._pool.values():
            for conn in connections:
                await conn.close()
        self._pool.clear()
