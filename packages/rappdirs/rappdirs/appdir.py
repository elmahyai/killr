"""Application directory bundle from rappdirs 0.3.4 ``app_dir``."""

from __future__ import annotations

import os

from rappdirs.cache import (
    _MISSING,
    _base_path,
    _check_os,
    _check_version,
    _env_fallback,
    _file_path,
    _get_os,
    _r_if,
    _win_local,
    _win_path_csidl,
    user_cache_dir,
)


class AppDir:
    """Paths for one application, with one method per rappdirs directory kind."""

    def __init__(
        self,
        appname,
        appauthor,
        version,
        expand,
        os_name: str,
    ) -> None:
        self._appname = appname
        self._appauthor = appauthor
        self._version = version
        self._expand = expand
        self._os = os_name
        self.os = os_name

    def cache(self, opinion=True):
        return user_cache_dir(
            self._appname,
            self._appauthor,
            self._version,
            opinion,
            self._expand,
            self._os,
        )

    def log(self, opinion=True):
        return _user_log_dir(
            self._appname,
            self._appauthor,
            self._version,
            opinion,
            self._expand,
            self._os,
        )

    def data(self, roaming=False):
        return _user_data_dir(
            self._appname,
            self._appauthor,
            self._version,
            roaming,
            self._expand,
            self._os,
        )

    def config(self, roaming=False):
        return _user_config_dir(
            self._appname,
            self._appauthor,
            self._version,
            roaming,
            self._expand,
            self._os,
        )

    def site_data(self, multipath=False):
        return _site_data_dir(
            self._appname,
            self._appauthor,
            self._version,
            multipath,
            self._expand,
            self._os,
        )

    def site_config(self, multipath=False):
        return _site_config_dir(
            self._appname,
            self._appauthor,
            self._version,
            multipath,
            self._expand,
            self._os,
        )


def app_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    expand=True,
    os=None,
):
    """Return an object with ``cache``, ``log``, ``data``, and related path methods."""

    if appauthor is _MISSING:
        appauthor = appname
    os_name = _check_os(os)
    return AppDir(appname, appauthor, version, expand, os_name)


def _user_log_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    opinion=True,
    expand=True,
    os_name=None,
):
    if appauthor is _MISSING:
        appauthor = appname
    version = _check_version(version, appname, expand)
    system = _check_os(os_name)
    if system == "win":
        logs = "Logs" if _r_if(opinion) else None
        return _file_path(_win_path("local"), appauthor, appname, version, logs)
    if system == "mac":
        return _file_path("~/Library/Logs", appname, version)
    base = os.environ.get("XDG_CACHE_HOME", "~/.cache")
    log_dir = "log" if _r_if(opinion) else None
    return _file_path(base, appname, version, log_dir)


def _user_data_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    roaming=False,
    expand=True,
    os_name=None,
):
    if appauthor is _MISSING:
        appauthor = appname
    version = _check_version(version, appname, expand)
    base = _base_path(
        os_name,
        "DATA",
        lambda: _win_path("roaming" if _r_if(roaming) else "local"),
        lambda: "~/Library/Application Support",
        _xdg_data_home,
    )
    system = _check_os(os_name)
    if system == "win":
        return _file_path(base, appauthor, appname, version)
    return _file_path(base, appname, version)


def _user_config_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    roaming=False,
    expand=True,
    os_name=None,
):
    if appauthor is _MISSING:
        appauthor = appname
    version = _check_version(version, appname, expand)
    base = _base_path(
        os_name,
        "CONFIG",
        lambda: _win_path("roaming" if _r_if(roaming) else "local"),
        lambda: "~/Library/Application Support",
        _xdg_config_home,
    )
    system = _check_os(os_name)
    if system == "win":
        return _file_path(base, appauthor, appname, version)
    return _file_path(base, appname, version)


def _site_data_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    multipath=False,
    expand=True,
    os_name=None,
):
    if appauthor is _MISSING:
        appauthor = appname
    version = _check_version(version, appname, expand)
    system = _check_os(os_name)
    if system == "win":
        return _file_path(_win_path("common"), appauthor, appname, version)
    if system == "mac":
        return _file_path("/Library/Application Support", appname, version)
    env = os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share")
    return _file_path_site_unix(env, appname, version, multipath)


def _site_config_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    multipath=False,
    expand=True,
    os_name=None,
):
    if appauthor is _MISSING:
        appauthor = appname
    version = _check_version(version, appname, expand)
    system = _check_os(os_name)
    if system == "win":
        return _file_path(_win_path("common"), appauthor, appname, version)
    if system == "mac":
        return _file_path("/Library/Application Support", appname, version)
    env = os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg")
    return _file_path_site_unix(env, appname, version, multipath)


def _xdg_data_home() -> str:
    if "XDG_DATA_HOME" in os.environ:
        return os.environ["XDG_DATA_HOME"]
    return "~/.local/share"


def _xdg_config_home() -> str:
    if "XDG_CONFIG_HOME" in os.environ:
        return os.environ["XDG_CONFIG_HOME"]
    return "~/.config"


def _win_path(type_appdata: str = "common") -> str:
    if type_appdata == "roaming":
        found = _win_path_csidl(26)
        if found is not None:
            return found
        return _env_fallback("APPDATA")
    if type_appdata == "local":
        return _win_local()
    if type_appdata == "common":
        found = _win_path_csidl(35)
        if found is not None:
            return found
        program = os.environ.get("PROGRAMDATA")
        if program is not None and program != "":
            return program
        return _file_path(_env_fallback("ALLUSERPROFILE"), "Application Data")
    raise ValueError("invalid `type` argument")


def _parse_path_string(path: str, sep: str = ":") -> list[str]:
    seen: list[str] = []
    for piece in path.split(sep):
        if piece not in seen:
            seen.append(piece)
    return seen


def _file_path_site_unix(sys_getenv, appname, version, multipath=False):
    paths = _parse_path_string(sys_getenv)
    if _r_if(multipath):
        return [_file_path(path, appname, version) for path in paths]
    return _file_path(paths[0], appname, version)
