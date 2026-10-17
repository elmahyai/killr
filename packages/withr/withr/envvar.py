"""with_envvar and local_envvar (R's env.R)."""

from __future__ import annotations

import os

from .factory import local_, with_

_ACTIONS = ("replace", "prefix", "suffix")


def _as_envvars(envs) -> dict[str, str | None]:
    """Named values as a dict; None means unset. The last duplicate wins."""
    if not envs:
        return {}
    items = envs.items() if isinstance(envs, dict) else list(envs)
    return {str(name): None if value is None else str(value) for name, value in items}


def get_envvar(envs, **_):
    """The current values of the named variables; None where unset."""
    return {name: os.environ.get(name) for name in _as_envvars(envs)}


def set_envvar(envs, action: str = "replace"):
    """Set (or unset, for None) the variables. Returns the old values as a dict."""
    if action not in _ACTIONS:
        raise ValueError('`action` must be "replace", "prefix" or "suffix"')
    envs = _as_envvars(envs)
    if not envs:
        return {}
    old = get_envvar(envs)
    new = dict(envs)
    if action != "replace":
        for name, value in envs.items():
            previous = old[name]
            if value is not None and previous is not None:
                new[name] = f"{value} {previous}" if action == "prefix" else f"{previous} {value}"
    for name, value in new.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    return old


with_envvar = with_(set_envvar, get_fn=get_envvar)
local_envvar = local_(set_envvar, get_fn=get_envvar, dots=True)
