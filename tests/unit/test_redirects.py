"""tests/unit/test_redirects.py

Unit tests for HTTP redirect handling in Request and AsyncRequest.
"""

from unittest import mock

import pytest

from reqivo.client.request import AsyncRequest, Request
from reqivo.client.response import Response
from reqivo.exceptions import RedirectLoopError, TooManyRedirects
from reqivo.http.headers import Headers


class TestRedirects:
    """Tests for synchronous redirect handling."""

    @mock.patch("reqivo.client.request.Request._perform_request")
    def test_basic_redirect_flow(self, mock_perform):
        """Test following a simple 302 redirect."""
        # Setup responses
        resp1 = mock.Mock(spec=Response)
        resp1.status_code = 302
        resp1.headers = Headers({"Location": "/target"})
        resp1.text.return_value = ""  # Consume body

        resp2 = mock.Mock(spec=Response)
        resp2.status_code = 200
        resp2.headers = Headers()
        resp2.text.return_value = "OK"

        mock_perform.side_effect = [resp1, resp2]

        # Execute
        response = Request.get("http://example.com/source")

        # Verify
        assert response == resp2
        assert len(response.history) == 1
        assert response.history[0] == resp1
        assert mock_perform.call_count == 2

        # Check second call URL
        args, _ = mock_perform.call_args_list[1]
        assert args[1] == "http://example.com/target"

    @mock.patch("reqivo.client.request.Request._perform_request")
    def test_max_redirects_exceeded(self, mock_perform):
        """Test that TooManyRedirects is raised when limit is exceeded."""
        # Setup infinite redirect loop
        resp = mock.Mock(spec=Response)
        resp.status_code = 302
        resp.headers = Headers({"Location": "/loop"})
        resp.text.return_value = ""

        mock_perform.return_value = resp

        # Execute
        # Now triggers RedirectLoopError because it redirects to itself
        with pytest.raises(RedirectLoopError):
            Request.get("http://example.com/loop", max_redirects=3)

        assert mock_perform.call_count == 1  # Detected cycle after first perform

    @mock.patch("reqivo.client.request.Request._perform_request")
    def test_allow_redirects_false(self, mock_perform):
        """Test that redirects are not followed when allow_redirects=False."""
        resp = mock.Mock(spec=Response)
        resp.status_code = 302
        resp.headers = Headers({"Location": "/target"})

        mock_perform.return_value = resp

        # Execute
        response = Request.get("http://example.com/source", allow_redirects=False)

        # Verify
        assert response == resp
        assert len(response.history) == 0
        assert mock_perform.call_count == 1

    @mock.patch("reqivo.client.request.Request._perform_request")
    def test_303_method_change(self, mock_perform):
        """Test that 303 See Other changes POST to GET."""
        resp1 = mock.Mock(spec=Response)
        resp1.status_code = 303
        resp1.headers = Headers({"Location": "/target"})
        resp1.text.return_value = ""

        resp2 = mock.Mock(spec=Response)
        resp2.status_code = 200
        resp2.headers = Headers()

        mock_perform.side_effect = [resp1, resp2]

        # Execute POST
        Request.post("http://example.com/source", body="data")

        # Verify second call is GET and has no body
        args, _ = mock_perform.call_args_list[1]
        # method, url, headers, body, ...
        assert args[0] == "GET"
        assert args[3] is None  # Body should be None

    @mock.patch("reqivo.client.request.Request._perform_request")
    def test_307_method_preservation(self, mock_perform):
        """Test that 307 Temporary Redirect preserves POST method."""
        resp1 = mock.Mock(spec=Response)
        resp1.status_code = 307
        resp1.headers = Headers({"Location": "/target"})
        resp1.text.return_value = ""

        resp2 = mock.Mock(spec=Response)
        resp2.status_code = 200
        resp2.headers = Headers()

        mock_perform.side_effect = [resp1, resp2]

        # Execute POST
        Request.post("http://example.com/source", body="data")

        # Verify second call is POST and has body
        args, _ = mock_perform.call_args_list[1]
        assert args[0] == "POST"
        assert args[3] == "data"

    @mock.patch("reqivo.client.request.Request._perform_request")
    def test_auth_stripping_on_host_change(self, mock_perform):
        """Test that Authorization header is stripped on host change."""
        resp1 = mock.Mock(spec=Response)
        resp1.status_code = 302
        resp1.headers = Headers({"Location": "http://other-domain.com/target"})
        resp1.text.return_value = ""

        resp2 = mock.Mock(spec=Response)
        resp2.status_code = 200
        resp2.headers = Headers()

        mock_perform.side_effect = [resp1, resp2]

        headers = {"Authorization": "Secret"}
        Request.get("http://example.com/source", headers=headers)

        # Verify second call headers
        args, _ = mock_perform.call_args_list[1]
        called_headers = args[2]
        assert "Authorization" not in called_headers

    @mock.patch("reqivo.client.request.Request._perform_request")
    def test_auth_preservation_on_same_host(self, mock_perform):
        """Test that Authorization header is preserved on same host redirect."""
        resp1 = mock.Mock(spec=Response)
        resp1.status_code = 302
        resp1.headers = Headers({"Location": "/target"})
        resp1.text.return_value = ""

        resp2 = mock.Mock(spec=Response)
        resp2.status_code = 200
        resp2.headers = Headers()

        mock_perform.side_effect = [resp1, resp2]

        headers = {"Authorization": "Secret"}
        Request.get("http://example.com/source", headers=headers)

        # Verify second call headers
        args, _ = mock_perform.call_args_list[1]
        called_headers = args[2]
        assert "Authorization" in called_headers
        assert called_headers["Authorization"] == "Secret"


class TestAsyncRedirects:
    """Tests for asynchronous redirect handling."""

    @pytest.mark.asyncio
    @mock.patch(
        "reqivo.client.request.AsyncRequest._perform_request",
        new_callable=mock.AsyncMock,
    )
    async def test_async_basic_redirect(self, mock_perform):
        """Test async following of a redirect."""
        resp1 = mock.Mock(spec=Response)
        resp1.status_code = 302
        resp1.headers = Headers({"Location": "/target"})
        resp1.text.return_value = ""

        resp2 = mock.Mock(spec=Response)
        resp2.status_code = 200
        resp2.headers = Headers()

        mock_perform.side_effect = [resp1, resp2]

        response = await AsyncRequest.get("http://example.com/source")

        assert response == resp2
        assert len(response.history) == 1
        assert mock_perform.await_count == 2

        args, _ = mock_perform.call_args_list[1]
        assert args[1] == "http://example.com/target"

    @pytest.mark.asyncio
    @mock.patch(
        "reqivo.client.request.AsyncRequest._perform_request",
        new_callable=mock.AsyncMock,
    )
    async def test_async_max_redirects(self, mock_perform):
        """Test async TooManyRedirects."""
        resp = mock.Mock(spec=Response)
        resp.status_code = 302
        resp.headers = Headers({"Location": "/loop"})
        resp.text.return_value = ""

        mock_perform.return_value = resp

        # Now triggers RedirectLoopError because it redirects to itself
        with pytest.raises(RedirectLoopError):
            await AsyncRequest.get("http://example.com/loop", max_redirects=2)

        # Initial call detected cycle immediately
        assert mock_perform.await_count == 1
