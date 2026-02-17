"""src/reqivo/client/facade.py

Unified facade for Reqivo HTTP client and WebSocket functionality.

Provides ``Reqivo`` (sync) and ``AsyncReqivo`` (async) as single entry
points that wrap Session/AsyncSession with a fluent interface.
"""

from typing import IO, Any, Callable, Dict, Iterator, List, Optional, Union

from reqivo.client.response import Response
from reqivo.client.session import AsyncSession, Session
from reqivo.client.websocket import MAX_FRAME_SIZE, AsyncWebSocket, WebSocket

__all__ = ["Reqivo", "AsyncReqivo"]

# pylint: disable=too-many-arguments


class Reqivo:
    """
    Unified sync HTTP client facade.

    Wraps :class:`Session` to provide a simplified, fluent API for HTTP
    requests, authentication, hooks, and WebSocket connections.

    Attributes:
        _session: Internal session instance.
    """

    __slots__ = ("_session",)

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = 5,
        headers: Optional[Dict[str, str]] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        Initialize a Reqivo facade.

        Args:
            base_url: Base URL prefix for relative URLs.
            timeout: Default timeout in seconds for all requests.
            headers: Default headers for all requests.
            limits: Default resource limits.
        """
        self._session = Session(
            base_url=base_url,
            default_timeout=timeout,
            limits=limits,
        )
        if headers:
            self._session.headers.update(headers)

    # -- HTTP Methods --------------------------------------------------------

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send a GET request."""
        return self._session.get(url, headers=headers, timeout=timeout, limits=limits)

    def post(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send a POST request."""
        return self._session.post(
            url, headers=headers, body=body, timeout=timeout, limits=limits
        )

    def put(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send a PUT request."""
        return self._session.put(
            url, headers=headers, body=body, timeout=timeout, limits=limits
        )

    def delete(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send a DELETE request."""
        return self._session.delete(
            url, headers=headers, body=body, timeout=timeout, limits=limits
        )

    def patch(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send a PATCH request."""
        return self._session.patch(
            url, headers=headers, body=body, timeout=timeout, limits=limits
        )

    def head(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send a HEAD request."""
        return self._session.head(url, headers=headers, timeout=timeout, limits=limits)

    def options(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an OPTIONS request."""
        return self._session.options(
            url, headers=headers, timeout=timeout, limits=limits
        )

    # -- Auth (fluent) -------------------------------------------------------

    def basic_auth(self, username: str, password: str) -> "Reqivo":
        """
        Set Basic Auth credentials.

        Args:
            username: Username for authentication.
            password: Password for authentication.

        Returns:
            Self for chaining.
        """
        self._session.set_basic_auth(username, password)
        return self

    def bearer_token(self, token: str) -> "Reqivo":
        """
        Set Bearer token.

        Args:
            token: Bearer token for authentication.

        Returns:
            Self for chaining.
        """
        self._session.set_bearer_token(token)
        return self

    # -- Hooks (fluent) ------------------------------------------------------

    def on_request(self, hook: Callable[..., Any]) -> "Reqivo":
        """
        Register a pre-request hook.

        The hook receives ``(method, url, headers)`` and must return
        ``(method, url, headers)``.

        Args:
            hook: Callable that transforms request parameters.

        Returns:
            Self for chaining.
        """
        self._session.add_pre_request_hook(hook)
        return self

    def on_response(self, hook: Callable[..., Any]) -> "Reqivo":
        """
        Register a post-response hook.

        The hook receives a :class:`Response` and must return a
        :class:`Response`.

        Args:
            hook: Callable that transforms the response.

        Returns:
            Self for chaining.
        """
        self._session.add_post_response_hook(hook)
        return self

    # -- WebSocket -----------------------------------------------------------

    def websocket(
        self,
        url: str,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        subprotocols: Optional[List[str]] = None,
        max_frame_size: int = MAX_FRAME_SIZE,
        auto_reconnect: bool = False,
        max_reconnect_attempts: int = 3,
        reconnect_delay: float = 1.0,
    ) -> WebSocket:
        """
        Create a WebSocket instance with session headers merged.

        Args:
            url: WebSocket URL (ws:// or wss://).
            timeout: Connection timeout.
            headers: Additional headers (merged with session headers).
            subprotocols: Requested subprotocols.
            max_frame_size: Maximum frame size in bytes.
            auto_reconnect: Whether to auto-reconnect on disconnect.
            max_reconnect_attempts: Maximum reconnection attempts.
            reconnect_delay: Delay between reconnection attempts.

        Returns:
            WebSocket instance (not yet connected).
        """
        merged_headers = {**self._session.headers, **(headers or {})}
        return WebSocket(
            url,
            timeout=timeout,
            headers=merged_headers,
            subprotocols=subprotocols,
            max_frame_size=max_frame_size,
            auto_reconnect=auto_reconnect,
            max_reconnect_attempts=max_reconnect_attempts,
            reconnect_delay=reconnect_delay,
        )

    # -- Lifecycle -----------------------------------------------------------

    def close(self) -> None:
        """Close all connections in the underlying session pool."""
        self._session.close()

    def __enter__(self) -> "Reqivo":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        self.close()


class AsyncReqivo:
    """
    Unified async HTTP client facade.

    Wraps :class:`AsyncSession` to provide a simplified, fluent API for
    async HTTP requests, authentication, hooks, and WebSocket connections.

    Attributes:
        _session: Internal async session instance.
    """

    __slots__ = ("_session",)

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: Optional[float] = 5,
        headers: Optional[Dict[str, str]] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        Initialize an async Reqivo facade.

        Args:
            base_url: Base URL prefix for relative URLs.
            timeout: Default timeout in seconds for all requests.
            headers: Default headers for all requests.
            limits: Default resource limits.
        """
        self._session = AsyncSession(
            base_url=base_url,
            default_timeout=timeout,
            limits=limits,
        )
        if headers:
            self._session.headers.update(headers)

    # -- HTTP Methods --------------------------------------------------------

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async GET request."""
        return await self._session.get(
            url, headers=headers, timeout=timeout, limits=limits
        )

    async def post(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async POST request."""
        return await self._session.post(
            url, headers=headers, body=body, timeout=timeout, limits=limits
        )

    async def put(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async PUT request."""
        return await self._session.put(
            url, headers=headers, body=body, timeout=timeout, limits=limits
        )

    async def delete(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async DELETE request."""
        return await self._session.delete(
            url, headers=headers, body=body, timeout=timeout, limits=limits
        )

    async def patch(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async PATCH request."""
        return await self._session.patch(
            url, headers=headers, body=body, timeout=timeout, limits=limits
        )

    async def head(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async HEAD request."""
        return await self._session.head(
            url, headers=headers, timeout=timeout, limits=limits
        )

    async def options(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async OPTIONS request."""
        return await self._session.options(
            url, headers=headers, timeout=timeout, limits=limits
        )

    # -- Auth (fluent) -------------------------------------------------------

    def basic_auth(self, username: str, password: str) -> "AsyncReqivo":
        """
        Set Basic Auth credentials.

        Args:
            username: Username for authentication.
            password: Password for authentication.

        Returns:
            Self for chaining.
        """
        self._session.set_basic_auth(username, password)
        return self

    def bearer_token(self, token: str) -> "AsyncReqivo":
        """
        Set Bearer token.

        Args:
            token: Bearer token for authentication.

        Returns:
            Self for chaining.
        """
        self._session.set_bearer_token(token)
        return self

    # -- Hooks (fluent) ------------------------------------------------------

    def on_request(self, hook: Callable[..., Any]) -> "AsyncReqivo":
        """
        Register a pre-request hook.

        The hook receives ``(method, url, headers)`` and may be sync or async.

        Args:
            hook: Callable that transforms request parameters.

        Returns:
            Self for chaining.
        """
        self._session.add_pre_request_hook(hook)
        return self

    def on_response(self, hook: Callable[..., Any]) -> "AsyncReqivo":
        """
        Register a post-response hook.

        The hook receives a :class:`Response` and may be sync or async.

        Args:
            hook: Callable that transforms the response.

        Returns:
            Self for chaining.
        """
        self._session.add_post_response_hook(hook)
        return self

    # -- WebSocket -----------------------------------------------------------

    def websocket(
        self,
        url: str,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        subprotocols: Optional[List[str]] = None,
        max_frame_size: int = MAX_FRAME_SIZE,
        auto_reconnect: bool = False,
        max_reconnect_attempts: int = 3,
        reconnect_delay: float = 1.0,
    ) -> AsyncWebSocket:
        """
        Create an async WebSocket instance with session headers merged.

        Args:
            url: WebSocket URL (ws:// or wss://).
            timeout: Connection timeout.
            headers: Additional headers (merged with session headers).
            subprotocols: Requested subprotocols.
            max_frame_size: Maximum frame size in bytes.
            auto_reconnect: Whether to auto-reconnect on disconnect.
            max_reconnect_attempts: Maximum reconnection attempts.
            reconnect_delay: Delay between reconnection attempts.

        Returns:
            AsyncWebSocket instance (not yet connected).
        """
        merged_headers = {**self._session.headers, **(headers or {})}
        return AsyncWebSocket(
            url,
            timeout=timeout,
            headers=merged_headers,
            subprotocols=subprotocols,
            max_frame_size=max_frame_size,
            auto_reconnect=auto_reconnect,
            max_reconnect_attempts=max_reconnect_attempts,
            reconnect_delay=reconnect_delay,
        )

    # -- Lifecycle -----------------------------------------------------------

    async def close(self) -> None:
        """Close all connections in the underlying async session pool."""
        await self._session.close()

    async def __aenter__(self) -> "AsyncReqivo":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        await self.close()
