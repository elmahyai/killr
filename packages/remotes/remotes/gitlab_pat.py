"""GitLab personal access token from the GITLAB_PAT environment variable."""

from __future__ import annotations

import os
import sys


def gitlab_pat(quiet: bool = True) -> str | None:
    """Return GITLAB_PAT when it has non-zero length, otherwise None.

    When quiet is false and a token is present, write
    "Using GitLab PAT from envvar GITLAB_PAT" to stderr, as R's message() does.
    An unset variable and an empty string both return None.
    """
    pat = os.environ.get("GITLAB_PAT")
    if pat is not None and len(pat) > 0:
        if not quiet:
            print("Using GitLab PAT from envvar GITLAB_PAT", file=sys.stderr)
        return pat
    return None
