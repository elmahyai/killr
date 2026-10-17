"""Lifecycle statuses recorded in an installed package's help topics."""

from __future__ import annotations

from .rd import (
    LifecycleError,
    help_topics,
    lifecycle_token,
    match_which,
    require_r_packages,
    usage_function_names,
)


def pkg_lifecycle_statuses(package, which=None):
    """Rows of package, function, and lifecycle for one installed package."""
    require_r_packages(["vctrs"])
    chosen = match_which(which)
    if not isinstance(package, str):
        raise LifecycleError("is_string(package) is not TRUE")
    rows = []
    for _name, topic in help_topics(package):
        token = lifecycle_token(topic)
        for fun in usage_function_names(topic):
            rows.append((fun, token))
    keep_na = any(item is None for item in chosen)
    if not keep_na:
        rows = [(fun, token) for fun, token in rows if token is not None]
    rows = [(fun, token) for fun, token in rows if fun]
    rows = [(fun, token) for fun, token in rows if "\\method{" not in fun]
    allowed = set(chosen)
    rows = [
        (fun, token)
        for fun, token in rows
        if token in allowed or (token is None and keep_na)
    ]
    return [
        {"package": package, "fun": fun, "lifecycle": token}
        for fun, token in rows
    ]
