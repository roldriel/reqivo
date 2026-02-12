"""src/reqivo/exceptions.py

Reqivo Exceptions hierarchy.
"""

# pylint: disable=redefined-builtin


class ReqivoError(Exception):
    """Base exception for all Reqivo errors."""


class RequestError(ReqivoError):
    """General exception for Request errors."""


class NetworkError(RequestError):
    """
    Base exception for network-related errors.
    Wraps socket errors and other connection issues.
    """


class TimeoutError(RequestError):
    """
    Base exception for timeouts.
    """

    def __init__(self, message: str = "Operation timed out"):
        super().__init__(message)


class ConnectTimeout(TimeoutError):
    """Timeout during connection establishment."""


class ReadTimeout(TimeoutError):
    """Timeout during data reception."""


class TlsError(NetworkError):
    """TLS/SSL handshake or verification errors."""


class ProtocolError(RequestError):
    """
    Errors related to HTTP protocol (parsing, violations).
    """


class InvalidResponseError(ProtocolError):
    """Server sent a response that could not be understood."""


class RedirectLoopError(RequestError):
    """Exception for infinite redirect loops."""


class TooManyRedirects(RequestError):
    """Too many redirects occurred."""
