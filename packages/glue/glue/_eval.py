"""Evaluate a brace as a Python expression against the names in scope."""

from __future__ import annotations

from typing import Any

from glue._scan import GlueError
from glue._text import rewrite_names


def identity_transformer(text: str, envir: dict[str, Any] | None = None) -> Any:
    """Evaluate ``text`` as Python. A name that is an exact key is returned as stored."""

    env = {} if envir is None else envir
    if text in env:
        return env[text]
    stripped = text.strip()
    if stripped in env:
        return env[stripped]
    code, extra = rewrite_names(text, env)
    local = dict(env)
    local.update(extra)
    try:
        return eval(code, {"__builtins__": __builtins__}, local)  # noqa: S307
    except SyntaxError as exc:
        raise GlueError("Failed to parse glue component") from exc
    except GlueError:
        raise
    except Exception as exc:
        raise GlueError(f"Failed to evaluate glue component {{{text}}}") from exc


def get_transformer(text: str, envir: dict[str, Any] | None = None) -> Any:
    """Look up ``text`` as one name. The text is not evaluated."""

    env = {} if envir is None else envir
    if text not in env:
        raise GlueError(f"object '{text}' not found")
    return env[text]
