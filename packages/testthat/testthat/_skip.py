"""Skips. skip() raises SkipSignal, which test_that records."""

from __future__ import annotations

import os
import platform
import sys

from testthat._core import STATE, SkipSignal, skip, stop


def skip_if(condition, message=None) -> None:
    if message is None:
        message = "condition is TRUE"
    if condition is True:
        skip(message)


def skip_if_not(condition, message=None) -> None:
    if message is None:
        message = "condition is not TRUE"
    if condition is not True:
        skip(message)


def skip_if_not_installed(pkg, minimum_version=None) -> None:
    if pkg in sys.modules or _importable(pkg):
        if minimum_version is not None:
            skip(f"Installed {pkg} version check is not compared here")
        return
    skip(f"{{{pkg}}} is not installed")


def _importable(pkg: str) -> bool:
    try:
        __import__(pkg)
    except Exception:
        return False
    return True


def skip_if_offline(host="captive.apple.com") -> None:
    skip_on_cran()
    stop("The package \"curl\" is required.")


def skip_if_translated(message) -> None:
    """Translations are not applied. The English message is never skipped."""
    return None


def on_cran() -> bool:
    """Unset NOT_CRAN counts as CRAN when this process is not a terminal."""
    env = os.environ.get("NOT_CRAN", "")
    if env == "":
        return not sys.stdout.isatty()
    return env.lower() not in {"true", "1", "t", "yes"}


def skip_on_cran() -> None:
    if on_cran():
        skip("On CRAN")


def local_on_cran(on_cran=True):
    from contextlib import contextmanager

    @contextmanager
    def _ctx():
        old = os.environ.get("NOT_CRAN")
        os.environ["NOT_CRAN"] = "false" if on_cran else "true"
        try:
            yield
        finally:
            if old is None:
                os.environ.pop("NOT_CRAN", None)
            else:
                os.environ["NOT_CRAN"] = old

    return _ctx()


def skip_on_bioc() -> None:
    if os.environ.get("IS_BIOC_BUILD_MACHINE") == "true":
        skip("On Bioconductor")


def skip_on_covr() -> None:
    if os.environ.get("R_COVR") == "true":
        skip("On covr")


def skip_on_ci() -> None:
    if os.environ.get("CI") == "true":
        skip("On CI")


def skip_on_os(os_name) -> None:
    names = os_name if isinstance(os_name, (list, tuple)) else [os_name]
    current = {"linux": "linux", "windows": "windows", "darwin": "mac"}.get(platform.system().lower(), platform.system().lower())
    if current in names or platform.system().lower() in names:
        label = {"linux": "Linux", "mac": "Mac", "windows": "Windows"}.get(current, current)
        skip(f"On {label}")
    return True


def skip_on_travis() -> None:
    if os.environ.get("TRAVIS") == "true":
        skip("On Travis")


def skip_on_appveyor() -> None:
    if os.environ.get("APPVEYOR") == "true":
        skip("On Appveyor")


def skip_unless_r(spec) -> None:
    """Skip when the host R version does not satisfy a spec such as ``>= 4.0.0``."""
    text = str(spec).strip()
    parts = text.split()
    if len(parts) != 2:
        stop(
            "`spec` must be an valid version specification, like \">= 4.0.0\", not\n"
            f"\"{text}\"."
        )
    current = os.environ.get("TESTTHAT_R_VERSION", "4.5.0")
    if not _satisfies(current, parts[0], parts[1]):
        skip(f"Current R version ({current}) does not satisfy requirement ({parts[0]} {parts[1]})")


def _satisfies(current: str, op: str, needed: str) -> bool:
    ops = {
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        "==": lambda a, b: a == b,
    }
    if op not in ops:
        stop(f"`spec` must be an valid version specification, like \">= 4.0.0\", not\n\"{op} {needed}\".")
    return ops[op](_parts(current), _parts(needed))


def _parts(text: str) -> tuple[int, ...]:
    bits = []
    for part in str(text).split("."):
        digits = ""
        for char in part:
            if char.isdigit():
                digits += char
            else:
                break
        bits.append(int(digits or "0"))
    return tuple(bits)


def _older(current: str, needed: str) -> bool:
    def parts(text: str) -> tuple[int, ...]:
        return tuple(int(piece) for piece in text.split(".") if piece.isdigit())
    return parts(current) < parts(needed)
