"""src/reqivo/transport/connection_pool.py

Connection pooling module.

This module provides connection pool management for efficient reuse of
TCP/TLS connections across multiple HTTP requests.
"""

import asyncio
import threading
import time
from collections import deque
from typing import Deque, Dict, List, Tuple, Union

from reqivo.transport.connection import AsyncConnection, Connection
from reqivo.utils.timing import Timeout

__all__ = ["ConnectionPool", "AsyncConnectionPool"]


class ConnectionPool:
    """
    Pool of reusable open connections.

    Maintains a cache of open connections keyed by (host, port, ssl, proxy)
    to enable connection reuse across multiple requests.

    This implementation is thread-safe and supports multiple connections
    per host.
    """

    __slots__ = ("_pool", "_lock", "_semaphores", "max_size", "max_idle_time")

    def __init__(self, max_size: int = 10, max_idle_time: float = 30.0) -> None:
        """
        Initialize connection pool.

        Args:
            max_size: Maximum number of connections to keep per host.
            max_idle_time: Max time (seconds) a connection can be idle.
        """
        # Key -> List of (connection, timestamp) tuples (LIFO stack for reuse)
        self._pool: Dict[Tuple[str, int, bool], Deque[Tuple[Connection, float]]] = {}
        self._semaphores: Dict[Tuple[str, int, bool], threading.Semaphore] = {}
        self._lock = threading.Lock()
        self.max_size = max_size
        self.max_idle_time = max_idle_time

    def get_connection(
        self,
        host: str,
        port: int,
        use_ssl: bool,
        timeout: Union[float, Timeout, None] = None,
    ) -> Connection:
        """
        Get an existing connection or create a new one.
        Blocks if max_size is reached until a connection is available.
        """
        # pylint: disable=too-many-branches
        key = (host, port, use_ssl)

        with self._lock:
            if key not in self._semaphores:
                self._semaphores[key] = threading.Semaphore(self.max_size)

        # Acquire semaphore (limits total active + idle connections)
        # Using connect timeout or default blocking?
        # Ideally we block.
        self._semaphores[key].acquire()

        try:
            with self._lock:
                # Cleanup expired connections first
                self._cleanup_expired(key)

                connections = self._pool.get(key)
                if connections:
                    # Iterate to find a valid connection
                    while connections:
                        conn, last_used = connections.pop()  # Pop from right (LIFO)

                        # Check if connection is still fresh and usable
                        if (
                            time.time() - last_used < self.max_idle_time
                            and conn.is_usable()
                        ):
                            return conn

                        # Close expired or dead connection
                        conn.close()

            # Create new connection
            conn = Connection(host, port, use_ssl, timeout=timeout)
            conn.open()
            return conn

        except Exception:
            # If anything fails (creation), release key
            self._semaphores[key].release()
            raise

    def put_connection(self, conn: Connection) -> None:
        """
        Return a connection to the pool with timestamp.
        """
        key = (conn.host, conn.port, conn.use_ssl)

        # If connection is bad or closed, we effectively discard it
        if not conn.sock or not conn.is_usable():
            conn.close()
            # Release the slot
            if key in self._semaphores:
                self._semaphores[key].release()
            return

        with self._lock:
            if key not in self._pool:
                self._pool[key] = deque()

            queue = self._pool[key]

            # If full, drop oldest
            if len(queue) >= self.max_size:
                oldest_conn, _ = queue.popleft()
                oldest_conn.close()

            # Store connection with current timestamp
            queue.append((conn, time.time()))

            if key in self._semaphores:
                self._semaphores[key].release()

    def _cleanup_expired(self, key: Tuple[str, int, bool]) -> None:
        """
        Remove expired connections from the pool for a specific key.
        Must be called with _lock held.
        """
        if key not in self._pool:
            return

        connections = self._pool[key]
        current_time = time.time()

        # Filter out expired connections
        valid_connections: Deque[Tuple[Connection, float]] = deque()
        for conn, last_used in connections:
            if current_time - last_used < self.max_idle_time and conn.is_usable():
                valid_connections.append((conn, last_used))
            else:
                conn.close()

        self._pool[key] = valid_connections

    def discard_connection(self, conn: Connection) -> None:
        """Discard a connection and release its slot."""
        conn.close()
        key = (conn.host, conn.port, conn.use_ssl)
        if key in self._semaphores:
            self._semaphores[key].release()

    def release_connection(self, host: str, port: int, use_ssl: bool) -> None:
        """
        Deprecated: Manual release by key.
        """
        key = (host, port, use_ssl)
        with self._lock:
            if key in self._pool:
                connections = self._pool.pop(key)
                for conn, _ in connections:
                    conn.close()
                    # Also release semaphores?
                    # The number of semaphores to release is len(connections).
                    if key in self._semaphores:
                        for _ in range(len(connections)):
                            self._semaphores[key].release()

    def close_all(self) -> None:
        """
        Close all connections in the pool.
        """
        with self._lock:
            for key, connections in self._pool.items():
                count = len(connections)
                for conn, _ in connections:
                    conn.close()

                if key in self._semaphores:
                    for _ in range(count):
                        self._semaphores[key].release()

            self._pool.clear()


class AsyncConnectionPool:
    """
    Pool of reusable asynchronous connections.
    """

    __slots__ = ("_pool", "_semaphores", "max_size", "max_idle_time")

    def __init__(self, max_size: int = 10, max_idle_time: float = 30.0):
        # Key -> List of (connection, timestamp) tuples
        self._pool: Dict[Tuple[str, int, bool], List[Tuple[AsyncConnection, float]]] = (
            {}
        )
        self._semaphores: Dict[Tuple[str, int, bool], asyncio.Semaphore] = {}
        self.max_size = max_size
        self.max_idle_time = max_idle_time

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

        if key not in self._semaphores:
            self._semaphores[key] = asyncio.Semaphore(self.max_size)

        await self._semaphores[key].acquire()

        try:
            # Cleanup expired connections first
            await self._cleanup_expired(key)

            if key in self._pool:
                connections = self._pool[key]
                while connections:
                    conn, last_used = connections.pop()

                    # Check if connection is still fresh and usable
                    if (
                        time.time() - last_used < self.max_idle_time
                        and conn.is_usable()
                    ):
                        return conn

                    # Close expired or dead connection
                    await conn.close()

            # Create new connection
            conn = AsyncConnection(host, port, use_ssl, timeout=timeout)
            await conn.open()
            return conn

        except Exception:
            self._semaphores[key].release()
            raise

    async def put_connection(self, conn: AsyncConnection) -> None:
        """
        Returns a connection to the pool for reuse with timestamp.
        """
        key = (conn.host, conn.port, conn.use_ssl)

        if not conn.is_usable():
            await conn.close()
            if key in self._semaphores:
                self._semaphores[key].release()
            return

        if key not in self._pool:
            self._pool[key] = []

        connections = self._pool[key]
        if len(connections) >= self.max_size:
            oldest_conn, _ = connections.pop(0)
            await oldest_conn.close()

        # Store connection with current timestamp
        connections.append((conn, time.time()))

        if key in self._semaphores:
            self._semaphores[key].release()

    async def _cleanup_expired(self, key: Tuple[str, int, bool]) -> None:
        """
        Remove expired connections from the pool for a specific key.
        """
        if key not in self._pool:
            return

        connections = self._pool[key]
        current_time = time.time()

        # Filter out expired connections
        valid_connections: List[Tuple[AsyncConnection, float]] = []
        for conn, last_used in connections:
            if current_time - last_used < self.max_idle_time and conn.is_usable():
                valid_connections.append((conn, last_used))
            else:
                await conn.close()

        self._pool[key] = valid_connections

    async def discard_connection(self, conn: AsyncConnection) -> None:
        """Discard async connection and release slot."""
        await conn.close()
        key = (conn.host, conn.port, conn.use_ssl)
        if key in self._semaphores:
            self._semaphores[key].release()

    async def release_connection(self, host: str, port: int, use_ssl: bool) -> None:
        """
        Closes and removes all connections for the key.
        """
        key = (host, port, use_ssl)
        if key in self._pool:
            connections = self._pool.pop(key)
            for conn, _ in connections:
                await conn.close()

            if key in self._semaphores:
                for _ in range(len(connections)):
                    self._semaphores[key].release()

    async def close_all(self) -> None:
        """
        Closes all connections in the pool.
        """
        for key, connections in self._pool.items():
            count = len(connections)
            for conn, _ in connections:
                await conn.close()

            if key in self._semaphores:
                for _ in range(count):
                    self._semaphores[key].release()
        self._pool.clear()
