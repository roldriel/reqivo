"""utils/serialization.py

Serialization utilities for Reqivo (JSON, form-urlencode, etc.).
"""

import json
from typing import Any

# Currently a placeholder to be populated with logic from Request.py if needed
# or centralized serialization logic.


def to_json(data: Any) -> str:
    """Serializes data to a JSON string."""
    return json.dumps(data)
