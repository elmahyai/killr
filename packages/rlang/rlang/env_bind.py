"""Bind symbols to objects in an environment (``env_bind``)."""

from __future__ import annotations

from typing import Any

from rlang import Env, Named, RLangError, Splice, Zap, zap


def _stop_input_type(x: object, arg: str) -> None:
    if isinstance(x, list):
        friendly = "a list"
    elif isinstance(x, dict) and not isinstance(x, Env):
        friendly = "a dictionary"
    else:
        friendly = f"a {type(x).__name__}"
    raise RLangError(f"`{arg}` must be an environment, not {friendly}.")


def _value_pairs(value: object) -> list[tuple[str, object]]:
    if isinstance(value, dict) and not isinstance(value, Env):
        return [(str(key), item) for key, item in value.items()]
    if isinstance(value, Named):
        names = value.names
        if len(names) != len(value):
            raise RLangError("Can't bind data because some elements are not named.")
        return [(name, value[index]) for index, name in enumerate(names) if name]
    raise RLangError("Can't bind data because some elements are not named.")


def _collect_named_values(*args: object, **kwargs: object) -> list[tuple[str, object]]:
    pairs: list[tuple[str, object]] = []
    for arg in args:
        if isinstance(arg, Splice):
            for item in arg:
                pairs.extend(_value_pairs(item))
        else:
            pairs.extend(_value_pairs(arg))
    for key, value in kwargs.items():
        pairs.append((str(key), value))
    return pairs


def _binding_old(env: Env, name: str) -> object:
    if name not in env:
        return zap()
    return env[name]


def env_bind(env: Env, *args: object, **kwargs: object) -> dict[str, object]:
    if not isinstance(env, Env):
        _stop_input_type(env, ".env")

    pairs = _collect_named_values(*args, **kwargs)
    if not pairs:
        return {}

    old: dict[str, object] = {}
    for name, value in pairs:
        if not name:
            raise RLangError("Can't bind data because some elements are not named.")
        old[name] = _binding_old(env, name)
        if isinstance(value, Zap):
            env.pop(name, None)
        else:
            env[name] = value
    return old
