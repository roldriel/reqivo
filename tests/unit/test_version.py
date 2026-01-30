"""tests/unit/test_version.py"""

import reqivo


def test_version():
    """Verify that the version string is present and valid."""
    assert isinstance(reqivo.__version__, str)
    assert len(reqivo.__version__) > 0
    # Basic semver-ish check
    assert reqivo.__version__.count(".") >= 1
