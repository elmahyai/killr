"""Evaluate an expression in an environment (``eval_bare``)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rlang import Env, RLangError, caller_env
from rlang.as_label import Call
from rlang.as_string import Symbol


def _r_add(x: Any, y: Any) -> Any:
    return x + y


def _r_sub(x: Any, y: Any) -> Any:
    return x - y


def _r_mul(x: Any, y: Any) -> Any:
    return x * y


def _r_div(x: Any, y: Any) -> Any:
    return x / y


_R_BASE: dict[str, Any] = {
    "+": _r_add,
    "-": _r_sub,
    "*": _r_mul,
    "/": _r_div,
}


def _as_env(env: Mapping[str, Any] | Env) -> Mapping[str, Any]:
    if isinstance(env, Env):
        return env
    if isinstance(env, Mapping):
        return env
    raise RLangError("`env` must be an environment.")


def _env_parent(env: Mapping[str, Any]) -> Mapping[str, Any] | None:
    parent = getattr(env, "parent", None)
    if parent is None:
        return None
    return _as_env(parent)


def _env_lookup(env: Mapping[str, Any], name: str) -> Any:
    if name in env:
        return env[name]
    parent = _env_parent(env)
    if parent is not None:
        return _env_lookup(parent, name)
    if name in _R_BASE:
        return _R_BASE[name]
    raise RLangError(f"object '{name}' not found")


def _eval_expr(expr: Any, env: Mapping[str, Any]) -> Any:
    if isinstance(expr, Symbol):
        return _env_lookup(env, expr._name)
    if isinstance(expr, Call):
        head = _eval_expr(expr[1], env)
        args = [_eval_expr(expr[index], env) for index in range(2, len(expr) + 1)]
        if callable(head):
            return head(*args)
        raise RLangError(f"attempt to apply non-function of type '{type(head).__name__}'")
    return expr


def eval_bare(expr: Any, env: Mapping[str, Any] | Env | None = None) -> Any:
    """Evaluate ``expr`` in ``env`` with bare (single-frame) semantics."""
    if env is None:
        env = caller_env()
    return _eval_expr(expr, _as_env(env))
