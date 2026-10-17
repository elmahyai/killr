"""User data directory from rappdirs 0.3.4."""

from __future__ import annotations

from rappdirs.appdir import _user_data_dir
from rappdirs.cache import _MISSING


def user_data_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    roaming=False,
    expand=True,
    os=None,
):
    """Return the user-specific data directory for an application.

    ``R_USER_DATA_DIR`` replaces the platform base when it is set and not
    empty. On Linux this is ``~/.local/share`` (or ``XDG_DATA_HOME``); on
    macOS and Windows it follows the same application-support layout as user
    config, with ``roaming`` choosing roaming vs local app data on Windows
    (default not roaming).
    """

    return _user_data_dir(appname, appauthor, version, roaming, expand, os)
