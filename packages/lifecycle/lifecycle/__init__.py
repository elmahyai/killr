"""Lifecycle stages, deprecation, help-topic statuses, and the linter errors."""

from __future__ import annotations

import re
import warnings

from rlang import arg_match0

from lifecycle.lint import lifecycle_linter, lint_lifecycle, lint_tidyverse_lifecycle
from lifecycle.rd import LifecycleError
from lifecycle.statuses import pkg_lifecycle_statuses

_MISSING = object()
_warned: set[str] = set()
_warnings: list[str] = []
options = {"lifecycle_verbosity": "default"}


def deprecated():
    return _MISSING


def is_present(arg) -> bool:
    return arg is not _MISSING


def _upcase1(stage: str) -> str:
    return stage[:1].upper() + stage[1:]


def badge(stage: str) -> str:
    old = ("maturing", "questioning", "soft-deprecated", "defunct", "retired")
    if stage not in old:
        stage = arg_match0(stage, ["experimental", "stable", "superseded", "deprecated"])
    url = f"https://lifecycle.r-lib.org/articles/stages.html#{stage}"
    image = f"lifecycle-{stage}.svg"
    html = f"\\href{{{url}}}{{\\figure{{{image}}}{{options: alt='[{_upcase1(stage)}]'}}}}"
    text = f"\\strong{{[{_upcase1(stage)}]}}"
    return f"\\ifelse{{html}}{{{html}}}{{{text}}}"


def _message(when: str, what: str, replacement=None, package="<NA>", defunct=False) -> str:
    if "(" in what and what.endswith(")"):
        fn = what
        arg = None
        reason = None
        if " = " in what:
            head, reason = what.split(" = ", 1)
            fn = head.split("(")[0] + "()"
            arg = head.split("(")[1]
            reason = reason.rstrip(")")
        elif "(" in what and what.index("(") + 1 != what.index(")"):
            fn = what.split("(")[0] + "()"
            arg = what[what.index("(") + 1:what.index(")")]
        label = fn if fn.startswith("`") else f"`{fn}`" if fn.endswith("()") else f"`{fn}()`"
        if not label.endswith("`") and label.endswith("()"):
            label = f"`{fn}`"
        if arg is None:
            if defunct:
                line = f"{label} was deprecated in {package} {when} and is now defunct."
            else:
                line = f"{label} was deprecated in {package} {when}."
        else:
            reason = reason or "is deprecated"
            line = f"The `{arg}` argument of {label} {reason} as of {package} {when}."
    else:
        line = f"`{what}` was deprecated in {package} {when}."
    if replacement:
        line += f"\n\u2139 Please use `{replacement}` instead."
    return line


def deprecate_warn(when, what, with_=None, details=None, id=None, always=False, package="<NA>", **_kwargs):
    text = _message(when, what, with_, package=package)
    key = id or text
    force = always or options.get("lifecycle_verbosity") == "warning"
    if not force and key in _warned:
        return None
    _warned.add(key)
    _warnings[:] = [text]
    warnings.warn(text, stacklevel=2)
    return None


def deprecate_soft(when, what, with_=None, details=None, id=None, package="<NA>", **kwargs):
    return deprecate_warn(when, what, with_, details, id, always=False, package=package)


def deprecate_stop(when, what, with_=None, details=None, **_kwargs):
    raise LifecycleError(_message(when, what, with_, defunct=True))


def signal_stage(stage, what, with_=None, env=None):
    return None


def signal_experimental(when, what, env=None):
    deprecate_soft(
        "1.1.0",
        "signal_experimental()",
        "signal_stage()",
        id="lifecycle_signal_experimental",
        package="lifecycle",
    )
    return signal_stage("experimental", what)


def signal_superseded(when, what, env=None):
    deprecate_soft(
        "1.1.0",
        "signal_superseded()",
        "signal_stage()",
        id="lifecycle_signal_superseded",
        package="lifecycle",
    )
    return signal_stage("superseded", what)


def last_lifecycle_warnings():
    return list(_warnings)


def expect_deprecated(fn, regexp=None):
    options["lifecycle_verbosity"] = "warning"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fn()
    if not caught:
        raise RuntimeError("Expected a warning.")
    text = str(caught[-1].message)
    if regexp is not None and re.search(regexp, text) is None:
        raise RuntimeError(f"Expected warning matching {regexp!r}. Actual: {text}")
    return None


def expect_defunct(fn):
    try:
        fn()
    except LifecycleError:
        return None
    raise RuntimeError("Expected an error.")
