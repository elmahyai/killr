"""Site-wide data and config directories from rappdirs 0.3.4."""

from __future__ import annotations

from rappdirs.appdir import _site_config_dir, _site_data_dir
from rappdirs.cache import _MISSING


def site_data_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    multipath=False,
    expand=True,
    os=None,
):
    """Return the site-wide shared data directory for an application name.

    On Windows and macOS this uses the all-users application data layout. On
    Unix the base list comes from ``XDG_DATA_DIRS``, defaulting to
    ``/usr/local/share:/usr/share``.
    """

    return _site_data_dir(appname, appauthor, version, multipath, expand, os)


def site_config_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    multipath=False,
    expand=True,
    os=None,
):
    """Return the site configuration directory for an application name.

    On Windows and macOS this matches the site data directory layout. On Unix
    the base list comes from ``XDG_CONFIG_DIRS``, defaulting to ``/etc/xdg``.
    """

    return _site_config_dir(appname, appauthor, version, multipath, expand, os)
