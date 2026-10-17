"""Expectation conditions, edition, and labels.

code arguments are callables. R would force an expression after the
expectation is set up. A failure outside a test raises Expectation.
Inside test_that the failure is recorded and the test continues.
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager


class TestthatError(Exception):
    """An error from testthat itself, not a failed expectation."""


class Expectation(Exception):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind
        self.message = message

    def __str__(self) -> str:
        return self.message


class SkipSignal(Exception):
    def __init__(self, message: str, empty: bool = False):
        super().__init__(message)
        self.message = message
        self.empty = empty


class _State:
    def __init__(self) -> None:
        self.edition: int | None = None
        self.reporter = None
        self.description: list[str] = []
        self.expectations = 0
        self.in_test = False
        self.snapshot = False
        self.package = ""
        self.handlers: list = []


STATE = _State()


def stop(message: str) -> None:
    raise TestthatError(message)


def edition_get() -> int:
    if STATE.edition is not None:
        return int(STATE.edition)
    env = os.environ.get("TESTTHAT_EDITION", "")
    if env.strip():
        return int(env)
    found = _edition_from_dir(os.getcwd())
    return found if found is not None else 2


def _edition_from_dir(start: str) -> int | None:
    path = os.path.abspath(start)
    for _ in range(8):
        desc = os.path.join(path, "DESCRIPTION")
        if os.path.isfile(desc):
            text = open(desc, encoding="utf-8", errors="replace").read()
            match = re.search(r"(?m)^Config/testthat/edition:\s*(\d+)", text)
            if match:
                return int(match.group(1))
            return 2
        parent = os.path.dirname(path)
        if parent == path:
            break
        path = parent
    return None


@contextmanager
def local_edition(x: int):
    if x not in (2, 3):
        stop("`x` must be a whole number between 2 and 3")
    old = STATE.edition
    STATE.edition = int(x)
    try:
        yield
    finally:
        STATE.edition = old


def label_of(value, label: str | None) -> str:
    if label is not None:
        return label
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if value is None:
        return "NULL"
    if isinstance(value, float) and value == int(value) and abs(value) < 1e15:
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return repr(value)


def _join(message) -> str:
    if isinstance(message, (list, tuple)):
        parts = []
        for part in message:
            if part is None:
                continue
            if isinstance(part, (list, tuple)):
                parts.append(_join(part))
            else:
                parts.append(str(part))
        return "\n".join(parts)
    return str(message)


def _deliver(kind: str, message: str) -> Expectation:
    exp = Expectation(kind, message)
    if STATE.handlers:
        STATE.handlers[-1](exp)
        return exp
    if kind in {"failure", "error"}:
        raise exp
    return exp


def pass_() -> None:
    _deliver("success", "success")
    return None


def fail(message="Failure has been forced", info=None) -> None:
    parts = [message]
    if info:
        parts.append(info)
    _deliver("failure", _join(parts))


def succeed(message="Success has been forced", info=None):
    parts = [message]
    if info:
        parts.append(info)
    return _deliver("success", _join(parts))


def expect(ok: bool, failure_message, info=None) -> None:
    if not isinstance(ok, bool):
        stop("`ok` must be TRUE or FALSE")
    if ok:
        return succeed(failure_message, info)
    return fail(failure_message, info)


def expectation(kind: str, message: str) -> Expectation:
    return _deliver(kind, _join(message))


def new_expectation(kind: str, message: str) -> Expectation:
    allowed = {"success", "failure", "error", "skip", "warning"}
    if kind not in allowed:
        stop("`type` must be one of success, failure, error, skip, warning")
    return Expectation(kind, _join(message))


def exp_signal(exp: Expectation) -> Expectation:
    return _deliver(exp.kind, exp.message)


def is_expectation(x) -> bool:
    return isinstance(x, Expectation)


def skip(message: str = "Skipping") -> None:
    text = message if isinstance(message, str) else "\n".join(message)
    raise SkipSignal("Reason: " + text)


def skip_empty() -> None:
    raise SkipSignal("Reason: empty test", empty=True)


@contextmanager
def handling(callback):
    STATE.handlers.append(callback)
    try:
        yield
    finally:
        STATE.handlers.pop()


def is_testing() -> bool:
    return os.environ.get("TESTTHAT") == "true"


def is_parallel() -> bool:
    return os.environ.get("TESTTHAT_IS_PARALLEL") == "true"


def is_checking() -> bool:
    return os.environ.get("TESTTHAT_IS_CHECKING") == "true"


def is_snapshot() -> bool:
    return os.environ.get("TESTTHAT_IS_SNAPSHOT") == "true"


def testing_package() -> str:
    return os.environ.get("TESTTHAT_PKG", "")
