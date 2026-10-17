"""with_dir and local_dir (R's dir.R): the working directory."""

from __future__ import annotations

import os

from .factory import local_, with_


def set_dir(new: str) -> str:
    """setwd(new). Returns the previous working directory."""
    old = os.getcwd()
    os.chdir(new)
    return old


with_dir = with_(set_dir)
local_dir = local_(set_dir)
