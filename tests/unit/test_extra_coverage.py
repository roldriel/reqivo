# tests/unit/test_extra_coverage.py
import socket
import unittest
from http.cookies import CookieError, SimpleCookie
from unittest.mock import MagicMock, patch

import pytest

from reqivo.client.response import Response
from reqivo.client.session import Session
from reqivo.exceptions import ConnectTimeout, ReadTimeout
from reqivo.transport.connection import Connection


def test_session_cookie_parsing_exception():
    session = Session()
    # Mock response with headers that cause SimpleCookie.load to fail is hard,
    # but we can mock SimpleCookie.load itself.
    response = MagicMock(spec=Response)
    response.headers.get_all.return_value = ["invalid cookie"]

    with patch(
        "reqivo.client.session.SimpleCookie.load",
        side_effect=CookieError("Parsing error"),
    ):
        session._update_cookies_from_response(response)
        # Should not raise exception because of the try-except block
        assert session.cookies == {}


def test_connection_socket_timeout_in_error_catch():
    conn = Connection("localhost", 80)
    # We want to trigger line 120 in connection.py
    # except socket.error as e:
    #     if isinstance(e, socket.timeout):
    #         raise ConnectTimeout(...)

    with patch(
        "socket.create_connection", side_effect=socket.timeout("Custom timeout")
    ):
        with pytest.raises(ConnectTimeout):
            conn.open()


@pytest.mark.asyncio
async def test_async_session_cookie_parsing_exception():
    from reqivo.client.session import AsyncSession

    session = AsyncSession()
    response = MagicMock(spec=Response)
    response.headers.get_all.return_value = ["invalid cookie"]

    with patch(
        "reqivo.client.session.SimpleCookie.load",
        side_effect=CookieError("Parsing error"),
    ):
        session._update_cookies_from_response(response)
        assert session.cookies == {}
