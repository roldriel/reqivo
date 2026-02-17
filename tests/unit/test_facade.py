"""tests/unit/test_facade.py

Unit tests for the Reqivo and AsyncReqivo facade classes (v0.3.0, Fase 5).

Test Coverage:
    - HTTP method delegation (get, post, put, delete, patch, head, options)
    - Auth fluent interface (basic_auth, bearer_token) with chaining
    - Hooks fluent interface (on_request, on_response) with chaining
    - WebSocket creation with merged headers
    - Context manager (sync and async)
    - Constructor parameters (base_url, timeout, headers, limits)
    - Async variants of all the above

Testing Strategy:
    - Mock Session/AsyncSession to verify delegation
    - Verify fluent chaining returns self
    - Verify constructor wiring to Session
"""

from unittest import mock

import pytest

from reqivo.client.facade import AsyncReqivo, Reqivo
from reqivo.client.response import Response
from reqivo.client.session import AsyncSession, Session
from reqivo.client.websocket import AsyncWebSocket, WebSocket

# ============================================================================
# TEST CLASS: Reqivo Constructor
# ============================================================================


class TestReqivoConstructor:
    """Tests for Reqivo constructor parameter wiring."""

    def test_default_constructor(self) -> None:
        """Test Reqivo with default parameters."""
        r = Reqivo()
        assert isinstance(r._session, Session)
        assert r._session.base_url is None
        assert r._session.default_timeout == 5
        assert r._session.limits is None

    def test_base_url(self) -> None:
        """Test base_url is passed to Session."""
        r = Reqivo(base_url="https://api.example.com")
        assert r._session.base_url == "https://api.example.com"

    def test_timeout(self) -> None:
        """Test timeout is passed as default_timeout."""
        r = Reqivo(timeout=30)
        assert r._session.default_timeout == 30

    def test_headers(self) -> None:
        """Test initial headers are set on Session."""
        r = Reqivo(headers={"X-Custom": "value"})
        assert r._session.headers["X-Custom"] == "value"

    def test_limits(self) -> None:
        """Test limits are passed to Session."""
        limits = {"max_header_size": 4096}
        r = Reqivo(limits=limits)
        assert r._session.limits == limits

    def test_no_headers_does_not_modify_session(self) -> None:
        """Test that None headers leave session headers empty."""
        r = Reqivo()
        assert r._session.headers == {}


# ============================================================================
# TEST CLASS: Reqivo HTTP Methods
# ============================================================================


class TestReqivoHTTPMethods:
    """Tests for HTTP method delegation to Session."""

    @mock.patch.object(Session, "_request")
    def test_get(self, mock_request: mock.Mock) -> None:
        """Test get delegates to Session."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = Reqivo()
        r.get("https://example.com/", headers={"X": "1"}, timeout=10)
        mock_request.assert_called_once_with(
            "GET",
            "https://example.com/",
            headers={"X": "1"},
            timeout=10,
            limits=None,
        )

    @mock.patch.object(Session, "_request")
    def test_post(self, mock_request: mock.Mock) -> None:
        """Test post delegates to Session."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = Reqivo()
        r.post("https://example.com/", body="data")
        mock_request.assert_called_once_with(
            "POST",
            "https://example.com/",
            headers=None,
            body="data",
            timeout=None,
            limits=None,
        )

    @mock.patch.object(Session, "_request")
    def test_put(self, mock_request: mock.Mock) -> None:
        """Test put delegates to Session."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = Reqivo()
        r.put("https://example.com/", body=b"bytes")
        mock_request.assert_called_once_with(
            "PUT",
            "https://example.com/",
            headers=None,
            body=b"bytes",
            timeout=None,
            limits=None,
        )

    @mock.patch.object(Session, "_request")
    def test_delete(self, mock_request: mock.Mock) -> None:
        """Test delete delegates to Session."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = Reqivo()
        r.delete("https://example.com/")
        mock_request.assert_called_once_with(
            "DELETE",
            "https://example.com/",
            headers=None,
            body=None,
            timeout=None,
            limits=None,
        )

    @mock.patch.object(Session, "_request")
    def test_patch(self, mock_request: mock.Mock) -> None:
        """Test patch delegates to Session."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = Reqivo()
        r.patch("https://example.com/", body="update")
        mock_request.assert_called_once_with(
            "PATCH",
            "https://example.com/",
            headers=None,
            body="update",
            timeout=None,
            limits=None,
        )

    @mock.patch.object(Session, "_request")
    def test_head(self, mock_request: mock.Mock) -> None:
        """Test head delegates to Session."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = Reqivo()
        r.head("https://example.com/")
        mock_request.assert_called_once_with(
            "HEAD",
            "https://example.com/",
            headers=None,
            timeout=None,
            limits=None,
        )

    @mock.patch.object(Session, "_request")
    def test_options(self, mock_request: mock.Mock) -> None:
        """Test options delegates to Session."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = Reqivo()
        r.options("https://example.com/")
        mock_request.assert_called_once_with(
            "OPTIONS",
            "https://example.com/",
            headers=None,
            timeout=None,
            limits=None,
        )


# ============================================================================
# TEST CLASS: Reqivo Auth (Fluent)
# ============================================================================


class TestReqivoAuth:
    """Tests for fluent auth interface."""

    def test_basic_auth_returns_self(self) -> None:
        """Test basic_auth returns self for chaining."""
        r = Reqivo()
        result = r.basic_auth("user", "pass")
        assert result is r

    def test_basic_auth_sets_session(self) -> None:
        """Test basic_auth delegates to Session."""
        r = Reqivo()
        r.basic_auth("user", "pass")
        assert r._session._basic_auth == ("user", "pass")

    def test_bearer_token_returns_self(self) -> None:
        """Test bearer_token returns self for chaining."""
        r = Reqivo()
        result = r.bearer_token("my-token")
        assert result is r

    def test_bearer_token_sets_session(self) -> None:
        """Test bearer_token delegates to Session."""
        r = Reqivo()
        r.bearer_token("my-token")
        assert r._session._bearer_token == "my-token"

    def test_chaining(self) -> None:
        """Test fluent chaining: basic_auth -> bearer_token."""
        r = Reqivo()
        result = r.basic_auth("u", "p").bearer_token("tok")
        assert result is r
        assert r._session._bearer_token == "tok"
        # basic_auth should be cleared by bearer_token
        assert r._session._basic_auth is None


# ============================================================================
# TEST CLASS: Reqivo Hooks (Fluent)
# ============================================================================


class TestReqivoHooks:
    """Tests for fluent hooks interface."""

    def test_on_request_returns_self(self) -> None:
        """Test on_request returns self for chaining."""
        r = Reqivo()
        hook = lambda m, u, h: (m, u, h)
        result = r.on_request(hook)
        assert result is r

    def test_on_request_registers_hook(self) -> None:
        """Test on_request adds hook to session."""
        r = Reqivo()
        hook = lambda m, u, h: (m, u, h)
        r.on_request(hook)
        assert r._session._pre_request_hooks == [hook]

    def test_on_response_returns_self(self) -> None:
        """Test on_response returns self for chaining."""
        r = Reqivo()
        hook = lambda resp: resp
        result = r.on_response(hook)
        assert result is r

    def test_on_response_registers_hook(self) -> None:
        """Test on_response adds hook to session."""
        r = Reqivo()
        hook = lambda resp: resp
        r.on_response(hook)
        assert r._session._post_response_hooks == [hook]

    def test_full_chaining(self) -> None:
        """Test chaining auth + hooks."""
        pre = lambda m, u, h: (m, u, h)
        post = lambda resp: resp
        r = (
            Reqivo(base_url="https://api.example.com")
            .basic_auth("user", "pass")
            .on_request(pre)
            .on_response(post)
        )
        assert isinstance(r, Reqivo)
        assert r._session._basic_auth == ("user", "pass")
        assert len(r._session._pre_request_hooks) == 1
        assert len(r._session._post_response_hooks) == 1


# ============================================================================
# TEST CLASS: Reqivo WebSocket
# ============================================================================


class TestReqivoWebSocket:
    """Tests for WebSocket creation via facade."""

    def test_websocket_returns_instance(self) -> None:
        """Test websocket returns a WebSocket instance."""
        r = Reqivo()
        ws = r.websocket("ws://example.com/")
        assert isinstance(ws, WebSocket)
        assert ws.url == "ws://example.com/"

    def test_websocket_merges_headers(self) -> None:
        """Test websocket merges session headers with request headers."""
        r = Reqivo(headers={"Authorization": "Bearer tok"})
        ws = r.websocket("ws://example.com/", headers={"X-Custom": "val"})
        assert ws.headers["Authorization"] == "Bearer tok"
        assert ws.headers["X-Custom"] == "val"

    def test_websocket_passes_timeout(self) -> None:
        """Test websocket passes timeout."""
        r = Reqivo()
        ws = r.websocket("ws://example.com/", timeout=30)
        assert ws.timeout == 30

    def test_websocket_passes_subprotocols(self) -> None:
        """Test websocket passes subprotocols."""
        r = Reqivo()
        ws = r.websocket("ws://example.com/", subprotocols=["graphql-ws"])
        assert ws.subprotocols == ["graphql-ws"]


# ============================================================================
# TEST CLASS: Reqivo Lifecycle
# ============================================================================


class TestReqivoLifecycle:
    """Tests for context manager and close."""

    @mock.patch.object(Session, "close")
    def test_close(self, mock_close: mock.Mock) -> None:
        """Test close delegates to Session."""
        r = Reqivo()
        r.close()
        mock_close.assert_called_once()

    @mock.patch.object(Session, "close")
    def test_context_manager(self, mock_close: mock.Mock) -> None:
        """Test context manager calls close on exit."""
        with Reqivo() as r:
            assert isinstance(r, Reqivo)
        mock_close.assert_called_once()

    @mock.patch.object(Session, "close")
    def test_context_manager_on_exception(self, mock_close: mock.Mock) -> None:
        """Test context manager calls close even on exception."""
        with pytest.raises(RuntimeError):
            with Reqivo():
                raise RuntimeError("test error")
        mock_close.assert_called_once()


# ============================================================================
# TEST CLASS: AsyncReqivo Constructor
# ============================================================================


class TestAsyncReqivoConstructor:
    """Tests for AsyncReqivo constructor."""

    def test_default_constructor(self) -> None:
        """Test AsyncReqivo with default parameters."""
        r = AsyncReqivo()
        assert isinstance(r._session, AsyncSession)
        assert r._session.base_url is None
        assert r._session.default_timeout == 5

    def test_base_url(self) -> None:
        """Test base_url is passed to AsyncSession."""
        r = AsyncReqivo(base_url="https://api.example.com")
        assert r._session.base_url == "https://api.example.com"

    def test_timeout(self) -> None:
        """Test timeout is passed as default_timeout."""
        r = AsyncReqivo(timeout=15)
        assert r._session.default_timeout == 15

    def test_headers(self) -> None:
        """Test initial headers are set on AsyncSession."""
        r = AsyncReqivo(headers={"Accept": "application/json"})
        assert r._session.headers["Accept"] == "application/json"

    def test_limits(self) -> None:
        """Test limits are passed to AsyncSession."""
        limits = {"max_header_size": 8192}
        r = AsyncReqivo(limits=limits)
        assert r._session.limits == limits


# ============================================================================
# TEST CLASS: AsyncReqivo HTTP Methods
# ============================================================================


class TestAsyncReqivoHTTPMethods:
    """Tests for async HTTP method delegation."""

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "_request", new_callable=mock.AsyncMock)
    async def test_get(self, mock_request: mock.AsyncMock) -> None:
        """Test async get delegates to AsyncSession."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = AsyncReqivo()
        await r.get("https://example.com/")
        mock_request.assert_called_once_with(
            "GET",
            "https://example.com/",
            headers=None,
            timeout=None,
            limits=None,
        )

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "_request", new_callable=mock.AsyncMock)
    async def test_post(self, mock_request: mock.AsyncMock) -> None:
        """Test async post delegates to AsyncSession."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = AsyncReqivo()
        await r.post("https://example.com/", body="data")
        mock_request.assert_called_once_with(
            "POST",
            "https://example.com/",
            headers=None,
            body="data",
            timeout=None,
            limits=None,
        )

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "_request", new_callable=mock.AsyncMock)
    async def test_put(self, mock_request: mock.AsyncMock) -> None:
        """Test async put delegates to AsyncSession."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = AsyncReqivo()
        await r.put("https://example.com/", body=b"bytes")
        mock_request.assert_called_once_with(
            "PUT",
            "https://example.com/",
            headers=None,
            body=b"bytes",
            timeout=None,
            limits=None,
        )

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "_request", new_callable=mock.AsyncMock)
    async def test_delete(self, mock_request: mock.AsyncMock) -> None:
        """Test async delete delegates to AsyncSession."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = AsyncReqivo()
        await r.delete("https://example.com/")
        mock_request.assert_called_once_with(
            "DELETE",
            "https://example.com/",
            headers=None,
            body=None,
            timeout=None,
            limits=None,
        )

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "_request", new_callable=mock.AsyncMock)
    async def test_patch(self, mock_request: mock.AsyncMock) -> None:
        """Test async patch delegates to AsyncSession."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = AsyncReqivo()
        await r.patch("https://example.com/", body="update")
        mock_request.assert_called_once_with(
            "PATCH",
            "https://example.com/",
            headers=None,
            body="update",
            timeout=None,
            limits=None,
        )

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "_request", new_callable=mock.AsyncMock)
    async def test_head(self, mock_request: mock.AsyncMock) -> None:
        """Test async head delegates to AsyncSession."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = AsyncReqivo()
        await r.head("https://example.com/")
        mock_request.assert_called_once_with(
            "HEAD",
            "https://example.com/",
            headers=None,
            timeout=None,
            limits=None,
        )

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "_request", new_callable=mock.AsyncMock)
    async def test_options(self, mock_request: mock.AsyncMock) -> None:
        """Test async options delegates to AsyncSession."""
        mock_request.return_value = mock.Mock(spec=Response)
        r = AsyncReqivo()
        await r.options("https://example.com/")
        mock_request.assert_called_once_with(
            "OPTIONS",
            "https://example.com/",
            headers=None,
            timeout=None,
            limits=None,
        )


# ============================================================================
# TEST CLASS: AsyncReqivo Auth (Fluent)
# ============================================================================


class TestAsyncReqivoAuth:
    """Tests for async fluent auth interface."""

    def test_basic_auth_returns_self(self) -> None:
        """Test basic_auth returns self for chaining."""
        r = AsyncReqivo()
        result = r.basic_auth("user", "pass")
        assert result is r

    def test_bearer_token_returns_self(self) -> None:
        """Test bearer_token returns self for chaining."""
        r = AsyncReqivo()
        result = r.bearer_token("tok")
        assert result is r


# ============================================================================
# TEST CLASS: AsyncReqivo Hooks (Fluent)
# ============================================================================


class TestAsyncReqivoHooks:
    """Tests for async fluent hooks interface."""

    def test_on_request_returns_self(self) -> None:
        """Test on_request returns self for chaining."""
        r = AsyncReqivo()
        result = r.on_request(lambda m, u, h: (m, u, h))
        assert result is r

    def test_on_response_returns_self(self) -> None:
        """Test on_response returns self for chaining."""
        r = AsyncReqivo()
        result = r.on_response(lambda resp: resp)
        assert result is r


# ============================================================================
# TEST CLASS: AsyncReqivo WebSocket
# ============================================================================


class TestAsyncReqivoWebSocket:
    """Tests for async WebSocket creation via facade."""

    def test_websocket_returns_async_instance(self) -> None:
        """Test websocket returns an AsyncWebSocket instance."""
        r = AsyncReqivo()
        ws = r.websocket("ws://example.com/")
        assert isinstance(ws, AsyncWebSocket)

    def test_websocket_merges_headers(self) -> None:
        """Test websocket merges session headers."""
        r = AsyncReqivo(headers={"Authorization": "Bearer tok"})
        ws = r.websocket("ws://example.com/", headers={"X-Custom": "val"})
        assert ws.headers["Authorization"] == "Bearer tok"
        assert ws.headers["X-Custom"] == "val"


# ============================================================================
# TEST CLASS: AsyncReqivo Lifecycle
# ============================================================================


class TestAsyncReqivoLifecycle:
    """Tests for async context manager and close."""

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "close", new_callable=mock.AsyncMock)
    async def test_close(self, mock_close: mock.AsyncMock) -> None:
        """Test close delegates to AsyncSession."""
        r = AsyncReqivo()
        await r.close()
        mock_close.assert_called_once()

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "close", new_callable=mock.AsyncMock)
    async def test_async_context_manager(self, mock_close: mock.AsyncMock) -> None:
        """Test async context manager calls close on exit."""
        async with AsyncReqivo() as r:
            assert isinstance(r, AsyncReqivo)
        mock_close.assert_called_once()

    @pytest.mark.asyncio
    @mock.patch.object(AsyncSession, "close", new_callable=mock.AsyncMock)
    async def test_async_context_manager_on_exception(
        self, mock_close: mock.AsyncMock
    ) -> None:
        """Test async context manager calls close even on exception."""
        with pytest.raises(RuntimeError):
            async with AsyncReqivo():
                raise RuntimeError("test error")
        mock_close.assert_called_once()
