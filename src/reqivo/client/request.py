"""src/reqivo/client/request.py

HTTP request builder and sender.
"""

# pylint: disable=redefined-builtin,protected-access,too-many-statements

import asyncio
import collections.abc
import socket
import urllib.parse
from typing import (
    IO,
    TYPE_CHECKING,
    AsyncIterator,
    Dict,
    Iterator,
    Optional,
    Union,
    cast,
)

from reqivo.client.response import Response
from reqivo.exceptions import (
    NetworkError,
    ReadTimeout,
    RedirectLoopError,
    RequestError,
    TooManyRedirects,
)
from reqivo.http.body import (
    async_iter_write_chunked,
    file_to_iterator,
    iter_write_chunked,
)

# pylint: disable=unused-import
from reqivo.http.http11 import HttpParser
from reqivo.transport.connection import AsyncConnection, Connection
from reqivo.utils.timing import Timeout

if TYPE_CHECKING:  # pragma: no cover
    from reqivo.client.session import AsyncSession, Session

__all__ = ["Request", "AsyncRequest"]


class Request:
    """
    HTTP request builder and sender.
    """

    _session_instance: Optional["Session"] = None

    @classmethod
    def set_session_instance(cls, session: Optional["Session"]) -> None:
        """Sets the current session instance for the request."""
        cls._session_instance = session

    @staticmethod
    def build_request(
        method: str,
        path: str,
        host: str,
        headers: Dict[str, str],
        body: Optional[Union[str, bytes]],
    ) -> bytes:
        """
        Builds the raw HTTP request bytes.
        """
        request_line = f"{method} {path} HTTP/1.1\r\n"
        default_headers = {
            "Host": host,
            "Connection": "close",
            "User-Agent": "reqivo/0.3",
        }

        final_headers = {**default_headers, **headers}

        if body:
            if isinstance(body, str):
                body_bytes = body.encode("utf-8")
            else:
                body_bytes = body
            final_headers["Content-Length"] = str(len(body_bytes))
        else:
            body_bytes = b""

        headers_str = ""
        for k, v in final_headers.items():
            # Validate against HTTP header injection attacks
            if "\r" in k or "\n" in k or "\r" in v or "\n" in v:
                raise ValueError(f"Invalid character in header {k}: {v!r}")
            if "\x00" in k or "\x00" in v:
                raise ValueError(f"Null byte in header {k}: {v!r}")
            headers_str += f"{k}: {v}\r\n"

        full_request = (request_line + headers_str + "\r\n").encode(
            "utf-8"
        ) + body_bytes
        return full_request

    @staticmethod
    def build_request_headers(
        method: str,
        path: str,
        host: str,
        headers: Dict[str, str],
        *,
        chunked: bool = False,
    ) -> bytes:
        """
        Build the request line and headers without a body.

        Used for streaming uploads where the body is written separately
        using chunked transfer encoding.

        Args:
            method: HTTP method.
            path: Request path.
            host: Host header value.
            headers: Request headers.
            chunked: If True, adds Transfer-Encoding: chunked.

        Returns:
            Encoded request line and headers ending with \\r\\n\\r\\n.
        """
        request_line = f"{method} {path} HTTP/1.1\r\n"
        default_headers = {
            "Host": host,
            "Connection": "close",
            "User-Agent": "reqivo/0.3",
        }

        final_headers = {**default_headers, **headers}
        if chunked:
            final_headers["Transfer-Encoding"] = "chunked"

        headers_str = ""
        for k, v in final_headers.items():
            if "\r" in k or "\n" in k or "\r" in v or "\n" in v:
                raise ValueError(f"Invalid character in header {k}: {v!r}")
            if "\x00" in k or "\x00" in v:
                raise ValueError(f"Null byte in header {k}: {v!r}")
            headers_str += f"{k}: {v}\r\n"

        return (request_line + headers_str + "\r\n").encode("utf-8")

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches
    def send(
        cls,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Union[float, Timeout, None] = 5,
        connection: Optional[Connection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """
        Sends an HTTP request with automatic redirects support.
        """
        history: list[Response] = []
        visited_urls = {url}
        current_url = url
        current_method = method
        current_headers = headers or {}
        current_body = body

        # Ensure timeout is a Timeout object
        if isinstance(timeout, Timeout):
            timeout_obj = timeout
        else:
            timeout_obj = Timeout.from_float(timeout)

        for _ in range(max_redirects + 1):
            response = cls._perform_request(
                current_method,
                current_url,
                current_headers,
                current_body,
                timeout_obj,
                connection,
                limits=limits,
            )

            # Check for redirect
            if (
                allow_redirects
                and response.status_code in (301, 302, 303, 307, 308)
                and "Location" in response.headers
            ):
                # Consume response body to free connection
                response.text()

                response.history = list(history)
                history.append(response)

                # Prepare for next request
                redirect_url = response.headers["Location"]
                # Handle relative URLs
                parsed_current = urllib.parse.urlparse(current_url)
                current_url = urllib.parse.urljoin(current_url, redirect_url)
                if current_url in visited_urls:
                    raise RedirectLoopError(f"Redirect cycle detected: {current_url}")
                visited_urls.add(current_url)
                parsed_new = urllib.parse.urlparse(current_url)

                # Handle method changes
                status = response.status_code
                if status == 303:
                    current_method = "GET"
                    current_body = None
                    # Drop Content-* headers
                    current_headers = {
                        k: v
                        for k, v in current_headers.items()
                        if not k.lower().startswith("content-")
                    }
                elif status in (301, 302) and current_method != "HEAD":
                    current_method = "GET"
                    current_body = None
                    current_headers = {
                        k: v
                        for k, v in current_headers.items()
                        if not k.lower().startswith("content-")
                    }

                # Strip Authorization if host changed
                if parsed_new.netloc != parsed_current.netloc:
                    if "Authorization" in current_headers:
                        del current_headers["Authorization"]

                # If connection was specific, we shouldn't reuse it for redirect
                # to different host
                # Logic: if connection provided, use it only if hosts match
                # (handled in _perform_request)
                continue

            # Not a redirect or max reached (handled by loop end?)
            # Actually if max reached, loop ends.
            response.history = list(history)
            return response

        raise TooManyRedirects(f"Exceeded {max_redirects} redirects.")

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    # pylint: disable=too-many-locals,too-many-branches
    def _perform_request(
        cls,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]],
        timeout: Timeout,
        connection: Optional[Connection],
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Internal method to perform a single HTTP request."""
        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme
        host = parsed.hostname
        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        if not host:
            raise RequestError("Invalid URL: could not determine host")

        headers_dict = headers.copy()
        headers_dict.setdefault("Connection", "close")

        # Determine if body is a streaming iterable
        is_streaming = (
            body is not None
            and not isinstance(body, (str, bytes))
            and (isinstance(body, collections.abc.Iterator) or hasattr(body, "read"))
        )

        if is_streaming:
            request_bytes = cls.build_request_headers(
                method, path, host, headers_dict, chunked=True
            )
        else:
            simple_body = cast(Optional[Union[str, bytes]], body)
            request_bytes = cls.build_request(
                method, path, host, headers_dict, simple_body
            )

        if connection and connection.host == host and connection.port == port:
            conn = connection
        else:
            conn = Connection(
                host,
                port,
                use_ssl=(scheme == "https"),
                timeout=timeout,
            )

        try:
            if not conn.sock:
                conn.open()

            sock = conn.sock
            if not sock:
                raise NetworkError("Failed to open connection")

            sock.sendall(request_bytes)

            # If streaming, write body using chunked encoding
            if is_streaming:
                if hasattr(body, "read"):
                    chunks = file_to_iterator(body)  # type: ignore[arg-type]
                else:
                    chunks = cast(Iterator[bytes], body)
                iter_write_chunked(sock, chunks)

            # Read response
            response_data = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
            except socket.timeout as exc:
                raise ReadTimeout(f"Read timed out: {exc}") from exc
            except socket.error as exc:
                raise NetworkError(f"Network error during read: {exc}") from exc

            if not response_data:
                raise NetworkError("Server closed connection without response")

            resp_obj = Response(response_data, connection=conn, limits=limits)

            session_instance = getattr(cls, "_session_instance", None)
            if session_instance:
                session_instance._update_cookies_from_response(resp_obj)

            return resp_obj

        finally:
            if conn is not connection:
                # If we created the connection, close it
                conn.close()
            # If explicit connection provided, caller handles closing (usually)

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    def get(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[Connection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return cls.send(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    def post(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[Connection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return cls.send(
            "POST",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    def put(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[Connection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return cls.send(
            "PUT",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    def delete(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[Connection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return cls.send(
            "DELETE",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    def patch(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes, Iterator[bytes], IO[bytes]]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[Connection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return cls.send(
            "PATCH",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    def head(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[Connection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return cls.send(
            "HEAD",
            url,
            headers=headers,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    def options(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[Connection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return cls.send(
            "OPTIONS",
            url,
            headers=headers,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )


class AsyncRequest:
    """
    Asynchronous HTTP request builder and sender.
    """

    _session_instance: Optional["AsyncSession"] = None

    @classmethod
    def set_session_instance(cls, session: Optional["AsyncSession"]) -> None:
        """Sets the current session instance for the async request."""
        cls._session_instance = session

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches
    async def send(
        cls,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Union[float, Timeout, None] = 5,
        connection: Optional[AsyncConnection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Sends an async request with automatic redirects support."""
        history: list[Response] = []
        visited_urls = {url}
        current_url = url
        current_method = method
        current_headers = headers or {}
        current_body = body

        if isinstance(timeout, Timeout):
            timeout_obj = timeout
        else:
            timeout_obj = Timeout.from_float(timeout)

        for _ in range(max_redirects + 1):
            response = await cls._perform_request(
                current_method,
                current_url,
                current_headers,
                current_body,
                timeout_obj,
                connection,
                limits=limits,
            )

            # Check for redirect
            if (
                allow_redirects
                and response.status_code in (301, 302, 303, 307, 308)
                and "Location" in response.headers
            ):
                # Consume response body to free connection
                response.text()

                response.history = list(history)
                history.append(response)

                # Prepare for next request
                redirect_url = response.headers["Location"]
                parsed_current = urllib.parse.urlparse(current_url)
                current_url = urllib.parse.urljoin(current_url, redirect_url)
                if current_url in visited_urls:
                    raise RedirectLoopError(f"Redirect cycle detected: {current_url}")
                visited_urls.add(current_url)
                parsed_new = urllib.parse.urlparse(current_url)

                status = response.status_code
                if status == 303:
                    current_method = "GET"
                    current_body = None
                    current_headers = {
                        k: v
                        for k, v in current_headers.items()
                        if not k.lower().startswith("content-")
                    }
                elif status in (301, 302) and current_method != "HEAD":
                    current_method = "GET"
                    current_body = None
                    current_headers = {
                        k: v
                        for k, v in current_headers.items()
                        if not k.lower().startswith("content-")
                    }

                # Strip Authorization if host changed
                if parsed_new.netloc != parsed_current.netloc:
                    if "Authorization" in current_headers:
                        del current_headers["Authorization"]

                continue

            response.history = list(history)
            return response

        raise TooManyRedirects(f"Exceeded {max_redirects} redirects.")

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    # pylint: disable=too-many-locals,too-many-branches
    async def _perform_request(
        cls,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ],
        timeout: Timeout,
        connection: Optional[AsyncConnection],
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        """Internal method to perform a single async HTTP request."""
        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme
        host = parsed.hostname
        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        if not host:
            raise RequestError("Invalid URL: could not determine host")

        headers_dict = headers.copy()
        headers_dict.setdefault("Connection", "close")

        # Determine if body is a streaming iterable
        is_async_streaming = body is not None and isinstance(
            body, collections.abc.AsyncIterator
        )
        is_sync_streaming = (
            body is not None
            and not isinstance(body, (str, bytes))
            and not is_async_streaming
            and (isinstance(body, collections.abc.Iterator) or hasattr(body, "read"))
        )
        is_streaming = is_async_streaming or is_sync_streaming

        if is_streaming:
            request_bytes = Request.build_request_headers(
                method, path, host, headers_dict, chunked=True
            )
        else:
            simple_body = cast(Optional[Union[str, bytes]], body)
            request_bytes = Request.build_request(
                method, path, host, headers_dict, simple_body
            )

        if connection and connection.host == host and connection.port == port:
            conn = connection
        else:
            conn = AsyncConnection(
                host,
                port,
                use_ssl=(scheme == "https"),
                timeout=timeout,
            )

        try:
            if not conn.writer or not conn.reader:
                await conn.open()

            if conn.writer is None or conn.reader is None:
                raise NetworkError("Failed to establish stream connection")

            conn.writer.write(request_bytes)
            await conn.writer.drain()

            # If streaming, write body using chunked encoding
            if is_async_streaming:
                await async_iter_write_chunked(
                    conn.writer, body  # type: ignore[arg-type]
                )
            elif is_sync_streaming:
                sync_chunks: Iterator[bytes]
                if hasattr(body, "read"):
                    sync_chunks = file_to_iterator(body)  # type: ignore[arg-type]
                else:
                    sync_chunks = body  # type: ignore[assignment]
                # Write sync chunks through the async writer
                for chunk_data in sync_chunks:
                    if not chunk_data:
                        continue
                    size_line = f"{len(chunk_data):x}\r\n".encode("ascii")
                    conn.writer.write(size_line + chunk_data + b"\r\n")
                    await conn.writer.drain()
                conn.writer.write(b"0\r\n\r\n")
                await conn.writer.drain()

            # Read response
            response_data = b""
            try:
                while True:
                    if timeout.read is not None:
                        chunk = await asyncio.wait_for(
                            conn.reader.read(4096), timeout=timeout.read
                        )
                    elif timeout.total is not None:
                        chunk = await asyncio.wait_for(
                            conn.reader.read(4096), timeout=timeout.total
                        )
                    else:
                        chunk = await conn.reader.read(4096)

                    if not chunk:
                        break
                    response_data += chunk
            except asyncio.TimeoutError as exc:
                raise ReadTimeout(f"Read timed out: {exc}") from exc
            except Exception as exc:  # pylint: disable=broad-exception-caught
                raise NetworkError(f"Network error during read: {exc}") from exc

            if not response_data:
                raise NetworkError("Server closed connection without response")

            resp_obj = Response(response_data, limits=limits)

            session_instance = getattr(cls, "_session_instance", None)
            if session_instance:
                session_instance._update_cookies_from_response(resp_obj)

            return resp_obj

        finally:
            if conn is not connection:
                await conn.close()

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    async def get(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[AsyncConnection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return await cls.send(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    async def post(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Optional[float] = 5,
        connection: Optional[AsyncConnection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return await cls.send(
            "POST",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    async def put(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Optional[float] = 5,
        connection: Optional[AsyncConnection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return await cls.send(
            "PUT",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    async def delete(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Optional[float] = 5,
        connection: Optional[AsyncConnection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return await cls.send(
            "DELETE",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    async def patch(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[
            Union[str, bytes, Iterator[bytes], AsyncIterator[bytes], IO[bytes]]
        ] = None,
        timeout: Optional[float] = 5,
        connection: Optional[AsyncConnection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return await cls.send(
            "PATCH",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    async def head(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[AsyncConnection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return await cls.send(
            "HEAD",
            url,
            headers=headers,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    async def options(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[AsyncConnection] = None,
        allow_redirects: bool = True,
        max_redirects: int = 30,
        limits: Optional[Dict[str, int]] = None,
    ) -> Response:
        return await cls.send(
            "OPTIONS",
            url,
            headers=headers,
            timeout=timeout,
            connection=connection,
            allow_redirects=allow_redirects,
            max_redirects=max_redirects,
            limits=limits,
        )
