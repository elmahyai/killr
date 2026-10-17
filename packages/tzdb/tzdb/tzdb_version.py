"""Version string of the text time zone database."""

from __future__ import annotations

import tzdb_kernel

from tzdb.tzdb_path import tzdb_path


def tzdb_version():
    """Return the database version, such as ``"2025a"``."""
    return tzdb_kernel.database_version(tzdb_path("text"))
