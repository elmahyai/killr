"""with_collate and local_collate (R's collate.R): the LC_COLLATE category."""

from __future__ import annotations

from .locale_settings import local_locale, with_locale


def with_collate(new: str, code):
    return with_locale({"LC_COLLATE": new}, code)


def local_collate(new: str, *, _local_envir=None):
    return local_locale({"LC_COLLATE": new}, _local_envir=_local_envir)
