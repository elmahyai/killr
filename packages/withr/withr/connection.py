"""with_connection and local_connection (R's connection.R).

R's connections are handles into R's connection table. Here a connection is a
Python object with a close() method, such as a file opened with open(). The
translated behaviour is closing it when the block or frame exits. R's
connection numbers and showConnections() are not reproduced.
"""

from __future__ import annotations

from ._scope import current, force


def with_connection(con, code):
    """Run ``code(**con)`` and close each named connection afterwards."""
    if not isinstance(con, dict) or not all(
        isinstance(name, str) and name.isidentifier() for name in con
    ):
        raise ValueError("all connections must be named with identifier names")
    try:
        if not callable(code):
            raise TypeError("code must be a callable that takes the named connections")
        return code(**con)
    finally:
        for connection in con.values():
            connection.close()


def local_connection(con, *, _local_envir=None):
    current(_local_envir).add(lambda: con.close())
    return con


def with_db_connection(con, code):
    """Run ``code`` with named SQLAlchemy connections, then close them."""
    if not isinstance(con, dict) or not all(
        isinstance(name, str) and name.isidentifier() for name in con
    ):
        raise ValueError("all connections must be named with identifier names")
    try:
        if not callable(code):
            raise TypeError("code must be a callable that takes the named connections")
        return code(**con)
    finally:
        for connection in con.values():
            connection.close()


def local_db_connection(con, *, _local_envir=None):
    """Register a SQLAlchemy connection to close when its scope exits."""
    current(_local_envir).add(lambda: con.close())
    return con
