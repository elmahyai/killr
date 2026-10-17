"""Memoised functions.

A memoised function saves the result of a call and returns that result when
the same arguments are bound again. One-sided formulas in R are zero-argument
callables here: they are called on every lookup and mixed into the cache key.
"""

from __future__ import annotations

import inspect
import time
from typing import Any, Callable

from memoise._cache import CacheMem, KeyMissing, WrappedCache, is_old_cache
from memoise._hash import hash_object


class Memoised:
    def __init__(
        self,
        fn: Callable[..., Any],
        cache: Any,
        hash_fn: Callable[[Any], str],
        omit: tuple[str, ...],
        extras: tuple[Callable[[], Any], ...],
        f_hash: str,
    ) -> None:
        self._f = fn
        self._cache = cache
        self._hash = hash_fn
        self._omit = omit
        self._extras = extras
        self._f_hash = f_hash
        self._signature = inspect.signature(fn)
        self.__signature__ = self._signature
        self.__name__ = getattr(fn, "__name__", "memoised")
        self.__doc__ = getattr(fn, "__doc__", None)

    def _key(self, *args: Any, **kwargs: Any) -> str:
        bound = self._signature.bind(*args, **kwargs)
        bound.apply_defaults()
        arguments = dict(bound.arguments)
        for name in self._omit:
            arguments.pop(name, None)
        extra_values = tuple(extra() for extra in self._extras)
        return self._hash((self._f_hash, arguments, extra_values))

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        key = self._key(*args, **kwargs)
        found = self._cache.get(key)
        if isinstance(found, KeyMissing):
            found = self._f(*args, **kwargs)
            self._cache.set(key, found)
        return found

    def __repr__(self) -> str:
        try:
            body = inspect.getsource(self._f).rstrip()
        except (OSError, TypeError):
            body = f"{self.__name__}{self._signature}"
        return f"Memoised Function:\n{body}"


def _const_plain(value: Any) -> Any:
    nested = getattr(value, "co_code", None)
    if nested is not None:
        return {"code": value.co_code.hex(), "consts": [_const_plain(item) for item in value.co_consts]}
    if isinstance(value, tuple):
        return [_const_plain(item) for item in value]
    if isinstance(value, bytes):
        return value.hex()
    return value


def _function_hash(fn: Callable[..., Any]) -> str:
    code = getattr(fn, "__code__", None)
    if code is None:
        payload = {"builtin": getattr(fn, "__qualname__", repr(fn))}
    else:
        payload = {
            "sig": str(inspect.signature(fn)),
            "code": code.co_code.hex(),
            "names": list(code.co_names),
            "consts": [_const_plain(item) for item in code.co_consts],
        }
    return hash_object(payload)


def _omit_names(omit_args: Any) -> tuple[str, ...]:
    if omit_args is None:
        return ()
    if isinstance(omit_args, str):
        return (omit_args,)
    return tuple(omit_args)


def memoise(
    f: Callable[..., Any],
    *extras: Callable[[], Any],
    envir: Any = None,
    cache: Any = None,
    omit_args: Any = (),
    hash: Callable[[Any], str] | None = None,
) -> Memoised:
    if is_memoised(f):
        raise ValueError("`f` must not be memoised.")
    for extra in extras:
        if not callable(extra):
            raise ValueError(f"`{extra!r}` must be a formula.")
    hash_fn = hash if hash is not None else (lambda obj: hash_object(obj))
    if cache is None:
        cache = CacheMem(max_size=1024 * 1024**2)
    elif is_old_cache(cache):
        hash_fn = cache.digest
        cache = WrappedCache(cache)
    # envir is the parent of the memoised function in R. The original function
    # already closes over its cells, so the wrapper calls it directly.
    del envir
    return Memoised(
        f,
        cache=cache,
        hash_fn=hash_fn,
        omit=_omit_names(omit_args),
        extras=extras,
        f_hash=_function_hash(f),
    )


memoize = memoise


def is_memoised(f: Any) -> bool:
    return isinstance(f, Memoised)


is_memoized = is_memoised


def forget(f: Any) -> bool:
    if not is_memoised(f):
        return False
    f._cache.reset()
    return True


def has_cache(f: Any) -> Callable[..., bool]:
    if not is_memoised(f):
        raise ValueError("`f` is not a memoised function!")

    def probe(*args: Any, **kwargs: Any) -> bool:
        return f._cache.exists(f._key(*args, **kwargs))

    return probe


def drop_cache(f: Any) -> Callable[..., bool]:
    if not is_memoised(f):
        raise ValueError("`f` is not a memoised function!")

    def drop(*args: Any, **kwargs: Any) -> bool:
        key = f._key(*args, **kwargs)
        if f._cache.exists(key):
            f._cache.remove(key)
            return True
        return False

    return drop


def timeout(seconds: float, current: float | None = None) -> float:
    if current is None:
        current = time.time()
    value = (current - current % seconds) // seconds
    if value == int(value):
        return int(value)
    return value
