"""Check whether the RStudio IDE is running.

``isAvailable`` is false when R's ``.Platform$GUI`` is not ``"RStudio"``.
That is this process: Python is not the embedded R session. ``RSTUDIO=1``
does not change the result. A false GUI check does not read
``version_needed``. ``child_ok`` is combined with the job test by R's
``&&``.
"""

from __future__ import annotations

import math
import os


class RstudioapiError(Exception):
    """An error raised with the installed rstudioapi message."""


def isAvailable(version_needed=None, child_ok=False):
    """Return whether RStudio is available.

    Outside the IDE this is false. ``version_needed`` is accepted and not
    consulted, matching ``FALSE && version_ok(version_needed)``. When
    ``child_ok`` is true and this process is an RStudio job, the call asks
    the parent session. With no parent connection that request stops.
    """
    flag = _and_flag(child_ok, _is_job)
    if flag is None:
        raise RstudioapiError("missing value where TRUE/FALSE needed")
    if flag:
        return _call_remote()
    return False


def _is_job() -> bool:
    return _is_background_job() or _is_workbench_job()


def _is_background_job() -> bool:
    # Sys.getenv(..., unset = NA) is missing only when the variable is unset.
    # An empty value is not NA, so the process is a background job.
    return "RSTUDIOAPI_IPC_REQUESTS_FILE" in os.environ


def _is_workbench_job() -> bool:
    return os.environ.get("RSTUDIO_WORKBENCH_JOB", "") == "1"


def _call_remote():
    request = os.environ.get("RSTUDIOAPI_IPC_REQUESTS_FILE")
    response = os.environ.get("RSTUDIOAPI_IPC_RESPONSE_FILE")
    secret = os.environ.get("RSTUDIOAPI_IPC_SHARED_SECRET")
    if request is None or response is None or secret is None:
        raise RstudioapiError(
            "internal error: callRemote() called without remote connection"
        )
    raise RstudioapiError("RStudio did not respond to rstudioapi IPC request")


def _and_flag(left, right_fn):
    """R ``left && right()``. The right side runs unless left is false."""
    coerced = _logical1(left)
    if coerced is False:
        return False
    right = bool(right_fn())
    if coerced is True:
        return right
    if not right:
        return False
    return None


def _logical1(value):
    """Coerce one value the way ``&&`` coerces its left operand."""
    if isinstance(value, (list, tuple)):
        return _logical1_vector(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return value != 0.0
    if isinstance(value, complex):
        if math.isnan(value.real) or math.isnan(value.imag):
            return None
        return value.real != 0.0 or value.imag != 0.0
    raise RstudioapiError("invalid 'x' type in 'x && y'")


def _logical1_vector(values):
    if len(values) == 0:
        return None
    for item in values:
        if not isinstance(item, (bool, int, float, complex)):
            raise RstudioapiError("invalid 'x' type in 'x && y'")
    if len(values) != 1:
        raise RstudioapiError(
            f"'length = {len(values)}' in coercion to 'logical(1)'"
        )
    return _logical1(values[0])
