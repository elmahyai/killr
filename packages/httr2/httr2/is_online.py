"""Whether this computer is online.

httr2 exports this as a wrapper around curl's ``has_internet`` check.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PACKAGES = Path(__file__).resolve().parents[2]
_CURL = str(_PACKAGES / "curl")
if _CURL not in sys.path:
    sys.path.insert(0, _CURL)

from curl import has_internet


def is_online() -> bool:
    """Return the result of ``curl.has_internet``.

    That check is a DNS lookup of ``dns.google.com``. This wrapper does
    not make a further request.
    """
    return has_internet()
