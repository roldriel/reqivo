"""client/request.py

HTTP request builder and sender.
"""

# pylint: disable=redefined-builtin,protected-access

import urllib.parse
from typing import TYPE_CHECKING, Dict, Optional, Union

from reqivo.client.response import Response

# pylint: disable=unused-import
# Note: read_chunked and read_exact will be moved/handled,
# for now they are still in transport or we will implement body.py logic
# But the plan says body.py will have this logic.
# For now, I'll use placeholders if needed or keep existing if they work.
# Actually they were in core/utils.py which I am about to delete.
# I will move them to transport/connection.py or http/body.py as per the plan.
from reqivo.exceptions import (
    InvalidResponseError,
    NetworkError,
    ProtocolError,
    RedirectLoopError,
    ReqivoError,
    RequestError,
    TimeoutError,
)

# pylint: disable=unused-import
from reqivo.http.http11 import HttpParser
from reqivo.transport.connection import AsyncConnection, Connection
from reqivo.utils.timing import Timeout

if TYPE_CHECKING:
    from reqivo.client.session import AsyncSession, Session


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
            "User-Agent": "reqivo/0.1",
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

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-branches
    def send(
        cls,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = None,
        timeout: Union[float, Timeout, None] = 5,
        connection: Optional[Connection] = None,
    ) -> Response:
        """
        Sends an HTTP request.
        """
        # Ensure timeout is a Timeout object
        if isinstance(timeout, Timeout):
            timeout_obj = timeout
        else:
            timeout_obj = Timeout.from_float(timeout)

        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme
        host = parsed.hostname
        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        if not host:
            raise RequestError("Invalid URL: could not determine host")

        headers_dict = headers or {}
        headers_dict.setdefault("Connection", "close")
        request_bytes = cls.build_request(method, path, host, headers_dict, body)

        if connection and connection.host == host and connection.port == port:
            conn = connection
        else:
            conn = Connection(
                host,
                port,
                use_ssl=(scheme == "https"),
                timeout=timeout_obj,
            )

        try:
            if not conn.sock:
                conn.open()

            sock = conn.sock
            if not sock:
                raise NetworkError("Failed to open connection")

            sock.sendall(request_bytes)

            # Leer todo el contenido hasta cierre de socket
            response_data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_data += chunk

            if not response_data:
                raise NetworkError("Server closed connection without response")

            resp_obj = Response(response_data, connection=conn)

            session_instance = getattr(cls, "_session_instance", None)
            if session_instance:
                session_instance._update_cookies_from_response(resp_obj)

            return resp_obj

        finally:
            # Siempre cerrar en esta versión radical sin pools complejos por ahora
            conn.close()

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    def get(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[Connection] = None,
    ) -> Response:
        return cls.send(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
            connection=connection,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    def post(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[Connection] = None,
    ) -> Response:
        return cls.send(
            "POST",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
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
        body: Optional[Union[str, bytes]] = None,
        timeout: Union[float, Timeout, None] = 5,
        connection: Optional[AsyncConnection] = None,
    ) -> Response:
        """Sends an async request."""
        if isinstance(timeout, Timeout):
            timeout_obj = timeout
        else:
            timeout_obj = Timeout.from_float(timeout)

        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme
        host = parsed.hostname
        port = parsed.port or (443 if scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        if not host:
            raise RequestError("Invalid URL: could not determine host")

        headers_dict = headers or {}
        headers_dict.setdefault("Connection", "close")

        # Reuse Request.build_request
        request_bytes = Request.build_request(method, path, host, headers_dict, body)

        if connection and connection.host == host and connection.port == port:
            conn = connection
        else:
            conn = AsyncConnection(
                host,
                port,
                use_ssl=(scheme == "https"),
                timeout=timeout_obj,
            )

        try:
            if not conn.writer or not conn.reader:
                await conn.open()

            if conn.writer is None or conn.reader is None:
                raise NetworkError("Failed to establish stream connection")

            conn.writer.write(request_bytes)
            await conn.writer.drain()

            # Leer todo el contenido asíncronamente
            response_data = b""
            while True:
                chunk = await conn.reader.read(4096)
                if not chunk:
                    break
                response_data += chunk

            if not response_data:
                raise NetworkError("Server closed connection without response")

            resp_obj = Response(response_data)

            session_instance = getattr(cls, "_session_instance", None)
            if session_instance:
                session_instance._update_cookies_from_response(resp_obj)

            return resp_obj

        finally:
            await conn.close()

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    async def get(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[AsyncConnection] = None,
    ) -> Response:
        return await cls.send(
            "GET",
            url,
            headers=headers,
            timeout=timeout,
            connection=connection,
        )

    @classmethod
    # pylint: disable=too-many-arguments,too-many-positional-arguments,missing-function-docstring
    async def post(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Union[str, bytes]] = None,
        timeout: Optional[float] = 5,
        connection: Optional[AsyncConnection] = None,
    ) -> Response:
        return await cls.send(
            "POST",
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            connection=connection,
        )
