"""src/reqivo/transport/tls.py

Advanced TLS configuration for Reqivo.
"""

import ssl


def create_ssl_context() -> ssl.SSLContext:
    """Creates a default SSL context."""
    return ssl.create_default_context()
