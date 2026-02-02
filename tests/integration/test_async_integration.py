"""tests/integration/test_async_integration.py

Integration tests for async HTTP client functionality.

These tests validate async operations using a local HTTP test server.
"""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from reqivo import AsyncSession


class AsyncTestHTTPRequestHandler(BaseHTTPRequestHandler):
    """Simple HTTP server for async integration testing."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress server logs during testing."""
        pass

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/async-json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {"message": "Async response", "type": "async"}
            self.wfile.write(json.dumps(response_data).encode())

        elif self.path == "/slow":
            # Simulate slow response
            import time

            time.sleep(0.1)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Slow response")

        elif self.path == "/set-cookie":
            self.send_response(200)
            self.send_header("Set-Cookie", "async_session=async123; Path=/")
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Async cookie set")

        elif self.path == "/check-cookie":
            cookie_header = self.headers.get("Cookie", "")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {"cookie": cookie_header}
            self.wfile.write(json.dumps(response_data).encode())

        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Async OK")

    def do_POST(self) -> None:
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        if self.path == "/async-echo":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {
                "received": post_data.decode("utf-8"),
                "async": True,
            }
            self.wfile.write(json.dumps(response_data).encode())

        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Async POST received")


class TestAsyncHTTPIntegration:
    """Integration tests for async HTTP client operations."""

    @classmethod
    def setup_class(cls):
        """Start the test HTTP server."""
        cls.server = HTTPServer(("localhost", 0), AsyncTestHTTPRequestHandler)
        cls.port = cls.server.server_port
        cls.base_url = f"http://localhost:{cls.port}"

        # Start server in background thread
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

    @classmethod
    def teardown_class(cls):
        """Stop the test HTTP server."""
        cls.server.shutdown()
        cls.server.server_close()

    @pytest.mark.asyncio
    async def test_async_simple_get(self):
        """Test basic async GET request."""
        session = AsyncSession()
        try:
            response = await session.get(f"{self.base_url}/")
            assert response.status_code == 200
            assert response.text() == "Async OK"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_async_get_json(self):
        """Test async GET request with JSON response."""
        session = AsyncSession()
        try:
            response = await session.get(f"{self.base_url}/async-json")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Async response"
            assert data["type"] == "async"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_async_post_request(self):
        """Test async POST request."""
        session = AsyncSession()
        try:
            test_data = "async test payload"
            response = await session.post(f"{self.base_url}/async-echo", body=test_data)
            assert response.status_code == 200
            data = response.json()
            assert data["received"] == test_data
            assert data["async"] is True
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_async_session_cookies(self):
        """Test async session cookie management."""
        session = AsyncSession()
        try:
            # Set cookie
            response1 = await session.get(f"{self.base_url}/set-cookie")
            assert response1.status_code == 200

            # Verify cookie is stored
            assert "async_session" in session.cookies
            assert session.cookies["async_session"] == "async123"

            # Verify cookie is sent in subsequent request
            response2 = await session.get(f"{self.base_url}/check-cookie")
            assert response2.status_code == 200
            data = response2.json()
            assert "async_session=async123" in data["cookie"]
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_async_basic_auth(self):
        """Test async basic authentication."""
        session = AsyncSession()
        session.set_basic_auth("async_user", "async_pass")
        try:
            # Basic auth should be sent in Authorization header
            response = await session.get(f"{self.base_url}/")
            assert response.status_code == 200
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_async_bearer_token(self):
        """Test async bearer token authentication."""
        session = AsyncSession()
        session.set_bearer_token("async_token_xyz")
        try:
            # Bearer token should be sent in Authorization header
            response = await session.get(f"{self.base_url}/")
            assert response.status_code == 200
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_async_concurrent_requests(self):
        """Test multiple concurrent async requests."""
        session = AsyncSession()
        try:
            # Make multiple concurrent requests
            tasks = [
                session.get(f"{self.base_url}/async-json"),
                session.get(f"{self.base_url}/"),
                session.get(f"{self.base_url}/async-json"),
            ]

            responses = await asyncio.gather(*tasks)

            # All requests should succeed
            assert all(r.status_code == 200 for r in responses)
            assert responses[0].json()["type"] == "async"
            assert responses[1].text() == "Async OK"
            assert responses[2].json()["type"] == "async"
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_async_connection_reuse(self):
        """Test async connection pooling and reuse."""
        session = AsyncSession()
        try:
            # Make sequential requests
            response1 = await session.get(f"{self.base_url}/")
            assert response1.status_code == 200

            response2 = await session.get(f"{self.base_url}/async-json")
            assert response2.status_code == 200

            response3 = await session.get(f"{self.base_url}/")
            assert response3.status_code == 200

            # Connection pool should handle all requests efficiently
        finally:
            await session.close()

    @pytest.mark.asyncio
    async def test_async_custom_headers(self):
        """Test async session with custom headers."""
        session = AsyncSession()
        session.headers["X-Async-Header"] = "async-value"
        try:
            response = await session.get(f"{self.base_url}/")
            assert response.status_code == 200
            # Custom headers should be sent with all requests
        finally:
            await session.close()
