"""tests/unit/test_timing.py"""

from reqivo.utils.timing import Timeout


class TestTimeout:
    """Tests for Timeout class."""

    def test_timeout_from_float_with_none(self):
        """Test Timeout.from_float() with None returns empty Timeout."""
        timeout = Timeout.from_float(None)

        assert isinstance(timeout, Timeout)
        assert timeout.connect is None
        assert timeout.read is None
        assert timeout.total is None

    def test_timeout_from_float_with_value(self):
        """Test Timeout.from_float() with float value."""
        timeout = Timeout.from_float(5.0)

        assert timeout.connect == 5.0
        assert timeout.read == 5.0
        assert timeout.total == 5.0
