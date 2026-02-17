"""src/reqivo/__init__.py

Reqivo - Modern, async-first HTTP client library for Python.

Reqivo is a zero-dependency HTTP client built entirely on Python's standard library.
It provides both synchronous and asynchronous interfaces for HTTP requests and WebSocket
connections.

Key Features:
    - Zero external dependencies
    - Async-first design with sync support
    - HTTP/1.1 protocol support
    - WebSocket support (sync and async)
    - Connection pooling
    - Full type hints (PEP 561)
    - Memory optimized with __slots__

Example:
    Async usage::

        import asyncio
        from reqivo import AsyncReqivo

        async def main():
            async with AsyncReqivo() as client:
                response = await client.get('https://api.example.com/data')
                print(response.json())

        asyncio.run(main())

    Sync usage::

        from reqivo import Reqivo

        with Reqivo() as client:
            response = client.get('https://api.example.com/data')
            print(response.json())

    WebSocket usage::

        from reqivo import WebSocket

        ws = WebSocket('wss://echo.websocket.org')
        ws.connect()
        ws.send('Hello!')
        message = ws.recv()
        ws.close()
"""

from reqivo.client.facade import AsyncReqivo, Reqivo
from reqivo.client.request import AsyncRequest, Request
from reqivo.client.response import Response
from reqivo.client.session import AsyncSession, Session
from reqivo.client.websocket import AsyncWebSocket, WebSocket
from reqivo.exceptions import WebSocketError
from reqivo.version import __version__

__all__ = [
    "Request",
    "Response",
    "Session",
    "AsyncRequest",
    "AsyncSession",
    "WebSocket",
    "AsyncWebSocket",
    "Reqivo",
    "AsyncReqivo",
    "WebSocketError",
]
