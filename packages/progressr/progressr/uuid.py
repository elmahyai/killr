"""Session identifiers. They include time, pid, and a random draw, so they do not equal R."""

from __future__ import annotations

import os
import random
import socket
import tempfile
import time

from digest import digest


_SESSIONS: dict[str, str] = {}
_SOURCES: dict[str, object] = {}
_RNG = random.Random()


def uuid(source, keep_source: bool = False) -> str:
    """Format an md5 from digest.digest as 8-4-4-4-12."""
    text = source if isinstance(source, str) else repr(source)
    hashed = digest(text, serialize=False)
    formatted = (
        f"{hashed[0:8]}-{hashed[8:12]}-{hashed[12:16]}-"
        f"{hashed[16:20]}-{hashed[20:32]}"
    )
    if keep_source:
        _SOURCES[formatted] = source
    return formatted


def session_uuid(pid=None, attributes: bool = False) -> str:
    """One identifier per process id. Generated on first use."""
    if pid is None:
        pid = os.getpid()
    key = str(pid)
    if key not in _SESSIONS:
        host = socket.gethostname()
        info = {
            "host": host,
            "time": time.time(),
            "tempdir": tempfile.gettempdir(),
            "pid": pid,
            "random": _RNG.randint(1, 2**31 - 1),
        }
        _SESSIONS[key] = uuid(info, keep_source=True)
    value = _SESSIONS[key]
    if attributes:
        return value
    return value


def progressor_uuid(identifier, attributes: bool = False) -> str:
    source = {"session_uuid": session_uuid(), "id": identifier}
    return uuid(source, keep_source=attributes)
