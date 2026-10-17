"""with_timezone and local_timezone (R's timezone.R): the TZ variable.

R caches the system time zone; Python reads TZ through time.tzset(), which
this module calls after each change and each restore.
"""

from __future__ import annotations

import time

from .envvar import set_envvar
from .factory import local_, with_


def set_timezone(tz: str):
    old = set_envvar({"TZ": tz})
    time.tzset()
    return old


def reset_timezone(old) -> None:
    set_envvar(old)
    time.tzset()


with_timezone = with_(set_timezone, reset_timezone)
local_timezone = local_(set_timezone, reset_timezone)
