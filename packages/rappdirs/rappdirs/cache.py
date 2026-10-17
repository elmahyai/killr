"""User cache directory from rappdirs 0.3.4.

The path is pasted with the platform separator. A missing component is left
out. An empty string stays, so the path can start or end with a separator.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import sys
import warnings

_MISSING = object()
_SPECS: dict[str, str] | None = None
_TRUE = {"T", "TRUE", "True", "true"}
_FALSE = {"F", "FALSE", "False", "false"}
_SYSTEMS = {"win", "mac", "unix"}


def user_cache_dir(
    appname=None,
    appauthor=_MISSING,
    version=None,
    opinion=True,
    expand=True,
    os=None,
):
    """Path to the user cache directory.

    ``R_USER_CACHE_DIR`` replaces the platform base when it is set and not
    empty. ``opinion`` appends ``Cache`` only on Windows. ``expand`` rewrites
    ``%V``, ``%v``, ``%p``, ``%o``, ``%a``, and ``%%`` in ``version``.
    """

    if appauthor is _MISSING:
        appauthor = appname
    version = _check_version(version, appname, expand)
    base = _base_path(
        os,
        "CACHE",
        _win_local,
        lambda: "~/Library/Caches",
        _xdg_cache_home,
    )
    system = _check_os(os)
    if system == "win":
        cache = "Cache" if _r_if(opinion) else None
        return _file_path(base, appauthor, appname, version, cache)
    return _file_path(base, appname, version)


def _check_version(version, appname, expand):
    if appname is None and version is not None:
        warnings.warn(
            "version is ignored when appname is null",
            UserWarning,
            stacklevel=3,
        )
        return None
    if _r_if(expand):
        return _expand_r_libs_specifiers(version)
    return version


def _expand_r_libs_specifiers(value):
    if value is None:
        return None
    elements = _atoms(value)
    if not any("%" in item for item in elements):
        return elements
    specs = _r_specifiers()
    expanded = []
    for item in elements:
        text = item
        for token in ("%V", "%v", "%p", "%o", "%a"):
            text = _gsub_special(token, specs[token], text)
        text = text.replace("%%", "%")
        expanded.append(text)
    return expanded


def _gsub_special(pattern: str, replacement: str, text: str) -> str:
    """Replace ``pattern`` when it is at the start or follows a non-percent."""

    regex = re.compile(r"([^%]|^)" + re.escape(pattern))

    def repl(match: re.Match[str]) -> str:
        return match.group(1) + replacement

    return regex.sub(repl, text)


def _r_specifiers() -> dict[str, str]:
    global _SPECS
    if _SPECS is not None:
        return _SPECS
    script = (
        "rv <- getRversion();"
        "cat(as.character(rv), '\n', sep='');"
        "cat(paste(rv$major, rv$minor, sep='.'), '\n', sep='');"
        "cat(R.version$platform, '\n', sep='');"
        "cat(R.version$os, '\n', sep='');"
        "cat(R.version$arch, '\n', sep='')"
    )
    completed = subprocess.run(
        ["Rscript", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    lines = completed.stdout.splitlines()
    if len(lines) != 5:
        raise RuntimeError("could not read the installed R version")
    _SPECS = {
        "%V": lines[0],
        "%v": lines[1],
        "%p": lines[2],
        "%o": lines[3],
        "%a": lines[4],
    }
    return _SPECS


def _base_path(os_name, kind: str, win, mac, unix) -> str:
    val = os.environ.get(f"R_USER_{kind}_DIR", "")
    if val != "":
        return val
    system = _check_os(os_name)
    if system == "win":
        return win()
    if system == "mac":
        return mac()
    return unix()


def _xdg_cache_home() -> str:
    if "XDG_CACHE_HOME" in os.environ:
        return os.environ["XDG_CACHE_HOME"]
    return "~/.cache"


def _win_local() -> str:
    found = _win_path_csidl(28)
    if found is not None:
        return found
    if "LOCALAPPDATA" in os.environ:
        return os.environ["LOCALAPPDATA"]
    return _file_path(
        _env_fallback("USERPROFILE"),
        "Local Settings",
        "Application Data",
    )


def _win_path_csidl(csidl: int):
    """SHGetFolderPath, or NULL when the call fails or this is not Windows."""

    if sys.platform != "win32":
        return None
    import ctypes

    buffer = ctypes.create_unicode_buffer(260)
    code = ctypes.windll.shell32.SHGetFolderPathW(None, int(csidl), None, 0, buffer)
    if code < 0:
        return None
    short = ctypes.create_unicode_buffer(260)
    ctypes.windll.kernel32.GetShortPathNameW(buffer, short, 260)
    return short.value


def _env_fallback(name: str) -> str:
    val = os.environ.get(name, "")
    if val == "":
        if _get_os() == "win":
            raise ValueError(f"Can't find envvar '{name}'")
        return f"<{name}>"
    return val


def _get_os() -> str:
    if sys.platform == "win32":
        return "win"
    if sys.platform == "darwin":
        return "mac"
    return "unix"


def _check_os(os_name) -> str:
    if os_name is None:
        return _get_os()
    if isinstance(os_name, (list, tuple)):
        if len(os_name) != 1:
            raise ValueError("`os` must be a string")
        os_name = os_name[0]
    if not isinstance(os_name, str):
        raise ValueError("`os` must be a string")
    if os_name not in _SYSTEMS:
        raise ValueError("`os` must be one of 'win', 'mac', 'unix'")
    return os_name


def _r_if(condition) -> bool:
    """R's if() on one value."""

    if condition is None:
        raise ValueError("argument is of length zero")
    if isinstance(condition, (list, tuple)):
        if len(condition) == 0:
            raise ValueError("argument is of length zero")
        if len(condition) > 1:
            raise ValueError("the condition has length > 1")
        return _r_if(condition[0])
    if isinstance(condition, bool):
        return condition
    if isinstance(condition, (int, float)):
        if isinstance(condition, float) and math.isnan(condition):
            raise ValueError("argument is not interpretable as logical")
        if condition == 0:
            return False
        return True
    if isinstance(condition, str):
        if condition in _TRUE:
            return True
        if condition in _FALSE:
            return False
        raise ValueError("argument is not interpretable as logical")
    raise ValueError("argument is not interpretable as logical")


def _file_path(*parts) -> str:
    flat: list[str] = []
    for part in parts:
        flat.extend(_atoms(part))
    return os.sep.join(flat)


def _atoms(value) -> list[str]:
    """Drop NULL and length zero, and turn each kept value into text."""

    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        flat: list[str] = []
        for item in value:
            flat.extend(_atoms(item))
        return flat
    return [_as_character(value)]


def _as_character(value) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _as_character_double(value)
    return str(value)


def _as_character_double(value: float) -> str:
    """R as.character for a double, scientific on a length tie."""

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) <= len(fixed):
        return sci
    return fixed
