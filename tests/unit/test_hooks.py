"""tests/unit/test_hooks.py

Unit tests for the Hooks System (pre-request and post-response hooks)
added in v0.3.0 (Fase 2).

Test Coverage:
    - Pre-request hooks that modify method, url, and headers
    - Post-response hooks that transform response
    - Multiple hooks executed in FIFO order
    - Async hooks in AsyncSession
    - Sync hooks in AsyncSession (must also work)
    - Hook exceptions propagate to caller
    - Empty hook lists by default

Testing Strategy:
    - Mock Request.send / AsyncRequest.send to avoid real HTTP calls
    - Mock ConnectionPool to isolate session logic
    - Verify hooks receive and return correct values
"""

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
# TEST CLASS: Default State
# ============================================================================


class TestHooksDefaultState:
    """Tests for default hook state."""

    def test_session_has_empty_pre_hooks(self, session: Session) -> None:
        """Test that Session starts with empty pre-request hooks list."""
        assert session._pre_request_hooks == []

    def test_session_has_empty_post_hooks(self, session: Session) -> None:
        """Test that Session starts with empty post-response hooks list."""
        assert session._post_response_hooks == []

    def test_async_session_has_empty_pre_hooks(
        self, async_session: AsyncSession
    ) -> None:
        """Test that AsyncSession starts with empty pre-request hooks list."""
        assert async_session._pre_request_hooks == []

    def test_async_session_has_empty_post_hooks(
        self, async_session: AsyncSession
    ) -> None:
        """Test that AsyncSession starts with empty post-response hooks list."""
        assert async_session._post_response_hooks == []


# ============================================================================
# TEST CLASS: Pre-Request Hooks (Sync)
# ============================================================================


class TestPreRequestHooksSync:
    """Tests for sync Session pre-request hooks."""

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_pre_hook_modifies_headers(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test pre-request hook that adds a custom header."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        def add_custom_header(method, url, headers):
            headers["X-Custom"] = "hook-value"
            return method, url, headers

        session.add_pre_request_hook(add_custom_header)
        session.get("https://example.com/test")

        call_kwargs = MockRequest.send.call_args[1]
        assert call_kwargs["headers"]["X-Custom"] == "hook-value"

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_pre_hook_modifies_method(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test pre-request hook that changes the HTTP method."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        def change_method(method, url, headers):
            return "POST", url, headers

        session.add_pre_request_hook(change_method)
        session.get("https://example.com/test")

        call_args = MockRequest.send.call_args[0]
        assert call_args[0] == "POST"

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_pre_hook_modifies_url(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test pre-request hook that modifies the URL."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        def rewrite_url(method, url, headers):
            return method, url + "?debug=true", headers

        session.add_pre_request_hook(rewrite_url)
        session.get("https://example.com/test")

        call_args = MockRequest.send.call_args[0]
        assert "?debug=true" in call_args[1]

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_multiple_pre_hooks_fifo_order(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that multiple pre-hooks execute in FIFO order."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        execution_order: list = []

        def hook_a(method, url, headers):
            execution_order.append("A")
            headers["X-Order"] = "A"
            return method, url, headers

        def hook_b(method, url, headers):
            execution_order.append("B")
            headers["X-Order"] = "B"
            return method, url, headers

        session.add_pre_request_hook(hook_a)
        session.add_pre_request_hook(hook_b)
        session.get("https://example.com/test")

        assert execution_order == ["A", "B"]
        # Last hook wins for the header value
        call_kwargs = MockRequest.send.call_args[1]
        assert call_kwargs["headers"]["X-Order"] == "B"


# ============================================================================
# TEST CLASS: Post-Response Hooks (Sync)
# ============================================================================


class TestPostResponseHooksSync:
    """Tests for sync Session post-response hooks."""

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_post_hook_transforms_response(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test post-response hook that transforms the response."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        transformed = mock.Mock(spec=Response)
        transformed.headers = Headers()
        transformed.status_code = 201

        def transform_response(response):
            return transformed

        session.add_post_response_hook(transform_response)
        result = session.get("https://example.com/test")

        assert result == transformed

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_multiple_post_hooks_fifo_order(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that multiple post-hooks execute in FIFO order."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        execution_order: list = []

        def hook_a(response):
            execution_order.append("A")
            return response

        def hook_b(response):
            execution_order.append("B")
            return response

        session.add_post_response_hook(hook_a)
        session.add_post_response_hook(hook_b)
        session.get("https://example.com/test")

        assert execution_order == ["A", "B"]

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_post_hook_receives_response(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that post-hook receives the actual response object."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        received_responses: list = []

        def capture_response(response):
            received_responses.append(response)
            return response

        session.add_post_response_hook(capture_response)
        session.get("https://example.com/test")

        assert len(received_responses) == 1
        assert received_responses[0] == mock_response


# ============================================================================
# TEST CLASS: Hook Exception Propagation
# ============================================================================


class TestHookExceptions:
    """Tests for hook exception propagation."""

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_pre_hook_exception_propagates(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that exceptions in pre-request hooks propagate."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        def failing_hook(method, url, headers):
            raise RuntimeError("hook failed")

        session.add_pre_request_hook(failing_hook)

        with pytest.raises(RuntimeError, match="hook failed"):
            session.get("https://example.com/test")

    @mock.patch("reqivo.client.session.Request")
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    def test_post_hook_exception_propagates(
        self,
        mock_urlparse: mock.Mock,
        MockRequest: mock.Mock,
        session: Session,
        mock_response: mock.Mock,
    ) -> None:
        """Test that exceptions in post-response hooks propagate."""
        _setup_session_mocks(session, mock_urlparse, MockRequest, mock_response)

        def failing_hook(response):
            raise ValueError("post hook failed")

        session.add_post_response_hook(failing_hook)

        with pytest.raises(ValueError, match="post hook failed"):
            session.get("https://example.com/test")


# ============================================================================
# TEST CLASS: AsyncSession Hooks
# ============================================================================


class TestAsyncSessionHooks:
    """Tests for AsyncSession hooks (sync and async variants)."""

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_pre_hook_sync(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test sync pre-request hook in AsyncSession."""
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

        def add_header(method, url, headers):
            headers["X-Sync-Hook"] = "yes"
            return method, url, headers

        async_session.add_pre_request_hook(add_header)
        await async_session.get("https://example.com/test")

        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["headers"]["X-Sync-Hook"] == "yes"

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_pre_hook_async(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test async pre-request hook in AsyncSession."""
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

        async def async_add_header(method, url, headers):
            headers["X-Async-Hook"] = "yes"
            return method, url, headers

        async_session.add_pre_request_hook(async_add_header)
        await async_session.get("https://example.com/test")

        call_kwargs = mock_send.call_args[1]
        assert call_kwargs["headers"]["X-Async-Hook"] == "yes"

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_post_hook_sync(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test sync post-response hook in AsyncSession."""
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

        received: list = []

        def capture(response):
            received.append(response)
            return response

        async_session.add_post_response_hook(capture)
        await async_session.get("https://example.com/test")

        assert len(received) == 1

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_post_hook_async(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test async post-response hook in AsyncSession."""
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

        transformed = mock.Mock(spec=Response)
        transformed.headers = Headers()

        async def async_transform(response):
            return transformed

        async_session.add_post_response_hook(async_transform)
        result = await async_session.get("https://example.com/test")

        assert result == transformed

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_hook_exception_propagates(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test that async hook exceptions propagate."""
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

        async def failing_hook(method, url, headers):
            raise RuntimeError("async hook failed")

        async_session.add_pre_request_hook(failing_hook)

        with pytest.raises(RuntimeError, match="async hook failed"):
            await async_session.get("https://example.com/test")

    @pytest.mark.asyncio
    @mock.patch("reqivo.client.session.AsyncRequest.send", new_callable=mock.AsyncMock)
    @mock.patch("reqivo.client.session.urllib.parse.urlparse")
    async def test_async_multiple_hooks_fifo(
        self,
        mock_urlparse: mock.Mock,
        mock_send: mock.AsyncMock,
        async_session: AsyncSession,
        mock_response: mock.Mock,
    ) -> None:
        """Test that multiple hooks in AsyncSession execute in FIFO order."""
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

        order: list = []

        def sync_hook(method, url, headers):
            order.append("sync")
            return method, url, headers

        async def async_hook(method, url, headers):
            order.append("async")
            return method, url, headers

        async_session.add_pre_request_hook(sync_hook)
        async_session.add_pre_request_hook(async_hook)
        await async_session.get("https://example.com/test")

        assert order == ["sync", "async"]


# ============================================================================
# TEST CLASS: Hook Registration
# ============================================================================


class TestHookRegistration:
    """Tests for hook registration mechanics."""

    def test_add_pre_request_hook(self, session: Session) -> None:
        """Test adding a pre-request hook."""

        def my_hook(method, url, headers):
            return method, url, headers

        session.add_pre_request_hook(my_hook)
        assert len(session._pre_request_hooks) == 1
        assert session._pre_request_hooks[0] is my_hook

    def test_add_post_response_hook(self, session: Session) -> None:
        """Test adding a post-response hook."""

        def my_hook(response):
            return response

        session.add_post_response_hook(my_hook)
        assert len(session._post_response_hooks) == 1
        assert session._post_response_hooks[0] is my_hook

    def test_add_multiple_hooks(self, session: Session) -> None:
        """Test adding multiple hooks."""
        hooks = [lambda m, u, h: (m, u, h) for _ in range(3)]
        for hook in hooks:
            session.add_pre_request_hook(hook)
        assert len(session._pre_request_hooks) == 3

    def test_async_add_pre_request_hook(self, async_session: AsyncSession) -> None:
        """Test adding a pre-request hook to AsyncSession."""

        def my_hook(method, url, headers):
            return method, url, headers

        async_session.add_pre_request_hook(my_hook)
        assert len(async_session._pre_request_hooks) == 1

    def test_async_add_post_response_hook(self, async_session: AsyncSession) -> None:
        """Test adding a post-response hook to AsyncSession."""

        def my_hook(response):
            return response

        async_session.add_post_response_hook(my_hook)
        assert len(async_session._post_response_hooks) == 1
