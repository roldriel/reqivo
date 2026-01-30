"""tests/unit/test_utils.py"""

import pytest

from reqivo.utils.serialization import to_json
from reqivo.utils.validators import validate_url


def test_to_json():
    """Test JSON serialization utility."""
    data = {"a": 1, "b": [2, 3]}
    assert to_json(data) == '{"a": 1, "b": [2, 3]}'


@pytest.mark.parametrize(
    "url, expected",
    [
        ("http://example.com", True),
        ("https://example.com", True),
        ("ws://example.com", True),
        ("wss://example.com", True),
        ("ftp://example.com", False),
        ("invalid", False),
        ("", False),
    ],
)
def test_validate_url(url, expected):
    """Test URL validation utility."""
    assert validate_url(url) is expected
