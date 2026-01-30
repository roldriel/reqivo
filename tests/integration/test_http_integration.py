"""Integration tests for HTTP client functionality.

These tests use a local HTTP test server to validate real HTTP communication
without external dependencies.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

import pytest

from reqivo import Session


class IntegrationHTTPRequestHandler(BaseHTTPRequestHandler):
    """Simple HTTP server for integration testing."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress server logs during testing."""
        pass

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {"message": "Hello, World!", "method": "GET"}
            self.wfile.write(json.dumps(response_data).encode())

        elif self.path == "/set-cookie":
            self.send_response(200)
            self.send_header("Set-Cookie", "session_id=test123; Path=/")
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Cookie set")

        elif self.path == "/check-cookie":
            cookie_header = self.headers.get("Cookie", "")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {"cookie": cookie_header}
            self.wfile.write(json.dumps(response_data).encode())

        elif self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/json")
            self.end_headers()

        elif self.path == "/auth":
            auth_header = self.headers.get("Authorization", "")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {"auth": auth_header}
            self.wfile.write(json.dumps(response_data).encode())

        elif self.path == "/status/404":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")

    def do_POST(self) -> None:
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        if self.path == "/echo":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response_data = {
                "received": post_data.decode("utf-8"),
                "method": "POST",
            }
            self.wfile.write(json.dumps(response_data).encode())

        elif self.path == "/json":
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            try:
                received_json = json.loads(post_data.decode("utf-8"))
                response_data = {"echo": received_json, "status": "created"}
                self.wfile.write(json.dumps(response_data).encode())
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON")

        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"POST received")


class TestHTTPIntegration:
    """Integration tests for HTTP client operations."""

    @classmethod
    def setup_class(cls):
        """Start the test HTTP server."""
        cls.server = HTTPServer(("localhost", 0), IntegrationHTTPRequestHandler)
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

    def test_simple_get_request(self):
        """Test basic GET request."""
        session = Session()
        try:
            response = session.get(f"{self.base_url}/")
            assert response.status_code == 200
            assert response.text() == "OK"
        finally:
            session.close()

    def test_get_json_response(self):
        """Test GET request with JSON response."""
        session = Session()
        try:
            response = session.get(f"{self.base_url}/json")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Hello, World!"
            assert data["method"] == "GET"
        finally:
            session.close()

    def test_post_request_with_body(self):
        """Test POST request with request body."""
        session = Session()
        try:
            test_data = "test payload"
            response = session.post(f"{self.base_url}/echo", body=test_data)
            assert response.status_code == 200
            data = response.json()
            assert data["received"] == test_data
            assert data["method"] == "POST"
        finally:
            session.close()

    def test_post_json_data(self):
        """Test POST request with JSON data."""
        session = Session()
        try:
            test_json = {"name": "test", "value": 123}
            json_str = json.dumps(test_json)
            response = session.post(
                f"{self.base_url}/json",
                body=json_str,
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 201
            data = response.json()
            assert data["echo"]["name"] == "test"
            assert data["echo"]["value"] == 123
        finally:
            session.close()

    def test_session_cookies(self):
        """Test session cookie management."""
        session = Session()
        try:
            # Set cookie
            response1 = session.get(f"{self.base_url}/set-cookie")
            assert response1.status_code == 200

            # Verify cookie is stored
            assert "session_id" in session.cookies
            assert session.cookies["session_id"] == "test123"

            # Verify cookie is sent in subsequent request
            response2 = session.get(f"{self.base_url}/check-cookie")
            assert response2.status_code == 200
            data = response2.json()
            assert "session_id=test123" in data["cookie"]
        finally:
            session.close()

    def test_basic_authentication(self):
        """Test basic authentication header."""
        session = Session()
        session.set_basic_auth("user", "pass")
        try:
            response = session.get(f"{self.base_url}/auth")
            assert response.status_code == 200
            data = response.json()
            assert data["auth"].startswith("Basic ")
        finally:
            session.close()

    def test_bearer_token_authentication(self):
        """Test bearer token authentication."""
        session = Session()
        session.set_bearer_token("test_token_12345")
        try:
            response = session.get(f"{self.base_url}/auth")
            assert response.status_code == 200
            data = response.json()
            assert data["auth"] == "Bearer test_token_12345"
        finally:
            session.close()

    def test_custom_headers(self):
        """Test sending custom headers."""
        session = Session()
        session.headers["X-Custom-Header"] = "test-value"
        try:
            # Custom headers should be sent with requests
            response = session.get(f"{self.base_url}/")
            assert response.status_code == 200
        finally:
            session.close()

    def test_404_error_response(self):
        """Test handling of 404 error responses."""
        session = Session()
        try:
            response = session.get(f"{self.base_url}/status/404")
            assert response.status_code == 404
            assert response.text() == "Not Found"
        finally:
            session.close()

    def test_connection_reuse(self):
        """Test connection pooling and reuse."""
        session = Session()
        try:
            # Make multiple requests to the same host
            response1 = session.get(f"{self.base_url}/")
            assert response1.status_code == 200

            response2 = session.get(f"{self.base_url}/json")
            assert response2.status_code == 200

            response3 = session.get(f"{self.base_url}/")
            assert response3.status_code == 200

            # All requests should succeed using connection pool
        finally:
            session.close()
