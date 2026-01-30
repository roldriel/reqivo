"""core/timeouts.py

Timeouts configuration.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Timeout:
    """
    Timeout configuration.

    Attributes:
        connect: Maximum time to wait for connection establishment (socket connect).
        read: Maximum time to wait for data to be received (socket recv).
        total: Maximum total time for the operation.
    """

    connect: Optional[float] = None
    read: Optional[float] = None
    total: Optional[float] = None

    @classmethod
    def from_float(cls, timeout: Optional[float]) -> "Timeout":
        """Create a Timeout instance from a single float (total timeout fallback)."""
        if timeout is None:
            return cls()
        return cls(connect=timeout, read=timeout, total=timeout)
