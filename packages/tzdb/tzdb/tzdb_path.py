"""Path to the text time zone database."""

from __future__ import annotations

from tzdb._install import text_database_dir

_TYPE = "`type` must be 'text'."


def tzdb_path(type):
    """Return the directory that holds the text time zone database.

    ``type`` must be the string ``"text"``. Any other value raises
    ``ValueError``.
    """
    if type != "text":
        raise ValueError(_TYPE)
    return text_database_dir()
