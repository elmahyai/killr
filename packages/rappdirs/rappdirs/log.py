"""User log directory from rappdirs 0.3.4."""

from __future__ import annotations

from rappdirs.appdir import _user_log_dir
from rappdirs.cache import _MISSING


def user_log_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    opinion=True,
    expand=True,
    os=None,
):
    """Return the user-specific log directory for an application.

    On macOS this is ``~/Library/Logs/<AppName>``. On Unix it is
    ``<XDG_CACHE_HOME or ~/.cache>/<AppName>/log`` when ``opinion`` is true.
    On Windows it uses local app data with an optional ``Logs`` segment.
    """

    return _user_log_dir(appname, appauthor, version, opinion, expand, os)
