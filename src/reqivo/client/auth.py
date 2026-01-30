"""client/auth.py

Authentication helpers for Reqivo.
"""

import base64


def build_basic_auth_header(username: str, password: str) -> str:
    """
    Build Basic Auth header from username and password.

    Args:
        username: Username for authentication.
        password: Password for authentication.

    Returns:
        Basic Auth header value.
    """
    token = f"{username}:{password}".encode("utf-8")
    b64 = base64.b64encode(token).decode("ascii")
    return f"Basic {b64}"


def build_bearer_auth_header(token: str) -> str:
    """
    Build Bearer token header.

    Args:
        token: Bearer token for authentication.

    Returns:
        Bearer token header value.
    """
    return f"Bearer {token}"
