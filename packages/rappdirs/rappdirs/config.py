"""User configuration directory from rappdirs 0.3.4."""

from __future__ import annotations

from rappdirs.appdir import _user_config_dir
from rappdirs.cache import _MISSING


def user_config_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    roaming=True,
    expand=True,
    os=None,
):
    """Return the user-specific configuration directory for an application.

    ``R_USER_CONFIG_DIR`` replaces the platform base when it is set and not
    empty. On Linux this is ``~/.config`` (or ``XDG_CONFIG_HOME``); on macOS
    and Windows it follows the same application-support layout as user data,
    with ``roaming`` choosing roaming vs local app data on Windows (default
    roaming).
    """

    return _user_config_dir(appname, appauthor, version, roaming, expand, os)
