"""src/reqivo/transport/tls.py

Advanced TLS configuration for Reqivo.
"""

import ssl


def create_ssl_context() -> ssl.SSLContext:
    """Creates a default SSL context with TLS 1.2 minimum."""
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context
