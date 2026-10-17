"""Set or clear TCP_NODELAY on a socket (gtools 3.9.5 ``setTCPNoDelay``)."""

from __future__ import annotations

import ctypes
import math
import os
import socket as _socket
import warnings

_NA_INTEGER = -2147483648

_libc = ctypes.CDLL(None, use_errno=True)
_libc.setsockopt.argtypes = [
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(ctypes.c_int),
    ctypes.c_uint32,
]
_libc.setsockopt.restype = ctypes.c_int


class Socket:
    """Descriptor, host, and port of an R ``make.socket`` value."""

    def __init__(self, socket, host="", port=0):
        self.socket = socket
        self.host = host
        self.port = port


def _descriptor(sock) -> int:
    if isinstance(sock, _socket.socket):
        return sock.fileno()
    if isinstance(sock, Socket):
        inner = sock.socket
        if isinstance(inner, _socket.socket):
            return inner.fileno()
        return int(inner)
    raise RuntimeError("socket must be a socket object")


def _one_integer(item):
    """One R ``as.integer`` element. ``None`` means NA."""
    if item is None:
        return None, False
    if isinstance(item, bool):
        return (1 if item else 0), False
    if isinstance(item, int):
        if item == _NA_INTEGER:
            return None, False
        return item, False
    if isinstance(item, float):
        if math.isnan(item) or math.isinf(item):
            return None, True
        return int(math.trunc(item)), False
    if isinstance(item, str):
        return None, True
    raise TypeError("invalid TCP_NODELAY value")


def _flag(value) -> int:
    items = list(value) if isinstance(value, (list, tuple)) else [value]
    if not items:
        raise RuntimeError("NAs in foreign function call (arg 2)")
    integers = []
    warned = False
    for item in items:
        converted, do_warn = _one_integer(item)
        if do_warn and not warned:
            warnings.warn("NAs introduced by coercion", RuntimeWarning)
            warned = True
        integers.append(converted)
    if any(item is None for item in integers):
        raise RuntimeError("NAs in foreign function call (arg 2)")
    return 1 if integers[0] != 0 else 0


def _apply(fd: int, flag: int) -> str:
    # A successful setsockopt does not clear errno. The text is SUCCESS
    # only when errno is 0; otherwise it is the previous strerror text.
    stored = ctypes.c_int(flag)
    rc = _libc.setsockopt(
        int(fd),
        _socket.IPPROTO_TCP,
        _socket.TCP_NODELAY,
        ctypes.byref(stored),
        ctypes.sizeof(stored),
    )
    err = ctypes.get_errno()
    text = "SUCCESS" if err == 0 else os.strerror(err)
    if rc != 0:
        raise RuntimeError(text)
    return text


def setTCPNoDelay(sock, value=True):
    """Set TCP_NODELAY when ``value`` is nonzero, and return the status text."""
    fd = _descriptor(sock)
    flag = _flag(value)
    return _apply(fd, flag)
