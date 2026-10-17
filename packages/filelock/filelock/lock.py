"""Advisory locks from filelock 1.0.3.

Unix locks are POSIX ``fcntl`` record locks. ``fcntl.lockf`` is that call.
A second handle in this process shares the open descriptor. Closing any
descriptor would release every lock this process holds on the file.
"""

from __future__ import annotations

import errno
import math
import os
import time
import warnings
from fcntl import LOCK_EX, LOCK_NB, LOCK_SH, lockf

_INT_MAX = 2**31 - 1
_QUOTE = "\u2018"
_QUOTE_END = "\u2019"


class FilelockError(Exception):
    """An error raised with the installed filelock message."""


class _State:
    def __init__(self, path: str, fd: int, exclusive: bool):
        self.path = path
        self.fd = fd
        self.exclusive = exclusive
        self.refcount = 0


_locks: dict[str, _State] = {}


class FileLock:
    """One handle on a process lock. Several handles can share one file."""

    def __init__(self, state: _State):
        self.path = state.path
        self._state: _State | None = state
        state.refcount += 1

    def __del__(self):
        if getattr(self, "_state", None) is not None:
            try:
                unlock(self)
            except Exception:
                return

    def __str__(self) -> str:
        kind = "Unlocked lock on " if _is_unlocked(self) else "Lock on "
        return f"{kind}{_QUOTE}{self.path}{_QUOTE_END}"

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileLock):
            return NotImplemented
        return self.path == other.path and self._state is other._state


def _is_unlocked(lock: FileLock) -> bool:
    if lock._state is None:
        return True
    return _locks.get(lock.path) is not lock._state


def _dirname_basename(path: str) -> tuple[str, str]:
    """R ``dirname`` and ``basename``. Only ``/`` separates, and a trailing slash is dropped."""
    if path == "":
        return "", ""
    end = len(path)
    while end > 1 and path[end - 1] == "/":
        end -= 1
    trimmed = path[:end]
    slash = trimmed.rfind("/")
    if slash < 0:
        return ".", trimmed
    start = slash
    while start > 0 and trimmed[start - 1] == "/":
        start -= 1
    base = trimmed[slash + 1 :]
    directory = "/" if start == 0 else trimmed[:start]
    return directory, base


def _normalize_directory(directory: str) -> str:
    expanded = os.path.expanduser(directory)
    if os.path.exists(expanded):
        return os.path.realpath(expanded)
    warnings.warn(
        f'path[1]="{directory}": No such file or directory',
        stacklevel=3,
    )
    raise FilelockError(f"Directory of lock file does not exist: '{directory}'")


def _join(directory: str, base: str) -> str:
    if directory == "/":
        return "/" + base
    if directory.endswith("/"):
        return directory + base
    return directory + "/" + base


def _flag(value) -> bool:
    return isinstance(value, bool)


def _check_timeout(value) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FilelockError("is_timeout(timeout) is not TRUE")
    if isinstance(value, float) and math.isnan(value):
        raise FilelockError("is_timeout(timeout) is not TRUE")
    if value < 0:
        raise FilelockError("is_timeout(timeout) is not TRUE")


def _timeout_ms(value) -> int:
    """``as.integer(timeout)`` after ``Inf`` has been stored as ``-1``."""
    if math.isinf(value):
        return -1
    truncated = math.trunc(float(value))
    if truncated > _INT_MAX:
        warnings.warn("NAs introduced by coercion to integer range", stacklevel=3)
        return -1
    return truncated


def _acquire(fd: int, exclusive: bool, timeout_ms: int) -> bool:
    command = LOCK_EX if exclusive else LOCK_SH
    deadline = None if timeout_ms < 0 else time.monotonic() + timeout_ms / 1000.0
    while True:
        try:
            lockf(fd, command | LOCK_NB)
            return True
        except OSError as error:
            if error.errno not in (errno.EAGAIN, errno.EACCES):
                raise
            if deadline is None:
                time.sleep(0.05)
                continue
            if time.monotonic() >= deadline:
                return False
            time.sleep(min(0.05, deadline - time.monotonic()))


def lock(path, exclusive: bool = True, timeout: float = math.inf):
    """Lock ``path``, creating it when the directory exists. ``None`` means the wait timed out."""
    if not isinstance(path, str):
        raise FilelockError("is_string(path) is not TRUE")
    if not _flag(exclusive):
        raise FilelockError("is_flag(exclusive) is not TRUE")
    _check_timeout(timeout)
    directory, base = _dirname_basename(path)
    full = _join(_normalize_directory(directory), base)
    timeout_ms = _timeout_ms(timeout)
    current = _locks.get(full)
    if current is not None:
        if current.exclusive == exclusive:
            return FileLock(current)
        if exclusive:
            raise FilelockError("File already has a shared lock")
        raise FilelockError("File already has an exclusive lock")
    try:
        fd = os.open(full, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as error:
        raise FilelockError(f"Cannot open lock file: {error.strerror}") from error
    try:
        acquired = _acquire(fd, exclusive, timeout_ms)
    except OSError as error:
        os.close(fd)
        raise FilelockError(f"Cannot lock file: '{full}': {error.strerror}") from error
    if not acquired:
        os.close(fd)
        return None
    state = _State(full, fd, exclusive)
    _locks[full] = state
    return FileLock(state)


def unlock(lock) -> bool:
    """Release one handle. The file stays locked until the last handle is released."""
    if not isinstance(lock, FileLock):
        raise FilelockError("`unlock()` needs a lock object, not a file name")
    state = lock._state
    lock._state = None
    if state is None:
        return True
    state.refcount -= 1
    if state.refcount <= 0:
        _locks.pop(state.path, None)
        os.close(state.fd)
    return True
