"""tests/unit/test_tls.py"""

import ssl

from reqivo.transport.tls import create_ssl_context


class TestTLS:
    """Tests for TLS utilities."""

    def test_create_ssl_context(self):
        """Test creating SSL context."""
        context = create_ssl_context()
        assert isinstance(context, ssl.SSLContext)
        # Verify it's a properly configured context
        assert context.check_hostname is True
        assert context.verify_mode == ssl.CERT_REQUIRED
