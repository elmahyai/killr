"""Time zone names from the text database."""

from __future__ import annotations

import tzdb_kernel

from tzdb.tzdb_path import tzdb_path


def tzdb_names():
    """Return the zone and link names, sorted in byte order."""
    return list(tzdb_kernel.zone_names(tzdb_path("text")))
