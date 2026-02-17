"""src/reqivo/client/session.py

HTTP Session management module.

This module provides session functionality for persistent HTTP connections,
cookie management, authentication, and request state across multiple HTTP calls.
"""

import asyncio
import urllib.parse
from http.cookies import CookieError, SimpleCookie
from typing import (
    IO,
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)

from reqivo.client.auth import (
    build_basic_auth_header,
    build_bearer_auth_header,
)
from reqivo.client.request import AsyncRequest, Request
from reqivo.client.response import Response
from reqivo.transport.connection_pool import AsyncConnectionPool, ConnectionPool

__all__ = ["Session", "AsyncSession"]

# pylint: disable=too-many-instance-attributes,too-many-arguments


class Session:
    """
    HTTP session manager for persistent connections and state.

    This class manages session-specific data like cookies, persistent headers,
    and authentication credentials across multiple requests.

    Attributes:
        cookies: Dictionary of stored cookies.
        headers: Persistent headers for all requests.
        pool: Connection pool for reuse.
        base_url: Base URL prefix for relative URLs.
        default_timeout: Default timeout for requests.
        limits: Default resource limits for requests.
    """

    __slots__ = (
        "cookies",
        "headers",
        "pool",
        "_basic_auth",
        "_bearer_token",
        "limits",
        "base_url",
        "default_timeout",
        "_pre_request_hooks",
        "_post_response_hooks",
    )

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        default_timeout: Optional[float] = 5,
        limits: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        Initialize a new HTTP session.

        Args:
            base_url: Base URL prefix for relative URLs.
            default_timeout: Default timeout in seconds for all requests.
            limits: Default resource limits (max_header_size, etc.).
        """
        self.cookies: Dict[str, str] = {}
        self.headers: Dict[str, str] = {}
        self.pool = ConnectionPool()
        self._basic_auth: Optional[Tuple[str, str]] = None
        self._bearer_token: Optional[str] = None
        self.limits = limits
        self.base_url = base_url
        self.default_timeout = default_timeout
        self._pre_request_hooks: List[Callable[..., Any]] = []
        self._post_response_hooks: List[Callable[..., Any]] = []

    def set_basic_auth(self, username: str, password: str) -> None:
        """
        Set Basic Auth credentials for the session.

        Args:
            username: Username for authentication.
            password: Password for authentication.
        """
        self._basic_auth = (username, password)
        # Clear bearer token if basic auth is set
        self._bearer_token = None

    def set_bearer_token(self, token: str) -> None:
        """
        Set Bearer token for the session.

        Args:
            token: Bearer token for authentication.
        """
        self._bearer_token = token
        # Clear basic auth if bearer token is set
        self._basic_auth = None

    def add_pre_request_hook(self, hook: Callable[..., Any]) -> None:
        """
        Register a pre-request hook.

        The hook receives ``(method, url, headers)`` and must return
        ``(method, url, headers)``.  Hooks are called in FIFO order
        after header/auth/cookie merging, before the request is sent.

        Args:
            hook: Callable that transforms request parameters.
        """
        self._pre_request_hooks.append(hook)

    def add_post_response_hook(self, hook: Callable[..., Any]) -> None:
        """
        Register a post-response hook.

        The hook receives a :class:`Response` and must return a
        :class:`Response`.  Hooks are called in FIFO order after the
        response is received, before it is returned to the caller.

        Args:
            hook: Callable that transforms the response.
        """
        self._post_response_hooks.append(hook)

    def _update_cookies_from_response(self, response: Response) -> None:
        """
        Parse Set-Cookie headers and update internal cookie jar.

        Args:
            response: Response object containing Set-Cookie headers.
        """
        # Set-Cookie headers should be handled individually
        set_cookies = response.headers.get_all("Set-Cookie")
        if set_cookies:
            cookie = SimpleCookie()
            for cookie_val in set_cookies:
                try:
                    cookie.load(cookie_val)
                    for key, morsel in cookie.items():
                        self.cookies[key] = morsel.value
                except CookieError:
                    continue

    def _build_cookie_header(self) -> str:
        """
        Build Cookie header string from stored cookies.

        Returns:
            Cookie header value in 'name=value; name2=value2' format.
        """
        return "; ".join([f"{k}={v}" for k, v in self.cookies.items()])

    def _resolve_url(self, url: str) -> str:
        """
        Resolve URL against base_url if the URL is relative.

        Args:
            url: URL to resolve (absolute or relative).

        Returns:
            Resolved absolute URL.
        """
        if self.base_url and not urllib.parse.urlparse(url).scheme:
            return urllib.parse.urljoin(self.base_url, url)
        return url

    # pylint: disable=too-many-arguments
    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """
        Send an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, etc.).
            url: Request URL (absolute or relative to base_url).
            headers: Additional headers for this request.
            body: Request body.
            timeout: Request timeout (overrides default_timeout).
            limits: Resource limits (overrides session limits).

        Returns:
            Response object.
        """
        url = self._resolve_url(url)
        effective_timeout = timeout if timeout is not None else self.default_timeout

        merged_headers = {**self.headers, **(headers or {})}
        # Inject Authorization header if applicable
        if self._basic_auth:
            merged_headers["Authorization"] = build_basic_auth_header(
                self._basic_auth[0], self._basic_auth[1]
            )
        elif self._bearer_token:
            merged_headers["Authorization"] = build_bearer_auth_header(
                self._bearer_token
            )
        if self.cookies:
            merged_headers["Cookie"] = self._build_cookie_header()

        # Execute pre-request hooks (FIFO)
        for hook in self._pre_request_hooks:
            method, url, merged_headers = hook(method, url, merged_headers)

        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if not host:
            raise ValueError(f"Invalid URL: could not determine host: {url}")

        conn = self.pool.get_connection(
            host,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            use_ssl=(parsed.scheme == "https"),
            timeout=effective_timeout,
        )

        try:
            Request.set_session_instance(self)

            response = Request.send(
                method,
                url,
                headers=merged_headers,
                body=body,
                timeout=effective_timeout,
                connection=conn,
                limits=limits or self.limits,
            )

            self._update_cookies_from_response(response)

            # Execute post-response hooks (FIFO)
            for hook in self._post_response_hooks:
                response = hook(response)

            self.pool.put_connection(conn)

            return response

        except Exception:
            self.pool.discard_connection(conn)
            raise

        finally:
            Request.set_session_instance(None)

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send a GET request."""
        return self._request(
            "GET", url, headers=headers, timeout=timeout, limits=limits
        )

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
        return self._request(
            "POST", url, headers=headers, body=body, timeout=timeout, limits=limits
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
        return self._request(
            "PUT", url, headers=headers, body=body, timeout=timeout, limits=limits
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
        return self._request(
            "DELETE", url, headers=headers, body=body, timeout=timeout, limits=limits
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
        return self._request(
            "PATCH", url, headers=headers, body=body, timeout=timeout, limits=limits
        )

    def head(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send a HEAD request."""
        return self._request(
            "HEAD", url, headers=headers, timeout=timeout, limits=limits
        )

    def options(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an OPTIONS request."""
        return self._request(
            "OPTIONS", url, headers=headers, timeout=timeout, limits=limits
        )

    def close(self) -> None:
        """
        Close all open connections in the connection pool.

        Should be called when done with the session to free resources.
        """
        self.pool.close_all()


class AsyncSession:
    """
    Asynchronous HTTP session manager.

    Attributes:
        cookies: Dictionary of stored cookies.
        headers: Persistent headers for all requests.
        pool: Async connection pool for reuse.
        base_url: Base URL prefix for relative URLs.
        default_timeout: Default timeout for requests.
        limits: Default resource limits for requests.
    """

    __slots__ = (
        "cookies",
        "headers",
        "pool",
        "_basic_auth",
        "_bearer_token",
        "limits",
        "base_url",
        "default_timeout",
        "_pre_request_hooks",
        "_post_response_hooks",
    )

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        default_timeout: Optional[float] = 5,
        limits: Optional[Dict[str, int]] = None,
    ) -> None:
        """
        Initialize a new async HTTP session.

        Args:
            base_url: Base URL prefix for relative URLs.
            default_timeout: Default timeout in seconds for all requests.
            limits: Default resource limits (max_header_size, etc.).
        """
        self.cookies: Dict[str, str] = {}
        self.headers: Dict[str, str] = {}
        self.pool = AsyncConnectionPool()
        self._basic_auth: Optional[Tuple[str, str]] = None
        self._bearer_token: Optional[str] = None
        self.limits = limits
        self.base_url = base_url
        self.default_timeout = default_timeout
        self._pre_request_hooks: List[Callable[..., Any]] = []
        self._post_response_hooks: List[Callable[..., Any]] = []

    def set_basic_auth(self, username: str, password: str) -> None:
        """Set basic auth."""
        self._basic_auth = (username, password)
        self._bearer_token = None

    def set_bearer_token(self, token: str) -> None:
        """Set bearer token."""
        self._bearer_token = token
        self._basic_auth = None

    def add_pre_request_hook(self, hook: Callable[..., Any]) -> None:
        """
        Register a pre-request hook.

        The hook receives ``(method, url, headers)`` and must return
        ``(method, url, headers)``.  May be sync or async.

        Args:
            hook: Callable that transforms request parameters.
        """
        self._pre_request_hooks.append(hook)

    def add_post_response_hook(self, hook: Callable[..., Any]) -> None:
        """
        Register a post-response hook.

        The hook receives a :class:`Response` and must return a
        :class:`Response`.  May be sync or async.

        Args:
            hook: Callable that transforms the response.
        """
        self._post_response_hooks.append(hook)

    def _build_cookie_header(self) -> str:
        return "; ".join([f"{k}={v}" for k, v in self.cookies.items()])

    def _update_cookies_from_response(self, response: Response) -> None:
        set_cookies = response.headers.get_all("Set-Cookie")
        if set_cookies:
            cookie = SimpleCookie()
            for cookie_val in set_cookies:
                try:
                    cookie.load(cookie_val)
                    for key, morsel in cookie.items():
                        self.cookies[key] = morsel.value

                except CookieError:
                    continue

    def _resolve_url(self, url: str) -> str:
        """Resolve URL against base_url if relative."""
        if self.base_url and not urllib.parse.urlparse(url).scheme:
            return urllib.parse.urljoin(self.base_url, url)
        return url

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async GET request."""
        return await self._request(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
            limits=limits,
        )

    async def post(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async POST request."""
        return await self._request(
            "POST",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            limits=limits,
        )

    async def put(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async PUT request."""
        return await self._request(
            "PUT",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            limits=limits,
        )

    async def delete(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async DELETE request."""
        return await self._request(
            "DELETE",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            limits=limits,
        )

    async def patch(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async PATCH request."""
        return await self._request(
            "PATCH",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            limits=limits,
        )

    async def head(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async HEAD request."""
        return await self._request(
            "HEAD",
            url,
            headers=headers,
            timeout=timeout,
            limits=limits,
        )

    async def options(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async OPTIONS request."""
        return await self._request(
            "OPTIONS",
            url,
            headers=headers,
            timeout=timeout,
            limits=limits,
        )

    # pylint: disable=too-many-arguments
    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Optional[float] = None,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Send an async request."""
        url = self._resolve_url(url)
        effective_timeout = timeout if timeout is not None else self.default_timeout

        merged_headers = {**self.headers, **(headers or {})}

        if self._basic_auth:
            merged_headers["Authorization"] = build_basic_auth_header(*self._basic_auth)
        elif self._bearer_token:
            merged_headers["Authorization"] = build_bearer_auth_header(
                self._bearer_token
            )

        if self.cookies:
            merged_headers["Cookie"] = self._build_cookie_header()

        # Execute pre-request hooks (FIFO, supports sync and async)
        for hook in self._pre_request_hooks:
            if asyncio.iscoroutinefunction(hook):
                method, url, merged_headers = await hook(method, url, merged_headers)
            else:
                method, url, merged_headers = hook(method, url, merged_headers)

        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if not host:
            raise ValueError(f"Invalid URL: {url}")

        conn = await self.pool.get_connection(
            host,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            use_ssl=(parsed.scheme == "https"),
            timeout=effective_timeout,
        )

        # Inject session into AsyncRequest to handle cookies
        AsyncRequest.set_session_instance(self)
        try:
            response = await AsyncRequest.send(
                method,
                url,
                headers=merged_headers,
                body=body,
                timeout=effective_timeout,
                connection=conn,
                limits=limits or self.limits,
            )

            # Execute post-response hooks (FIFO, supports sync and async)
            for hook in self._post_response_hooks:
                if asyncio.iscoroutinefunction(hook):
                    response = await hook(response)
                else:
                    response = hook(response)

            # Put connection back to pool if it's still open
            await self.pool.put_connection(conn)

            return response

        except Exception:
            # If request failed, connection might be broken
            await self.pool.discard_connection(conn)
            raise
        finally:
            AsyncRequest.set_session_instance(None)

    async def close(self) -> None:
        """Close pool."""
        await self.pool.close_all()
