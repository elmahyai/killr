"""with_language and local_language (R's language.R): the LANGUAGE variable.

R also resets its gettext cache and warns when NLS is missing or LC_ALL is C.
Those are not reproduced: Python does not load R's message catalogues.
"""

from __future__ import annotations

from ._scope import force, private_scope
from .envvar import local_envvar


def local_language(lang: str, *, _local_envir=None) -> None:
    if not isinstance(lang, str):
        raise TypeError("`lang` must be a string")
    lang = lang.replace("-", "_")
    local_envvar({"LANGUAGE": lang}, _local_envir=_local_envir)


def with_language(lang: str, code):
    with private_scope() as frame:
        local_language(lang, _local_envir=frame)
        return force(code)
