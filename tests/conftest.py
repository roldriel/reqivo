import _thread
import threading
from contextlib import contextmanager

import pytest


@pytest.fixture
def timeout_context():
    """Fixture providing a timeout context manager."""

    @contextmanager
    def _timeout_context(seconds):
        def timeout_handler():
            _thread.interrupt_main()

        timer = threading.Timer(seconds, timeout_handler)
        timer.start()
        try:
            yield
        except KeyboardInterrupt:
            pytest.fail(f"Test timed out after {seconds} seconds")
        finally:
            timer.cancel()

    return _timeout_context
