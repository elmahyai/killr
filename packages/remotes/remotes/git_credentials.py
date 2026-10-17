"""Return the git credentials stored for remotes."""

from __future__ import annotations

options: dict = {}


def git_credentials():
    """Return the ``remotes.git_credentials`` option, or None when it is unset."""

    return options.get("remotes.git_credentials", None)
