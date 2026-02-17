"""tests/unit/test_http_methods.py

Unit tests for HTTP method helpers (put, delete, patch, head, options)
and global config (base_url, default_timeout) added in v0.3.0.

Test Coverage:
    - New HTTP methods (put, delete, patch, head, options) on Session
    - New HTTP methods on AsyncSession
    - New HTTP methods on Request and AsyncRequest
    - Session._request() consolidation (all methods delegate correctly)
    - base_url resolution with relative and absolute URLs
    - default_timeout fallback and per-request override

Testing Strategy:
    - Mock Request.send / AsyncRequest.send to avoid real HTTP calls
    - Mock urlparse and ConnectionPool for Session tests
    - Verify correct method string and kwargs are passed through
"""

from unittest import mock

import pytest

from reqivo.client.request import AsyncRequest, Request
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
    """Create a mock Response with empty headers."""
    resp = mock.Mock(spec=Response)
    resp.headers = Headers()
    resp.status_code = 200
    return resp


def _setup_session_mocks(
    session: Session,
    mock_urlparse: mock.Mock,
    MockRequest: mock.Mock,
    mock_response: mock.Mock,
) -> mock.Mock:
    """Helper to set up common mocks for Session tests."""
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
    return mock_conn


# ============================================================================
# TEST CLASS: Session HTTP Methods
# ============================================================================


class TestSessionHttpMethods:
    """Tests for Session put, delete, patch, head, options methods."""

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_put_sends_correct_method(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that put() delegates to _request with method PUT."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.put("https://example.com/resource", body='{"name": "test"}')

        call_args = MockRequest.send.call_args
        assert call_args[0][0] == "PUT"
        assert call_args[1]["body"] == '{"name": "test"}'

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_delete_sends_correct_method(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that delete() delegates to _request with method DELETE."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.delete("https://example.com/resource/1")

        call_args = MockRequest.send.call_args
        assert call_args[0][0] == "DELETE"

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_delete_with_body(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that delete() can include a body."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.delete("https://example.com/resource/1", body='{"reason": "obsolete"}')

        call_args = MockRequest.send.call_args
        assert call_args[1]["body"] == '{"reason": "obsolete"}'

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_patch_sends_correct_method(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that patch() delegates to _request with method PATCH."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.patch("https://example.com/resource/1", body='{"name": "updated"}')

        call_args = MockRequest.send.call_args
        assert call_args[0][0] == "PATCH"
        assert call_args[1]["body"] == '{"name": "updated"}'

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_head_sends_correct_method(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that head() delegates to _request with method HEAD."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.head("https://example.com/resource")

        call_args = MockRequest.send.call_args
        assert call_args[0][0] == "HEAD"

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_head_does_not_send_body(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that head() does not include a body parameter."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.head("https://example.com/resource")

        call_args = MockRequest.send.call_args
        assert call_args[1]["body"] is None

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_options_sends_correct_method(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that options() delegates to _request with method OPTIONS."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.options("https://example.com/resource")

        call_args = MockRequest.send.call_args
        assert call_args[0][0] == "OPTIONS"

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_options_does_not_send_body(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that options() does not include a body parameter."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.options("https://example.com/resource")

        call_args = MockRequest.send.call_args
        assert call_args[1]["body"] is None

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_put_passes_custom_headers(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that put() passes custom headers."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.put(
            "https://example.com/resource",
            headers={"Content-Type": "application/json"},
            body="{}",
        )

        call_kwargs = MockRequest.send.call_args[1]
        assert "Content-Type" in call_kwargs["headers"]

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_patch_passes_timeout(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that patch() passes timeout override."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.patch("https://example.com/resource", body="{}", timeout=30)

        call_kwargs = MockRequest.send.call_args[1]
        assert call_kwargs["timeout"] == 30

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_delete_passes_limits(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that delete() passes limits override."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        custom_limits = {"max_header_size": 16384}
        session.delete("https://example.com/resource", limits=custom_limits)

        call_kwargs = MockRequest.send.call_args[1]
        assert call_kwargs["limits"] == custom_limits


# ============================================================================
# TEST CLASS: Session _request() consolidation
# ============================================================================


class TestSessionRequestConsolidation:
    """Tests verifying all HTTP methods use the shared _request() path."""

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_all_methods_use_request_send(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that get, post, put, delete, patch, head, options all call Request.send."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        methods_with_body = [
            ("get", "GET", False),
            ("post", "POST", True),
            ("put", "PUT", True),
            ("delete", "DELETE", True),
            ("patch", "PATCH", True),
            ("head", "HEAD", False),
            ("options", "OPTIONS", False),
        ]

        for method_name, expected_method, has_body in methods_with_body:
            MockRequest.send.reset_mock()
            method_fn = getattr(session, method_name)
            if has_body:
                method_fn("https://example.com/test", body="data")
            else:
                method_fn("https://example.com/test")

            assert MockRequest.send.called, f"{method_name} did not call Request.send"
            call_args = MockRequest.send.call_args
            assert call_args[0][0] == expected_method

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_all_methods_inject_auth(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that all HTTP methods inject Basic Auth header."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.set_basic_auth("admin", "secret")

        for method_name in ["get", "post", "put", "delete", "patch", "head", "options"]:
            MockRequest.send.reset_mock()
            method_fn = getattr(session, method_name)
            if method_name in ("post", "put", "delete", "patch"):
                method_fn("https://example.com/test", body="x")
            else:
                method_fn("https://example.com/test")

            call_kwargs = MockRequest.send.call_args[1]
            assert (
                "Authorization" in call_kwargs["headers"]
            ), f"{method_name} missing Authorization header"

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_all_methods_inject_cookies(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that all HTTP methods inject Cookie header."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)
        session.cookies = {"sid": "abc"}

        for method_name in ["get", "post", "put", "delete", "patch", "head", "options"]:
            MockRequest.send.reset_mock()
            method_fn = getattr(session, method_name)
            if method_name in ("post", "put", "delete", "patch"):
                method_fn("https://example.com/test", body="x")
            else:
                method_fn("https://example.com/test")

            call_kwargs = MockRequest.send.call_args[1]
            assert (
                "Cookie" in call_kwargs["headers"]
            ), f"{method_name} missing Cookie header"


# ============================================================================
# TEST CLASS: base_url resolution
# ============================================================================


class TestBaseUrlResolution:
    """Tests for base_url resolution in Session._resolve_url()."""

    def test_resolve_url_with_base_url_and_relative_path(self) -> None:
        """Test that relative URLs are resolved against base_url."""
        s = Session(base_url="https://api.example.com")
        resolved = s._resolve_url("/users")
        assert resolved == "https://api.example.com/users"

    def test_resolve_url_with_base_url_and_absolute_url(self) -> None:
        """Test that absolute URLs are returned unchanged."""
        s = Session(base_url="https://api.example.com")
        resolved = s._resolve_url("https://other.com/data")
        assert resolved == "https://other.com/data"

    def test_resolve_url_without_base_url(self) -> None:
        """Test that URLs pass through when base_url is None."""
        s = Session()
        resolved = s._resolve_url("https://example.com/path")
        assert resolved == "https://example.com/path"

    def test_resolve_url_relative_path_joins_correctly(self) -> None:
        """Test urljoin behavior with nested base_url."""
        s = Session(base_url="https://api.example.com/v2/")
        resolved = s._resolve_url("users")
        assert resolved == "https://api.example.com/v2/users"

    def test_async_resolve_url_with_base_url(self) -> None:
        """Test base_url resolution in AsyncSession."""
        s = AsyncSession(base_url="https://api.example.com")
        resolved = s._resolve_url("/items")
        assert resolved == "https://api.example.com/items"

    def test_async_resolve_url_absolute_passthrough(self) -> None:
        """Test absolute URL passthrough in AsyncSession."""
        s = AsyncSession(base_url="https://api.example.com")
        resolved = s._resolve_url("https://other.com/data")
        assert resolved == "https://other.com/data"

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.ConnectionPool")
    def test_session_get_with_base_url_and_relative(
        self,
        MockPool: mock.Mock,
        MockRequest: mock.Mock,
        mock_response: mock.Mock,
    ) -> None:
        """Test full request flow with base_url and relative URL."""
        s = Session(base_url="https://api.example.com")

        mock_conn = mock.Mock()
        mock_pool_instance = mock.Mock()
        mock_pool_instance.get_connection.return_value = mock_conn
        s.pool = mock_pool_instance

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        s.get("/users")

        call_args = MockRequest.send.call_args
        # The resolved URL should be https://api.example.com/users
        assert call_args[0][1] == "https://api.example.com/users"


# ============================================================================
# TEST CLASS: default_timeout
# ============================================================================


class TestDefaultTimeout:
    """Tests for default_timeout fallback and override."""

    def test_default_timeout_is_five(self) -> None:
        """Test that default_timeout defaults to 5."""
        s = Session()
        assert s.default_timeout == 5

    def test_custom_default_timeout(self) -> None:
        """Test setting a custom default_timeout."""
        s = Session(default_timeout=30)
        assert s.default_timeout == 30

    def test_none_default_timeout(self) -> None:
        """Test setting default_timeout to None (no timeout)."""
        s = Session(default_timeout=None)
        assert s.default_timeout is None

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_default_timeout_used_when_not_overridden(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        mock_response: mock.Mock,
    ) -> None:
        """Test that default_timeout is used when timeout is not specified."""
        s = Session(default_timeout=15)

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        s.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        s.get("https://example.com/test")

        call_kwargs = MockRequest.send.call_args[1]
        assert call_kwargs["timeout"] == 15

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_per_request_timeout_overrides_default(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        mock_response: mock.Mock,
    ) -> None:
        """Test that per-request timeout overrides default_timeout."""
        s = Session(default_timeout=15)

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.Mock()
        mock_pool = mock.Mock()
        mock_pool.get_connection.return_value = mock_conn
        s.pool = mock_pool

        MockRequest.send.return_value = mock_response
        MockRequest.set_session_instance = mock.Mock()

        s.get("https://example.com/test", timeout=60)

        call_kwargs = MockRequest.send.call_args[1]
        assert call_kwargs["timeout"] == 60

    def test_async_default_timeout_is_five(self) -> None:
        """Test that AsyncSession default_timeout defaults to 5."""
        s = AsyncSession()
        assert s.default_timeout == 5

    def test_async_custom_default_timeout(self) -> None:
        """Test AsyncSession with custom default_timeout."""
        s = AsyncSession(default_timeout=20)
        assert s.default_timeout == 20


# ============================================================================
# TEST CLASS: AsyncSession HTTP Methods
# ============================================================================


class TestAsyncSessionHttpMethods:
    """Tests for AsyncSession put, delete, patch, head, options methods."""

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_put(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test AsyncSession.put() sends PUT method."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.AsyncMock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        await async_session.put("https://example.com/resource", body='{"name": "test"}')

        assert mock_send.called
        call_args = mock_send.call_args
        assert call_args[0][0] == "PUT"
        assert call_args[1]["body"] == '{"name": "test"}'

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_delete(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test AsyncSession.delete() sends DELETE method."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.AsyncMock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        await async_session.delete("https://example.com/resource/1")

        call_args = mock_send.call_args
        assert call_args[0][0] == "DELETE"

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_patch(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test AsyncSession.patch() sends PATCH method."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.AsyncMock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        await async_session.patch(
            "https://example.com/resource/1", body='{"status": "active"}'
        )

        call_args = mock_send.call_args
        assert call_args[0][0] == "PATCH"
        assert call_args[1]["body"] == '{"status": "active"}'

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_head(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test AsyncSession.head() sends HEAD method."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.AsyncMock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        await async_session.head("https://example.com/resource")

        call_args = mock_send.call_args
        assert call_args[0][0] == "HEAD"

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_options(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test AsyncSession.options() sends OPTIONS method."""
        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.AsyncMock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        async_session.pool = mock_pool

        mock_send.return_value = mock_response

        await async_session.options("https://example.com/resource")

        call_args = mock_send.call_args
        assert call_args[0][0] == "OPTIONS"

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_default_timeout_fallback(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        mock_response: mock.Mock,
    ) -> None:
        """Test that AsyncSession uses default_timeout when timeout is not specified."""
        s = AsyncSession(default_timeout=25)

        mock_parsed = mock.Mock()
        mock_parsed.hostname = "example.com"
        mock_parsed.port = None
        mock_parsed.scheme = "https"
        mock_urlparse.return_value = mock_parsed

        mock_conn = mock.AsyncMock()
        mock_pool = mock.AsyncMock()
        mock_pool.get_connection.return_value = mock_conn
        s.pool = mock_pool

        mock_send.return_value = mock_response

        await s.get("https://example.com/test")

        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["timeout"] == 25


# ============================================================================
# TEST CLASS: Request HTTP Methods
# ============================================================================


class TestRequestHttpMethods:
    """Tests for Request.put, delete, patch, head, options class methods."""

    @mock.patch.object(Request, "send")
    def test_request_put_delegates_to_send(self, mock_send: mock.Mock) -> None:
        """Test Request.put() delegates to send with PUT method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = Request.put("https://example.com/resource", body="data")

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[1].get("body") == "data" or call_args[0][2] == "data"
        assert result == mock_resp

    @mock.patch.object(Request, "send")
    def test_request_delete_delegates_to_send(self, mock_send: mock.Mock) -> None:
        """Test Request.delete() delegates to send with DELETE method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = Request.delete("https://example.com/resource/1")

        mock_send.assert_called_once()
        assert result == mock_resp

    @mock.patch.object(Request, "send")
    def test_request_patch_delegates_to_send(self, mock_send: mock.Mock) -> None:
        """Test Request.patch() delegates to send with PATCH method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = Request.patch("https://example.com/resource/1", body="update")

        mock_send.assert_called_once()
        assert result == mock_resp

    @mock.patch.object(Request, "send")
    def test_request_head_delegates_to_send(self, mock_send: mock.Mock) -> None:
        """Test Request.head() delegates to send with HEAD method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = Request.head("https://example.com/resource")

        mock_send.assert_called_once()
        assert result == mock_resp

    @mock.patch.object(Request, "send")
    def test_request_options_delegates_to_send(self, mock_send: mock.Mock) -> None:
        """Test Request.options() delegates to send with OPTIONS method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = Request.options("https://example.com/resource")

        mock_send.assert_called_once()
        assert result == mock_resp

    @mock.patch.object(Request, "send")
    def test_request_methods_pass_correct_method_string(
        self, mock_send: mock.Mock
    ) -> None:
        """Test that each Request method passes the correct HTTP method string."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        methods = {
            "put": "PUT",
            "delete": "DELETE",
            "patch": "PATCH",
            "head": "HEAD",
            "options": "OPTIONS",
        }

        for method_name, expected_method in methods.items():
            mock_send.reset_mock()
            method_fn = getattr(Request, method_name)
            method_fn("https://example.com/test")

            call_args = mock_send.call_args[0]
            assert (
                call_args[0] == expected_method
            ), f"Request.{method_name} should pass '{expected_method}'"


# ============================================================================
# TEST CLASS: AsyncRequest HTTP Methods
# ============================================================================


class TestAsyncRequestHttpMethods:
    """Tests for AsyncRequest.put, delete, patch, head, options class methods."""

    @pytest.mark.asyncio
    @mock.patch.object(AsyncRequest, "send", new_callable=mock.AsyncMock)
    async def test_async_request_put(self, mock_send: mock.AsyncMock) -> None:
        """Test AsyncRequest.put() delegates to send with PUT method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = await AsyncRequest.put("https://example.com/resource", body="data")

        mock_send.assert_called_once()
        assert result == mock_resp

    @pytest.mark.asyncio
    @mock.patch.object(AsyncRequest, "send", new_callable=mock.AsyncMock)
    async def test_async_request_delete(self, mock_send: mock.AsyncMock) -> None:
        """Test AsyncRequest.delete() delegates to send with DELETE method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = await AsyncRequest.delete("https://example.com/resource/1")

        mock_send.assert_called_once()
        assert result == mock_resp

    @pytest.mark.asyncio
    @mock.patch.object(AsyncRequest, "send", new_callable=mock.AsyncMock)
    async def test_async_request_patch(self, mock_send: mock.AsyncMock) -> None:
        """Test AsyncRequest.patch() delegates to send with PATCH method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = await AsyncRequest.patch(
            "https://example.com/resource/1", body="update"
        )

        mock_send.assert_called_once()
        assert result == mock_resp

    @pytest.mark.asyncio
    @mock.patch.object(AsyncRequest, "send", new_callable=mock.AsyncMock)
    async def test_async_request_head(self, mock_send: mock.AsyncMock) -> None:
        """Test AsyncRequest.head() delegates to send with HEAD method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = await AsyncRequest.head("https://example.com/resource")

        mock_send.assert_called_once()
        assert result == mock_resp

    @pytest.mark.asyncio
    @mock.patch.object(AsyncRequest, "send", new_callable=mock.AsyncMock)
    async def test_async_request_options(self, mock_send: mock.AsyncMock) -> None:
        """Test AsyncRequest.options() delegates to send with OPTIONS method."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        result = await AsyncRequest.options("https://example.com/resource")

        mock_send.assert_called_once()
        assert result == mock_resp

    @pytest.mark.asyncio
    @mock.patch.object(AsyncRequest, "send", new_callable=mock.AsyncMock)
    async def test_async_request_methods_pass_correct_method_string(
        self, mock_send: mock.AsyncMock
    ) -> None:
        """Test that each AsyncRequest method passes the correct HTTP method string."""
        mock_resp = mock.Mock(spec=Response)
        mock_send.return_value = mock_resp

        methods = {
            "put": "PUT",
            "delete": "DELETE",
            "patch": "PATCH",
            "head": "HEAD",
            "options": "OPTIONS",
        }

        for method_name, expected_method in methods.items():
            mock_send.reset_mock()
            method_fn = getattr(AsyncRequest, method_name)
            await method_fn("https://example.com/test")

            call_args = mock_send.call_args[0]
            assert (
                call_args[0] == expected_method
            ), f"AsyncRequest.{method_name} should pass '{expected_method}'"
