"""tests/unit/test_session.py

Unit tests for reqivo.client.session module.

Test Coverage:
    - Session and AsyncSession initialization
    - Authentication (Basic Auth and Bearer Token)
    - Cookie management (parsing Set-Cookie, building Cookie header)
    - Request methods (GET, POST) with header/cookie merging
    - Connection pool integration
    - Error handling and resource cleanup
    - Global config (base_url, default_timeout)

Testing Strategy:
    - Mock Request, AsyncRequest, and ConnectionPool to avoid real HTTP calls
    - Test state management (cookies, auth, headers)
    - Validate proper cleanup on errors
"""

from http.cookies import CookieError
from typing import Dict
from unittest import mock

import pytest

from reqivo.client.response import Response
from reqivo.client.session import AsyncSession, Session
from reqivo.http.headers import Headers

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def session() -> Session:
    """Create a Session instance."""
    return Session()


@pytest.fixture
def async_session() -> AsyncSession:
    """Create an AsyncSession instance."""
    return AsyncSession()


@pytest.fixture
def mock_response() -> mock.Mock:
    """Create a mock Response."""
    resp = mock.Mock(spec=Response)
    resp.headers = Headers()
    resp.status_code = 200
    return resp


# ============================================================================
# TEST CLASS: Session Init and Auth
# ============================================================================


class TestSessionInit:
    """Tests for Session initialization and authentication."""

    def test_init_creates_empty_state(self, session: Session) -> None:
        """Test that Session initializes with empty cookies and headers."""
        assert session.cookies == {}
        assert session.headers == {}
        assert session._basic_auth is None
        assert session._bearer_token is None
        assert session.pool is not None

    def test_init_with_base_url(self) -> None:
        """Test Session initialization with base_url."""
        s = Session(base_url="https://api.example.com")
        assert s.base_url == "https://api.example.com"

    def test_init_with_default_timeout(self) -> None:
        """Test Session initialization with custom default_timeout."""
        s = Session(default_timeout=10)
        assert s.default_timeout == 10

    def test_init_default_timeout_is_five(self, session: Session) -> None:
        """Test that default_timeout is 5 by default."""
        assert session.default_timeout == 5

    def test_set_basic_auth(self, session: Session) -> None:
        """Test setting Basic Auth credentials."""
        session.set_basic_auth("user", "pass")
        assert session._basic_auth == ("user", "pass")
        assert session._bearer_token is None

    def test_set_bearer_token(self, session: Session) -> None:
        """Test setting Bearer token."""
        session.set_bearer_token("token123")
        assert session._bearer_token == "token123"
        assert session._basic_auth is None

    def test_set_basic_auth_clears_bearer(self, session: Session) -> None:
        """Test that setting Basic Auth clears Bearer token."""
        session._bearer_token = "old_token"
        session.set_basic_auth("user", "pass")
        assert session._bearer_token is None

    def test_set_bearer_token_clears_basic(self, session: Session) -> None:
        """Test that setting Bearer token clears Basic Auth."""
        session._basic_auth = ("old_user", "old_pass")
        session.set_bearer_token("new_token")
        assert session._basic_auth is None


# ============================================================================
# TEST CLASS: Cookie Management
# ============================================================================


class TestSessionCookies:
    """Tests for cookie management."""

    def test_build_cookie_header_empty(self, session: Session) -> None:
        """Test building Cookie header with no cookies."""
        assert session._build_cookie_header() == ""

    def test_build_cookie_header_single_cookie(self, session: Session) -> None:
        """Test building Cookie header with single cookie."""
        session.cookies = {"session_id": "abc123"}
        assert session._build_cookie_header() == "session_id=abc123"

    def test_build_cookie_header_multiple_cookies(self, session: Session) -> None:
        """Test building Cookie header with multiple cookies."""
        session.cookies = {"session_id": "abc123", "user_pref": "dark_mode"}
        header = session._build_cookie_header()
        assert "session_id=abc123" in header
        assert "user_pref=dark_mode" in header
        assert "; " in header

    def test_update_cookies_from_response(
        self, session: Session, mock_response: mock.Mock
    ) -> None:
        """Test parsing Set-Cookie header from response."""
        mock_response.headers = Headers({"Set-Cookie": "session_id=xyz789; Path=/"})
        session._update_cookies_from_response(mock_response)
        assert "session_id" in session.cookies
        assert session.cookies["session_id"] == "xyz789"

    def test_update_cookies_no_set_cookie_header(
        self, session: Session, mock_response: mock.Mock
    ) -> None:
        """Test that no cookies are added when Set-Cookie is absent."""
        mock_response.headers = Headers()
        session._update_cookies_from_response(mock_response)
        assert session.cookies == {}


# ============================================================================
# TEST CLASS: Session GET/POST
# ============================================================================


class TestSessionRequests:
    """Tests for Session request methods."""

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_get_basic_request(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test basic GET request."""
        # Setup mocks
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        # Execute
        result = session.get("https://example.com/test")

        # Verify
        assert result == mock_response
        mock_pool.get_connection.assert_called_once()
        mock_pool.put_connection.assert_called_once_with(mock_conn)
        MockRequest.send.assert_called_once()

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_get_includes_basic_auth_header(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that GET includes Authorization header when Basic Auth is set."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        session.set_basic_auth("user", "pass")
        session.get("https://example.com/test")

        # Check that Authorization header was included
        call_kwargs = MockRequest.send.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"].startswith("Basic ")

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_get_includes_cookies_in_header(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that GET includes Cookie header when cookies are set."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        session.cookies = {"session_id": "abc123"}
        session.get("https://example.com/test")

        call_kwargs = MockRequest.send.call_args[1]
        assert "Cookie" in call_kwargs["headers"]
        assert "session_id=abc123" in call_kwargs["headers"]["Cookie"]

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_get_raises_on_invalid_url(
        self, mock_urlparse: mock.Mock, MockRequest: mock.Mock, session: Session
    ) -> None:
        """Test that GET raises ValueError for invalid URL without hostname."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = None
        mock_parsed.scheme = ""
        mock_urlparse.return_value = mock_parsed

        with pytest.raises(ValueError) as exc_info:
            session.get("invalid://url")

        assert "Invalid URL" in str(exc_info.value)

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_get_closes_connection_on_error(
        self, mock_urlparse: mock.Mock, MockRequest: mock.Mock, session: Session
    ) -> None:
        """Test that connection is closed when request raises exception."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.set_session_instance = mock.Mock()
        MockRequest.send.side_effect = Exception("Network error")

        with pytest.raises(Exception):
            session.get("https://example.com/test")

        mock_pool.discard_connection.assert_called_once_with(mock_conn)

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_post_sends_body(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test POST request with body."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        body_data = '{"key": "value"}'
        session.post("https://example.com/api", body=body_data)

        call_kwargs = MockRequest.send.call_args[1]
        assert call_kwargs["body"] == body_data

    def test_close_closes_pool(self, session: Session) -> None:
        """Test that close() closes the connection pool."""
        mock_pool = mock.Mock()
        session.pool = mock_pool
        session.close()
        mock_pool.close_all.assert_called_once()


# ============================================================================
# TEST CLASS: AsyncSession
# ============================================================================


class TestAsyncSession:
    """Tests for AsyncSession."""

    def test_async_init(self, async_session: AsyncSession) -> None:
        """Test AsyncSession initialization."""
        assert async_session.cookies == {}
        assert async_session.headers == {}
        assert async_session._basic_auth is None
        assert async_session._bearer_token is None

    def test_async_init_with_base_url(self) -> None:
        """Test AsyncSession initialization with base_url."""
        s = AsyncSession(base_url="https://api.example.com")
        assert s.base_url == "https://api.example.com"

    def test_async_init_default_timeout(self, async_session: AsyncSession) -> None:
        """Test AsyncSession default_timeout is 5."""
        assert async_session.default_timeout == 5

    def test_async_set_basic_auth(self, async_session: AsyncSession) -> None:
        """Test async Basic Auth."""
        async_session.set_basic_auth("user", "pass")
        assert async_session._basic_auth == ("user", "pass")

    def test_async_set_bearer_token_clears_basic(
        self, async_session: AsyncSession
    ) -> None:
        """Test that async Bearer token clears Basic Auth."""
        async_session._basic_auth = ("user", "pass")
        async_session.set_bearer_token("token")
        assert async_session._basic_auth is None
        assert async_session._bearer_token == "token"

    def test_async_build_cookie_header(self, async_session: AsyncSession) -> None:
        """Test async cookie header building."""
        async_session.cookies = {"key": "value"}
        assert async_session._build_cookie_header() == "key=value"

    def test_async_update_cookies_handles_exception(
        self, async_session: AsyncSession, mock_response: mock.Mock
    ) -> None:
        """Test that async cookie parsing handles exceptions gracefully."""
        # Malformed Set-Cookie that would raise exception
        mock_response.headers = Headers({"Set-Cookie": "malformed cookie data"})

        # Should not raise, but gracefully skip
        async_session._update_cookies_from_response(mock_response)

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_get(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test async GET request."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        result = await async_session.get("https://example.com/test")

        assert result == mock_response
        mock_pool.get_connection.assert_awaited_once()
        mock_pool.put_connection.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_async_close(self, async_session: AsyncSession) -> None:
        """Test async close."""
        mock_pool = mock.AsyncMock()
        async_session.pool = mock_pool
        await async_session.close()
        mock_pool.close_all.assert_awaited_once()

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_post(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
    ) -> None:
        """Test async POST request."""
        mock_response = mock.Mock()
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        result = await async_session.post("https://example.com/test", body="test_data")

        assert result == mock_response
        # Verify body was passed to send
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["body"] == "test_data"

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_request_with_basic_auth(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
    ) -> None:
        """Test async request with basic authentication."""
        async_session.set_basic_auth("user", "pass")

        mock_response = mock.Mock()
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        await async_session.get("https://example.com/test")

        # Verify Authorization header was added
        call_kwargs = mock_send.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"].startswith("Basic ")

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_request_with_bearer_token(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
    ) -> None:
        """Test async request with bearer token."""
        async_session.set_bearer_token("my_token_123")

        mock_response = mock.Mock()
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        await async_session.get("https://example.com/test")

        # Verify Bearer token was added
        call_kwargs = mock_send.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer my_token_123"

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_request_with_cookies(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
    ) -> None:
        """Test async request includes cookies."""
        async_session.cookies = {"session_id": "abc123", "user": "test"}

        mock_response = mock.Mock()
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        await async_session.get("https://example.com/test")

        # Verify Cookie header was added
        call_kwargs = mock_send.call_args[1]
        assert "Cookie" in call_kwargs["headers"]
        # Cookie can be in any order
        cookie_header = call_kwargs["headers"]["Cookie"]
        assert "session_id=abc123" in cookie_header
        assert "user=test" in cookie_header

    @pytest.mark.asyncio
    async def test_async_request_invalid_url(self, async_session: AsyncSession) -> None:
        """Test async request with invalid URL (no hostname)."""
        with pytest.raises(ValueError, match="Invalid URL"):
            await async_session.get("not-a-valid-url")

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_request_exception_closes_connection(
        self,
        mock_urlparse: mock.Mock,
        MockAsyncRequest: mock.Mock,
        async_session: AsyncSession,
    ) -> None:
        """Test async request closes connection on exception."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_conn.close = mock.AsyncMock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        MockAsyncRequest.send = mock.AsyncMock(
            side_effect=RuntimeError("Request failed")
        )
        MockAsyncRequest.set_session_instance = mock.Mock()

        with pytest.raises(RuntimeError, match="Request failed"):
            await async_session.get("https://example.com/test")

        # Verify connection was closed on exception
        mock_pool.discard_connection.assert_awaited_once_with(mock_conn)


class TestSessionExceptionHandling:
    """Tests for sync Session exception handling."""

    def test_sync_request_exception_closes_connection(self) -> None:
        """Test sync request closes connection on exception."""
        from reqivo.client.session import Request

        session = Session()

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        # Mock Request.send to raise exception
        original_send = Request.send
        Request.send = mock.Mock(side_effect=RuntimeError("Request failed"))

        try:
            with pytest.raises(RuntimeError, match="Request failed"):
                session.get("http://example.com/test")

            # Verify connection was closed on exception
            mock_pool.discard_connection.assert_called_once_with(mock_conn)
        finally:
            # Restore original method
            Request.send = original_send

    def test_update_cookies_malformed_cookie(self) -> None:
        """Test _update_cookies_from_response handles malformed cookies gracefully."""
        session = Session()

        # Create a mock response with malformed Set-Cookie header
        mock_response = mock.Mock()
        mock_response.headers = Headers(
            {"Set-Cookie": "malformed cookie data \x00 invalid"}
        )

        # Should not raise exception
        session._update_cookies_from_response(mock_response)

        # Cookies dict should remain unchanged or handle gracefully
        # (The implementation catches exceptions and continues)

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_sync_get_with_bearer_token(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
    ) -> None:
        """Test sync GET request with bearer token."""
        session = Session()
        session.set_bearer_token("my_bearer_token")

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_response = mock.Mock(spec=Response)
        mock_response.headers = Headers()

        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        session.get("https://example.com/test")

        # Verify Bearer token was added
        call_kwargs = MockRequest.send.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer my_bearer_token"

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_sync_post_with_basic_auth(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
    ) -> None:
        """Test sync POST request with basic authentication."""
        session = Session()
        session.set_basic_auth("user123", "pass456")

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_response = mock.Mock(spec=Response)
        mock_response.headers = Headers()

        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        session.post("https://example.com/api", body="test")

        # Verify Basic Auth header was added
        call_kwargs = MockRequest.send.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"].startswith("Basic ")

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_sync_post_with_bearer_token(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
    ) -> None:
        """Test sync POST request with bearer token."""
        session = Session()
        session.set_bearer_token("token_abc123")

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_response = mock.Mock(spec=Response)
        mock_response.headers = Headers()

        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        session.post("https://example.com/api", body="test")

        # Verify Bearer token was added
        call_kwargs = MockRequest.send.call_args[1]
        assert "Authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["Authorization"] == "Bearer token_abc123"

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_sync_post_with_cookies(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
    ) -> None:
        """Test sync POST request includes cookies."""
        session = Session()
        session.cookies = {"session_id": "xyz789", "user": "john"}

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_response = mock.Mock(spec=Response)
        mock_response.headers = Headers()

        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        session.post("https://example.com/api", body="test")

        # Verify Cookie header was added
        call_kwargs = MockRequest.send.call_args[1]
        assert "Cookie" in call_kwargs["headers"]
        cookie_header = call_kwargs["headers"]["Cookie"]
        assert "session_id=xyz789" in cookie_header
        assert "user=john" in cookie_header

    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_sync_post_raises_on_invalid_url(self, mock_urlparse: mock.Mock) -> None:
        """Test sync POST raises ValueError for invalid URL."""
        session = Session()

        mock_parsed = mock.Mock()
        mock_parsed.hostname = None
        mock_parsed.scheme = ""
        mock_urlparse.return_value = mock_parsed

        with pytest.raises(ValueError, match="Invalid URL"):
            session.post("invalid://url", body="test")

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_sync_post_closes_connection_on_error(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
    ) -> None:
        """Test sync POST closes connection on exception."""
        session = Session()

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        session.pool = mock_pool

        MockRequest.set_session_instance = mock.Mock()
        MockRequest.send.side_effect = RuntimeError("POST failed")

        with pytest.raises(RuntimeError, match="POST failed"):
            session.post("https://example.com/api", body="test")

        # Verify connection was closed on exception
        mock_pool.discard_connection.assert_called_once_with(mock_conn)

    def test_async_update_cookies_exception_path(self) -> None:
        """Test AsyncSession cookie parsing exception path is covered."""
        async_session = AsyncSession()

        # Create a mock response with a Set-Cookie header
        mock_response = mock.Mock()
        # Set a truthy value so we enter the try block
        mock_response.headers = Headers({"Set-Cookie": "some_cookie_string"})

        # Patch SimpleCookie.load in the reqivo.client.session module to raise exception
        with mock.patch(
            "reqivo.client.session.SimpleCookie.load",
            side_effect=CookieError("Malformed cookie"),
        ):
            # Should not raise - exception should be caught
            async_session._update_cookies_from_response(mock_response)

        # Verify cookies remain empty after exception
        assert async_session.cookies == {}

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.ConnectionPool")
    def test_session_persists_limits(
        self, MockPool: mock.MagicMock, MockRequest: mock.MagicMock
    ) -> None:
        """Test that Session stores and passes limits."""
        limits = {"max_header_size": 1000}
        session = Session(limits=limits)
        assert session.limits == limits

        resp = mock.Mock(spec=Response)
        resp.headers = Headers()
        MockRequest.send.return_value = resp
        MockRequest.set_session_instance = mock.Mock()

        session.get("http://example.com")

        args, kwargs = MockRequest.send.call_args
        assert kwargs["limits"] == limits

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.AsyncConnectionPool")
    async def test_async_session_persists_limits(
        self, MockPool: mock.MagicMock, MockAsyncSend: mock.AsyncMock
    ) -> None:
        """Test that AsyncSession stores and passes limits."""
        limits = {"max_field_count": 50}
        async_session = AsyncSession(limits=limits)
        assert async_session.limits == limits

        resp = mock.Mock(spec=Response)
        resp.headers = Headers()
        MockAsyncSend.return_value = resp

        mock_pool = mock.AsyncMock()
        async_session.pool = mock_pool

        await async_session.get("http://example.com")

        args, kwargs = MockAsyncSend.call_args
        assert kwargs["limits"] == limits
