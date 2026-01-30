"""tests/unit/test_exceptions.py"""

import pytest

from reqivo.exceptions import (
    ConnectTimeout,
    InvalidResponseError,
    NetworkError,
    ProtocolError,
    ReadTimeout,
    RedirectLoopError,
    ReqivoError,
    RequestError,
    TimeoutError,
    TlsError,
)


def test_exception_hierarchy():
    """Verify the inheritance structure of Reqivo exceptions."""
    assert issubclass(RequestError, ReqivoError)
    assert issubclass(NetworkError, RequestError)
    assert issubclass(TimeoutError, RequestError)
    assert issubclass(ProtocolError, RequestError)
    assert issubclass(ConnectTimeout, TimeoutError)
    assert issubclass(ReadTimeout, TimeoutError)
    assert issubclass(TlsError, NetworkError)
    assert issubclass(InvalidResponseError, ProtocolError)
    assert issubclass(RedirectLoopError, RequestError)


def test_timeout_error_default_message():
    """Verify that TimeoutError has a default message."""
    with pytest.raises(TimeoutError) as exc_info:
        raise TimeoutError()
    assert "Operation timed out" in str(exc_info.value)


def test_timeout_error_custom_message():
    """Verify that TimeoutError accepts a custom message."""
    with pytest.raises(TimeoutError) as exc_info:
        raise TimeoutError("Custom timeout")
    assert "Custom timeout" in str(exc_info.value)


@pytest.mark.parametrize(
    "exception_class",
    [
        ReqivoError,
        RequestError,
        NetworkError,
        ProtocolError,
        TlsError,
        InvalidResponseError,
        RedirectLoopError,
    ],
)
def test_generic_exceptions_accept_message(exception_class):
    """Verify that generic exceptions can be raised with a message."""
    message = f"Testing {exception_class.__name__}"
    with pytest.raises(exception_class) as exc_info:
        raise exception_class(message)
    assert message in str(exc_info.value)
