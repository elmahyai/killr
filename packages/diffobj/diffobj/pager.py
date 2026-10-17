"""Pager probes that do not call ``tools::Rdiff``.

``pager_is_less`` follows the branch R uses when ``options(pager=)`` is still
the default. That branch reads ``PAGER`` after startup. R's ``Renviron`` sets
``PAGER`` when the variable is unset, so an empty environment is not an empty
pager. A bare name is not searched on ``PATH``.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

_LESS_VERSION = re.compile(r"^less \d+")
_PAGER_LINE = re.compile(r"^PAGER=\$\{PAGER-['\"]?([^'\"}]*)['\"]?\}", re.M)
_DEFAULT_PAGER: str | None = None
_LOOKED_UP = False


def _r_home() -> str | None:
    home = os.environ.get("R_HOME")
    if home:
        return home
    binary = shutil.which("R")
    if binary is None:
        return None
    try:
        completed = subprocess.run(
            [binary, "RHOME"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    text = completed.stdout.strip()
    return text or None


def _renviron_pager() -> str:
    """Default ``PAGER`` from ``R_HOME/etc/Renviron`` when the variable is unset."""

    global _DEFAULT_PAGER, _LOOKED_UP
    if _LOOKED_UP:
        return _DEFAULT_PAGER or ""
    _LOOKED_UP = True
    home = _r_home()
    if not home:
        _DEFAULT_PAGER = ""
        return ""
    path = os.path.join(home, "etc", "Renviron")
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        _DEFAULT_PAGER = ""
        return ""
    match = _PAGER_LINE.search(text)
    _DEFAULT_PAGER = match.group(1) if match else ""
    return _DEFAULT_PAGER


def _pager_program() -> str:
    if "PAGER" in os.environ:
        return os.environ["PAGER"]
    return _renviron_pager()


def file_is_less(path: str) -> bool:
    if not isinstance(path, str) or path == "":
        return False
    if not os.path.isfile(path) or not os.access(path, os.X_OK):
        return False
    try:
        completed = subprocess.run(
            [path, "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, ValueError):
        return False
    lines = (completed.stdout + completed.stderr).splitlines()
    return bool(lines) and _LESS_VERSION.match(lines[0]) is not None


def pager_is_less() -> bool:
    """Whether the pager R would use identifies itself as less."""

    return file_is_less(_pager_program())


def make_blocking(fun, msg: str = "Press ENTER to continue...", invisible_res: bool = True):
    """Run ``fun``, then wait for Enter.

    ``readline`` under ``Rscript`` does not prompt and does not wait. The same
    happens here when stdin is not a terminal. A closed terminal returns an
    empty line.
    """

    if not callable(fun):
        raise TypeError("Argument `fun` must be a function")
    if not isinstance(msg, str):
        raise TypeError("Argument `msg` must be character(1L) and not NA")
    if not isinstance(invisible_res, bool):
        raise TypeError("Argument `invisible.res` must be TRUE or FALSE")

    def wrapped(*args, **kwargs):
        result = fun(*args, **kwargs)
        if sys.stdin is not None and sys.stdin.isatty():
            try:
                input(msg)
            except EOFError:
                pass
        return result

    return wrapped


import math
import shlex
import warnings
import webbrowser

# URLs that could not be opened because there is no display or no browser.
recorded_urls: list[str] = []

_LESS_SHAPE = re.compile(r"^\s*-[A-Za-z]+(?:\s+-[A-Za-z]+)*\s*$")
_LESS_TAIL = re.compile(r"(-[A-Za-z]+)$")


class NA:
    """R missing value. ``kind`` is ``logical`` or ``character``."""

    def __init__(self, kind: str) -> None:
        self.kind = kind

    def __repr__(self) -> str:
        if self.kind == "character":
            return "NA_character_"
        return "NA"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NA) and self.kind == other.kind

    def __hash__(self) -> int:
        return hash(("NA", self.kind))


NA_logical = NA("logical")
NA_character_ = NA("character")


def _is_na(value) -> bool:
    if isinstance(value, NA):
        return True
    return isinstance(value, float) and math.isnan(value)


def _is_chr_1l(value) -> bool:
    """R ``is.chr.1L``: one character string, not NA."""

    return isinstance(value, str)


def _is_int_1l(value) -> bool:
    """R ``is.int.1L``. ``TRUE`` is logical, so it is not an integer."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        if not math.isfinite(value):
            return False
        return value == math.trunc(value)
    return True


def _is_tf(value) -> bool:
    """R ``is.TF``: exactly ``TRUE`` or ``FALSE``."""

    return value is True or value is False


def _is_logical_1(value) -> bool:
    if value is True or value is False:
        return True
    return isinstance(value, NA) and value.kind == "logical"


def _r_length(value) -> int:
    if value is None:
        return 0
    if isinstance(value, (list, tuple)):
        return len(value)
    return 1


def _class_error(class_name: str, detail: str) -> None:
    raise ValueError(f"invalid class “{class_name}” object: {detail}")


def _r_deparse(value) -> str:
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return repr(value)


def _unused(extra: dict) -> None:
    parts = ", ".join(f"{key} = {_r_deparse(val)}" for key, val in extra.items())
    word = "argument" if len(extra) == 1 else "arguments"
    raise ValueError(f"unused {word} ({parts})")


def _pop_alias(kwargs: dict, r_name: str, py_name: str, default):
    has_r = r_name in kwargs
    has_py = py_name in kwargs
    if has_r and has_py:
        raise ValueError(
            f"unused arguments ({r_name} = {_r_deparse(kwargs[r_name])}, "
            f"{py_name} = {_r_deparse(kwargs[py_name])})"
        )
    if has_r:
        return kwargs.pop(r_name)
    if has_py:
        return kwargs.pop(py_name)
    return default


def _coerce_file_path(value):
    """Pager ``initialize``: length 1, NA becomes ``NA_character_``, else character."""

    if _r_length(value) != 1:
        raise ValueError("Argument `file.path` must be length 1.")
    if _is_na(value):
        return NA_character_
    if not isinstance(value, str):
        raise ValueError("Argument `file.path` must be character.")
    return value


def _r_type_name(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, (int, float)):
        return "numeric"
    if isinstance(value, str) or (isinstance(value, NA) and value.kind == "character"):
        return "character"
    if isinstance(value, NA):
        return value.kind
    return type(value).__name__


def _write_lines(path) -> None:
    """Default ``Pager`` function: ``writeLines(readLines(x))``."""

    with open(path, encoding="utf-8", errors="surrogateescape") as handle:
        lines = handle.read().splitlines()
    sys.stdout.write("".join(f"{line}\n" for line in lines))


def file_show(path, *paths, header="", title="R Information", delete_file=False, pager=None, encoding=""):
    """``file.show`` for the file path a pager receives.

    A non-interactive stdin prints the file. A terminal uses ``PAGER`` when
    one is set, which is the same program R's ``file.show`` would invoke.
    """

    files = (path, *paths)
    program = None
    if isinstance(pager, str) and pager:
        program = pager
    elif pager is None:
        program = os.environ.get("PAGER") or shutil.which("less") or shutil.which("more")
    interactive = sys.stdin is not None and sys.stdin.isatty()
    for one in files:
        if interactive and program:
            subprocess.run([program, str(one)], check=False)
        else:
            _write_lines(one)


def set_less_var(flags: str):
    """Set ``LESS`` the way ``set_less_var`` does. Return the previous value or ``None``."""

    if "LESS" in os.environ:
        old = os.environ["LESS"]
        less = old
    else:
        old = None
        less = None
    new = None
    if less is None or less.strip() == "":
        new = f"-{flags}"
    elif _LESS_SHAPE.fullmatch(less):
        match = _LESS_TAIL.search(less)
        if match:
            new = less[: match.start(1)] + match.group(1) + flags
        else:
            new = less
    if new is not None:
        os.environ["LESS"] = new
    return old


def reset_less_var(old) -> None:
    if old is None:
        os.environ.pop("LESS", None)
    else:
        os.environ["LESS"] = old


def _with_less_flags(pager, flags: str):
    def wrapped(path):
        old = set_less_var(flags)
        try:
            return pager(path)
        finally:
            reset_less_var(old)

    return wrapped


def _display_exists() -> bool:
    if sys.platform == "win32" or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _browser_exists() -> bool:
    if os.environ.get("BROWSER"):
        return True
    names = (
        "xdg-open",
        "firefox",
        "mozilla",
        "chromium",
        "chromium-browser",
        "google-chrome",
        "chrome",
        "sensible-browser",
        "w3m",
        "links",
        "lynx",
    )
    return any(shutil.which(name) for name in names)


def _browse_url(url):
    """``utils::browseURL`` without a GUI wait.

    A non-empty character string is opened only when a display and a browser
    both exist. Otherwise the URL is recorded and this returns ``None``.
    """

    if not isinstance(url, str) or url == "":
        raise ValueError("'url' must be a non-empty character string")
    if not _display_exists() or not _browser_exists():
        recorded_urls.append(url)
        return None
    try:
        opened = webbrowser.open(url)
    except Exception:
        recorded_urls.append(url)
        return None
    if not opened:
        recorded_urls.append(url)
    return opened


def _call_viewer(viewer, url):
    if callable(viewer):
        return viewer(url)
    command = shlex.split(viewer)
    completed = subprocess.run(command + [str(url)], check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip() or f"exit status {completed.returncode}"
        raise OSError(detail)
    return completed.returncode


def view_or_browse(url, viewer=None):
    """Open ``url`` with a viewer, then a browser.

    A callable ``viewer`` argument is tried first. When that argument is
    omitted, ``DIFFOBJ_VIEWER`` is the viewer command. A viewer error warns
    and falls through. ``browseURL`` checks the URL, so an invalid URL raises
    ``'url' must be a non-empty character string`` only on that path. A normal
    http URL is recorded instead of opened when there is no display.
    """

    chosen = viewer
    if chosen is None:
        chosen = os.environ.get("DIFFOBJ_VIEWER") or None
    success = False
    result = None
    if callable(chosen) or (isinstance(chosen, str) and chosen):
        try:
            result = _call_viewer(chosen, url)
        except Exception as exc:
            warnings.warn(
                f"IDE viewer failed with error {exc}; falling back to `browseURL`",
                UserWarning,
                stacklevel=2,
            )
        else:
            success = True
    if not success:
        result = _browse_url(url)
    return result


class Pager:
    """Pager configuration. ``Pager(ansi=)`` is ignored, as in the R constructor."""

    class_name = "Pager"

    def __init__(self, pager=None, threshold=0, ansi=False, make_blocking=False, **kwargs):
        file_ext = _pop_alias(kwargs, "file.ext", "file_ext", "")
        file_path_given = "file.path" in kwargs or "file_path" in kwargs
        file_path = _pop_alias(kwargs, "file.path", "file_path", NA_character_)
        if "make.blocking" in kwargs or "make_blocking" in kwargs:
            make_blocking = _pop_alias(kwargs, "make.blocking", "make_blocking", make_blocking)
        if pager is None:
            pager = _write_lines
        # The R function `Pager` does not pass `ansi` into `new()`.
        if type(self) is Pager:
            ansi = False
            if kwargs:
                _unused(kwargs)
        elif kwargs:
            name = next(iter(kwargs))
            raise ValueError(f"invalid name for slot of class “{type(self).class_name}”: {name}")
        if file_path_given:
            file_path = _coerce_file_path(file_path)

        class_name = type(self).class_name
        if not callable(pager):
            got = _r_type_name(pager)
            _class_error(
                class_name,
                f'invalid object for slot "pager" in class "{class_name}": '
                f'got class "{got}", should be or extend class "function"',
            )
        if not _is_chr_1l(file_ext):
            _class_error(class_name, "Invalid `file.ext` slot")
        if not _is_int_1l(threshold):
            _class_error(class_name, "Invalid `threshold` slot")
        if not _is_tf(ansi):
            _class_error(class_name, "Invalid `ansi` slot")
        if not _is_logical_1(make_blocking):
            _class_error(class_name, "Invalid `make.blocking` slot")
        if not (
            isinstance(file_path, str)
            or (isinstance(file_path, NA) and file_path.kind == "character")
        ):
            _class_error(class_name, "Invalid `file.path` slot")
        threshold = int(threshold)

        self.class_name = class_name
        self.pager = pager
        self.threshold = threshold
        self.ansi = ansi
        self.file_ext = file_ext
        self.file_path = file_path
        self.make_blocking = make_blocking
        self.slots = {
            "pager": pager,
            "file.ext": file_ext,
            "threshold": threshold,
            "ansi": ansi,
            "file.path": file_path,
            "make.blocking": make_blocking,
        }
        for key, value in self.slots.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        return (
            f"{self.class_name}(threshold={self.threshold}, file.ext={self.file_ext!r}, "
            f"ansi={self.ansi}, make.blocking={self.make_blocking!r})"
        )


class PagerOff(Pager):
    """Turn the pager off. This is a ``Pager``."""

    class_name = "PagerOff"


class PagerSystem(Pager):
    """System pager via ``file.show``. The R constructor drops ``file.ext``."""

    class_name = "PagerSystem"

    def __init__(self, pager=None, threshold=-1, **kwargs):
        if pager is None:
            pager = file_show
        if type(self) is PagerSystem:
            kwargs.pop("file.ext", None)
            kwargs.pop("file_ext", None)
        super().__init__(pager=pager, threshold=threshold, **kwargs)


class PagerSystemLess(PagerSystem):
    """``PagerSystem`` that sets ``LESS`` from ``flags``.

    The constructor default is ``"R"``, the same string as ``gdo("less.flags")``.
    ``ansi`` is ``TRUE``. ``threshold`` is ``-1``.
    """

    class_name = "PagerSystemLess"

    def __init__(self, pager=None, threshold=-1, flags="R", ansi=True, **kwargs):
        if pager is None:
            pager = file_show
        if not _is_chr_1l(flags):
            raise ValueError("Argument `flags` must be character(1L) and not NA")
        wrapped = _with_less_flags(pager, flags)
        super().__init__(pager=wrapped, threshold=threshold, ansi=ansi, **kwargs)
        self.flags = flags
        self.slots["flags"] = flags


class PagerBrowser(Pager):
    """HTML pager. ``make.blocking`` defaults to NA and ``file.ext`` to ``html``."""

    class_name = "PagerBrowser"

    def __init__(self, pager=None, threshold=0, make_blocking=NA_logical, **kwargs):
        if pager is None:
            pager = view_or_browse
        if "file.ext" not in kwargs and "file_ext" not in kwargs:
            kwargs["file.ext"] = "html"
        super().__init__(
            pager=pager,
            threshold=threshold,
            make_blocking=make_blocking,
            **kwargs,
        )
