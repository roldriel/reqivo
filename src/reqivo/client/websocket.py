"""src/reqivo/client/websocket.py

WebSocket client implementation (Sync and Async).
"""

# pylint: disable=line-too-long,too-many-branches,too-many-statements,too-many-locals,too-many-instance-attributes,broad-exception-caught,no-else-raise,too-many-arguments,too-many-positional-arguments

import asyncio
import base64
import contextlib
import hashlib
import os
import socket
import time
import urllib.parse
from typing import Dict, List, Optional, Union

from reqivo.client.request import Request
from reqivo.client.response import Response
from reqivo.transport.connection import AsyncConnection, Connection
from reqivo.utils.websocket_utils import (
    OPCODE_BINARY,
    OPCODE_CLOSE,
    OPCODE_CONTINUATION,
    OPCODE_PING,
    OPCODE_PONG,
    OPCODE_TEXT,
    WebSocketError,
    apply_mask,
    create_frame,
    parse_frame_header,
)

__all__ = ["MAX_FRAME_SIZE", "WebSocket", "AsyncWebSocket"]

# Maximum frame payload size (10 MB)
MAX_FRAME_SIZE = 10 * 1024 * 1024


def _compute_accept_key(sec_key: str) -> str:
    """
    Compute Sec-WebSocket-Accept value from Sec-WebSocket-Key.
    As per RFC 6455 Section 4.2.2.
    """
    magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    # SHA1 is required by RFC 6455, not used for security purposes
    sha1 = hashlib.sha1(
        (sec_key + magic_string).encode("utf-8"), usedforsecurity=False
    ).digest()
    return base64.b64encode(sha1).decode("ascii")


class WebSocket:
    """
    Synchronous WebSocket Client.
    """

    __slots__ = (
        "url",
        "timeout",
        "headers",
        "subprotocols",
        "sock",
        "connected",
        "_buffer",
        "max_frame_size",
        "_auto_reconnect",
        "_max_reconnect_attempts",
        "_reconnect_delay",
    )

    def __init__(
        self,
        url: str,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        subprotocols: Optional[List[str]] = None,
        max_frame_size: int = MAX_FRAME_SIZE,
        auto_reconnect: bool = False,
        max_reconnect_attempts: int = 3,
        reconnect_delay: float = 1.0,
    ):
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}
        self.subprotocols = subprotocols or []
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self._buffer = bytearray()
        self.max_frame_size = max_frame_size
        self._auto_reconnect = auto_reconnect
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_delay = reconnect_delay

    def connect(self) -> None:
        """Establishes the WebSocket connection."""
        parsed = urllib.parse.urlparse(self.url)
        if parsed.scheme not in ("ws", "wss"):
            raise ValueError("URL must use ws:// or wss:// scheme")

        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)

        if not host:
            raise ValueError("Invalid URL: Hostname missing")

        conn = Connection(
            host, port, use_ssl=(parsed.scheme == "wss"), timeout=self.timeout
        )
        self.sock = conn.open()

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        headers = {
            "Host": f"{host}:{port}",
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": key,
            "Sec-WebSocket-Version": "13",
        }

        if self.headers:
            for k, v in self.headers.items():
                headers[k] = v

        if self.subprotocols:
            headers["Sec-WebSocket-Protocol"] = ", ".join(self.subprotocols)

        req_bytes = Request.build_request("GET", path, host, headers, None)
        if self.sock is None:
            raise WebSocketError("Failed to open connection")
        self.sock.sendall(req_bytes)

        header_data = b""
        while b"\r\n\r\n" not in header_data:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise WebSocketError("Connection closed during handshake")
            header_data += chunk

        parts = header_data.split(b"\r\n\r\n", 1)
        headers_bytes = parts[0]
        self._buffer = bytearray(parts[1])

        response = Response(headers_bytes + b"\r\n\r\n")

        if response.status_code != 101:
            raise WebSocketError(
                f"WebSocket handshake failed with status {response.status_code}"
            )

        # Validate Sec-WebSocket-Accept (RFC 6455)
        expected_accept = _compute_accept_key(key)
        actual_accept = response.headers.get("Sec-Websocket-Accept")
        if actual_accept != expected_accept:
            raise WebSocketError(
                f"Invalid Sec-WebSocket-Accept header. "
                f"Expected: {expected_accept}, Got: {actual_accept}"
            )

        self.connected = True

    def _reconnect(self) -> None:
        """Attempt to re-establish the WebSocket connection."""
        self.connected = False
        self._buffer = bytearray()
        if self.sock:
            with contextlib.suppress(Exception):
                self.sock.close()
            self.sock = None
        self.connect()

    def send(self, data: Union[str, bytes]) -> None:
        """Sends data through the WebSocket."""
        if not self.connected:
            raise ConnectionError("WebSocket is not connected")

        opcode = OPCODE_TEXT if isinstance(data, str) else OPCODE_BINARY
        payload = data.encode("utf-8") if isinstance(data, str) else data
        frame = create_frame(payload, opcode=opcode, mask=True)

        for attempt in range(self._max_reconnect_attempts + 1):
            try:
                if self.sock is None:
                    raise ConnectionError("WebSocket is not connected")
                self.sock.sendall(frame)
                return
            except (ConnectionError, WebSocketError, OSError):
                if not self._auto_reconnect or attempt >= self._max_reconnect_attempts:
                    raise
                delay = self._reconnect_delay * (2**attempt)
                time.sleep(delay)
                self._reconnect()

    def recv(self) -> Union[str, bytes]:
        """Receives data from the WebSocket."""
        # pylint: disable=too-many-branches,too-many-statements
        if not self.connected:
            raise ConnectionError("WebSocket is not connected")

        message_payload = bytearray()
        while True:
            while len(self._buffer) < 2:
                if self.sock is None:
                    raise ConnectionError("WebSocket is not connected")

                chunk = self.sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed")

                self._buffer.extend(chunk)

            header_info = parse_frame_header(bytes(self._buffer))
            if header_info is None:
                if self.sock is None:
                    raise ConnectionError("WebSocket is not connected")

                chunk = self.sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Connection closed")

                self._buffer.extend(chunk)
                continue

            header_len, payload_len, fin, _, _, _, opcode, masked = header_info

            # Validate frame size to prevent DoS
            if payload_len > self.max_frame_size:
                raise WebSocketError(
                    f"Frame payload too large: {payload_len} bytes "
                    f"(max: {self.max_frame_size})"
                )

            total_len = header_len + payload_len
            while len(self._buffer) < total_len:
                needed = total_len - len(self._buffer)
                if self.sock is None:
                    raise ConnectionError("WebSocket is not connected")

                chunk = self.sock.recv(min(needed, 4096))
                if not chunk:
                    raise ConnectionError("Connection closed")

                self._buffer.extend(chunk)

            frame_data = bytes(self._buffer[:total_len])
            self._buffer = self._buffer[total_len:]
            payload_bytes = frame_data[header_len:]
            if masked:
                mask_key = frame_data[header_len - 4 : header_len]
                payload_bytes = apply_mask(payload_bytes, mask_key)

            if opcode == OPCODE_CLOSE:
                self.close()
                raise ConnectionError("WebSocket closed by server")

            elif opcode == OPCODE_PING:
                self.pong(payload_bytes)
                continue

            elif opcode == OPCODE_PONG:
                continue

            elif opcode == OPCODE_CONTINUATION:
                message_payload.extend(payload_bytes)
                if fin:
                    break

            elif opcode in (OPCODE_TEXT, OPCODE_BINARY):
                message_payload = bytearray(payload_bytes)
                if fin:
                    break

            else:
                raise WebSocketError(f"Unknown opcode: {opcode}")

        try:
            return message_payload.decode("utf-8")
        except UnicodeDecodeError:
            return bytes(message_payload)

    def ping(self, payload: bytes = b"") -> None:
        """Sends a PING frame."""
        frame = create_frame(payload, opcode=OPCODE_PING, mask=True)
        if self.sock is None:
            raise ConnectionError("WebSocket is not connected")
        self.sock.sendall(frame)

    def pong(self, payload: bytes = b"") -> None:
        """Sends a PONG frame."""
        frame = create_frame(payload, opcode=OPCODE_PONG, mask=True)
        if self.sock is None:
            raise ConnectionError("WebSocket is not connected")
        self.sock.sendall(frame)

    def close(self) -> None:
        """Closes the WebSocket connection."""
        if self.connected:
            # We try to send a CLOSE frame, but if it fails (e.g. connection already closed),
            # we ignore it and proceed to close the transport anyway.
            with contextlib.suppress(Exception):
                frame = create_frame(b"", opcode=OPCODE_CLOSE, mask=True)
                if self.sock is None:
                    raise ConnectionError("WebSocket is not connected")
                self.sock.sendall(frame)

            if self.sock:
                self.sock.close()
            self.connected = False


class AsyncWebSocket:
    """
    Asynchronous WebSocket Client.
    """

    __slots__ = (
        "url",
        "timeout",
        "headers",
        "subprotocols",
        "connection",
        "connected",
        "_buffer",
        "reader",
        "writer",
        "max_frame_size",
        "_auto_reconnect",
        "_max_reconnect_attempts",
        "_reconnect_delay",
    )

    def __init__(
        self,
        url: str,
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        subprotocols: Optional[List[str]] = None,
        max_frame_size: int = MAX_FRAME_SIZE,
        auto_reconnect: bool = False,
        max_reconnect_attempts: int = 3,
        reconnect_delay: float = 1.0,
    ):
        self.url = url
        self.timeout = timeout
        self.headers = headers or {}
        self.subprotocols = subprotocols or []
        self.connection: Optional[AsyncConnection] = None
        self.connected = False
        self._buffer = bytearray()
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.max_frame_size = max_frame_size
        self._auto_reconnect = auto_reconnect
        self._max_reconnect_attempts = max_reconnect_attempts
        self._reconnect_delay = reconnect_delay

    async def connect(self) -> None:
        """Async connect."""
        # pylint: disable=too-many-locals,too-many-branches
        parsed = urllib.parse.urlparse(self.url)
        if parsed.scheme not in ("ws", "wss"):
            raise ValueError("URL must use ws:// or wss:// scheme")

        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)

        if not host:
            raise ValueError("Invalid URL: Hostname missing")

        self.connection = AsyncConnection(
            host, port, use_ssl=(parsed.scheme == "wss"), timeout=self.timeout
        )
        try:
            await self.connection.open()
        except Exception as e:
            raise WebSocketError(f"Connection failed: {e}") from e

        self.reader = self.connection.reader
        self.writer = self.connection.writer

        if not self.writer or not self.reader:
            raise WebSocketError("Failed to establish stream connection")

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        headers = {
            "Host": f"{host}:{port}",
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": key,
            "Sec-WebSocket-Version": "13",
        }

        if self.headers:
            for k, v in self.headers.items():
                headers[k] = v

        if self.subprotocols:
            headers["Sec-WebSocket-Protocol"] = ", ".join(self.subprotocols)

        req_bytes = Request.build_request("GET", path, host, headers, None)
        self.writer.write(req_bytes)
        await self.writer.drain()

        header_data = b""
        while b"\r\n\r\n" not in header_data:
            try:
                if self.timeout:
                    line = await asyncio.wait_for(
                        self.reader.readuntil(b"\r\n"), timeout=self.timeout
                    )
                else:
                    line = await self.reader.readuntil(b"\r\n")

            except asyncio.TimeoutError as exc:
                raise WebSocketError("Connection timeout") from exc

            except asyncio.IncompleteReadError as exc:
                raise WebSocketError("Connection closed during handshake") from exc

            header_data += line

        parts = header_data.split(b"\r\n\r\n", 1)
        headers_bytes = parts[0]
        response = Response(headers_bytes + b"\r\n\r\n")

        if response.status_code != 101:
            raise WebSocketError(
                f"WebSocket handshake failed with status {response.status_code}"
            )

        # Validate Sec-WebSocket-Accept (RFC 6455)
        expected_accept = _compute_accept_key(key)
        actual_accept = response.headers.get("Sec-Websocket-Accept")
        if actual_accept != expected_accept:
            raise WebSocketError(
                f"Invalid Sec-WebSocket-Accept header. "
                f"Expected: {expected_accept}, Got: {actual_accept}"
            )

        self.connected = True

    async def _reconnect(self) -> None:
        """Attempt to re-establish the async WebSocket connection."""
        self.connected = False
        self._buffer = bytearray()
        if self.connection:
            with contextlib.suppress(Exception):
                await self.connection.close()
            self.connection = None
        self.reader = None
        self.writer = None
        await self.connect()

    async def send(self, data: Union[str, bytes]) -> None:
        """Sends data through the WebSocket asynchronously."""
        if not self.connected:
            raise ConnectionError("WebSocket is not connected")

        opcode = OPCODE_TEXT if isinstance(data, str) else OPCODE_BINARY
        payload = data.encode("utf-8") if isinstance(data, str) else data
        frame = create_frame(payload, opcode=opcode, mask=True)

        for attempt in range(self._max_reconnect_attempts + 1):
            try:
                if self.writer:
                    self.writer.write(frame)
                    await self.writer.drain()
                return
            except (ConnectionError, WebSocketError, OSError):
                if not self._auto_reconnect or attempt >= self._max_reconnect_attempts:
                    raise
                delay = self._reconnect_delay * (2**attempt)
                await asyncio.sleep(delay)
                await self._reconnect()

    async def recv(self) -> Union[str, bytes]:
        """Async recv."""
        # pylint: disable=too-many-branches,too-many-statements
        if not self.connected:
            raise WebSocketError("WebSocket is not connected")

        message_payload = bytearray()
        while True:
            try:
                if self.reader is None:
                    raise WebSocketError("WebSocket is not connected")

                header2 = await self.reader.readexactly(2)

            except asyncio.IncompleteReadError as exc:
                raise WebSocketError(
                    "Connection closed while reading frame header"
                ) from exc

            b0 = header2[0]
            b1 = header2[1]

            fin = bool(b0 & 0x80)
            opcode = b0 & 0x0F
            masked = bool(b1 & 0x80)
            payload_len = b1 & 0x7F

            if payload_len == 126:
                if self.reader is None:
                    raise WebSocketError("WebSocket is not connected")

                header_extra = await self.reader.readexactly(2)
                payload_len = int.from_bytes(header_extra, "big")

            elif payload_len == 127:
                if self.reader is None:
                    raise WebSocketError("WebSocket is not connected")

                header_extra = await self.reader.readexactly(8)
                payload_len = int.from_bytes(header_extra, "big")

            # Validate frame size to prevent DoS
            if payload_len > self.max_frame_size:
                raise WebSocketError(
                    f"Frame payload too large: {payload_len} bytes "
                    f"(max: {self.max_frame_size})"
                )

            mask_key = b""
            if masked:
                if self.reader is None:
                    raise WebSocketError("WebSocket is not connected")
                mask_key = await self.reader.readexactly(4)

            try:
                if self.reader is None:
                    raise WebSocketError("WebSocket is not connected")

                payload = await self.reader.readexactly(payload_len)

            except asyncio.IncompleteReadError as exc:
                raise WebSocketError(
                    "Connection closed while reading frame payload"
                ) from exc

            if masked:
                payload = apply_mask(bytes(payload), mask_key)

            if opcode == OPCODE_CLOSE:
                await self.close()
                raise WebSocketError("WebSocket closed by server")

            elif opcode == OPCODE_PING:
                await self.pong(payload)
                continue

            elif opcode == OPCODE_PONG:
                continue

            elif opcode == OPCODE_CONTINUATION:
                message_payload.extend(payload)
                if fin:
                    break

            elif opcode in (OPCODE_TEXT, OPCODE_BINARY):
                message_payload = bytearray(payload)
                if fin:
                    break

            else:
                raise WebSocketError(f"Unknown opcode: {opcode}")

        try:
            return message_payload.decode("utf-8")

        except UnicodeDecodeError:
            return bytes(message_payload)

    async def ping(self, payload: bytes = b"") -> None:
        """Async ping."""
        frame = create_frame(payload, opcode=OPCODE_PING, mask=True)
        if self.writer:
            self.writer.write(frame)
            await self.writer.drain()

    async def pong(self, payload: bytes = b"") -> None:
        """Async pong."""
        frame = create_frame(payload, opcode=OPCODE_PONG, mask=True)
        if self.writer:
            self.writer.write(frame)
            await self.writer.drain()

    async def close(self) -> None:
        """Async close."""
        if self.connected:
            # We try to send a CLOSE frame, but if it fails (e.g. connection already closed),
            # we ignore it and proceed to close the transport anyway.
            with contextlib.suppress(Exception):
                frame = create_frame(b"", opcode=OPCODE_CLOSE, mask=True)
                if self.writer:
                    self.writer.write(frame)
                    await self.writer.drain()

            if self.connection:
                await self.connection.close()

            self.connected = False
