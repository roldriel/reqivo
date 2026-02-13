"""src/reqivo/client/session.py

HTTP Session management module.

This module provides session functionality for persistent HTTP connections,
cookie management, authentication, and request state across multiple HTTP calls.
"""

import urllib.parse
from http.cookies import CookieError, SimpleCookie
from typing import Dict, Optional, Tuple, Union

from reqivo.client.auth import (
    build_basic_auth_header,
    build_bearer_auth_header,
)
from reqivo.client.request import AsyncRequest, Request
from reqivo.client.response import Response
from reqivo.transport.connection_pool import AsyncConnectionPool, ConnectionPool

__all__ = ["Session", "AsyncSession"]


class Session:
    """
    HTTP session manager for persistent connections and state.

    This class manages session-specific data like cookies, persistent headers,
    and authentication credentials across multiple requests.

    Attributes:
        cookies: Dictionary of stored cookies.
        headers: Persistent headers for all requests.
        pool: Connection pool for reuse.
        _basic_auth: Basic authentication credentials.
        _bearer_token: Bearer token for authentication.
    """

    __slots__ = ("cookies", "headers", "pool", "_basic_auth", "_bearer_token", "limits")

    def __init__(self, limits: Optional[Dict[str, int]] = None) -> None:
        """
        Initialize a new HTTP session.

        Creates a session with empty cookies, headers, and a new connection pool.
        """
        self.cookies: Dict[str, str] = {}
        self.headers: Dict[str, str] = {}
        self.pool = ConnectionPool()
        self._basic_auth: Optional[Tuple[str, str]] = None
        self._bearer_token: Optional[str] = None
        self.limits = limits

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

    def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Sends a GET request."""

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

        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if not host:
            raise ValueError(f"Invalid URL: could not determine host: {url}")

        conn = self.pool.get_connection(
            host,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            use_ssl=(parsed.scheme == "https"),
            timeout=timeout,
        )

        try:
            Request.set_session_instance(self)

            response = Request.get(
                url,
                headers=merged_headers,
                timeout=timeout,
                connection=conn,
                limits=limits or self.limits,
            )

            self._update_cookies_from_response(response)

            # Return connection to pool
            # In this radical version, there is no stream=True
            self.pool.put_connection(conn)

            return response

        except Exception:
            # If there was an error, ensure the connection is closed
            self.pool.discard_connection(conn)
            raise

        finally:
            Request.set_session_instance(None)

    def post(  # pylint: disable=too-many-arguments
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = 5,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Sends a POST request."""

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

        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if not host:
            raise ValueError(f"Invalid URL: could not determine host: {url}")

        conn = self.pool.get_connection(
            host,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            use_ssl=(parsed.scheme == "https"),
            timeout=timeout,
        )

        try:
            Request.set_session_instance(self)

            response = Request.post(
                url,
                headers=merged_headers,
                body=body,
                timeout=timeout,
                connection=conn,
                limits=limits or self.limits,
            )

            self._update_cookies_from_response(response)

            self.pool.put_connection(conn)

            return response

        except Exception:
            self.pool.discard_connection(conn)
            raise

        finally:
            Request.set_session_instance(None)

    def close(self) -> None:
        """
        Close all open connections in the connection pool.

        Should be called when done with the session to free resources.
        """
        self.pool.close_all()


class AsyncSession:
    """
    Asynchronous HTTP session manager.
    """

    __slots__ = ("cookies", "headers", "pool", "_basic_auth", "_bearer_token", "limits")

    def __init__(self, limits: Optional[Dict[str, int]] = None) -> None:
        self.cookies: Dict[str, str] = {}
        self.headers: Dict[str, str] = {}
        self.pool = AsyncConnectionPool()
        self._basic_auth: Optional[Tuple[str, str]] = None
        self._bearer_token: Optional[str] = None
        self.limits = limits

    def set_basic_auth(self, username: str, password: str) -> None:
        """Set basic auth."""
        self._basic_auth = (username, password)

    def set_bearer_token(self, token: str) -> None:
        """Set bearer token."""
        self._bearer_token = token
        self._basic_auth = None

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

    # pylint: disable=missing-function-docstring
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Async GET."""
        return await self._request(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
            limits=limits,
        )

    async def post(  # pylint: disable=too-many-arguments
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = 5,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return await self._request(
            "POST",
            url,
            headers=headers,
            body=body,
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
        body: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = 5,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Sends an async request."""
        merged_headers = {**self.headers, **(headers or {})}

        if self._basic_auth:
            merged_headers["Authorization"] = build_basic_auth_header(*self._basic_auth)
        elif self._bearer_token:
            merged_headers["Authorization"] = build_bearer_auth_header(
                self._bearer_token
            )

        if self.cookies:
            merged_headers["Cookie"] = self._build_cookie_header()

        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if not host:
            raise ValueError(f"Invalid URL: {url}")

        conn = await self.pool.get_connection(
            host,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            use_ssl=(parsed.scheme == "https"),
            timeout=timeout,
        )

        # Inject session into AsyncRequest to handle cookies
        AsyncRequest.set_session_instance(self)
        try:
            response = await AsyncRequest.send(
                method,
                url,
                headers=merged_headers,
                body=body,
                timeout=timeout,
                connection=conn,
                limits=limits or self.limits,
            )

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
