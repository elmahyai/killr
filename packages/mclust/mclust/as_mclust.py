"""Conversions between ``Mclust`` and ``densityMclust`` objects."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .density import dens

__all__ = [
    "as_mclust",
    "as_mclust_default",
    "as_mclust_density_mclust",
    "as_density_mclust",
    "as_density_mclust_default",
    "as_density_mclust_mclust",
]


def _classes(obj: Any) -> list[str]:
    if isinstance(obj, Mapping):
        value = obj.get("_class", obj.get("class", ()))
    else:
        value = getattr(obj, "_class", getattr(obj, "class", ()))
    if isinstance(value, str):
        return [value]
    return list(value) if value is not None else []


def _copy_object(obj: Any) -> dict[str, Any]:
    if isinstance(obj, Mapping):
        return dict(obj)
    return dict(vars(obj))


def as_mclust(x: Any, **kwargs: Any) -> Any:
    """Coerce an object to the ``Mclust`` representation."""
    del kwargs
    if "densityMclust" in _classes(x):
        return as_mclust_density_mclust(x)
    return as_mclust_default(x)


def as_mclust_default(x: Any, **kwargs: Any) -> Any:
    """Return an existing Mclust object or reject the coercion."""
    del kwargs
    if "Mclust" in _classes(x):
        return x
    raise TypeError("argument 'x' cannot be coerced to class 'Mclust'")


def as_mclust_density_mclust(x: Any, **kwargs: Any) -> dict[str, Any]:
    """Mark a densityMclust object as an Mclust object."""
    del kwargs
    out = _copy_object(x)
    old = _classes(x)
    out["_class"] = ["Mclust"] + ([old[0]] if old else [])
    return out


def as_density_mclust(x: Any, **kwargs: Any) -> Any:
    """Coerce an object to the ``densityMclust`` representation."""
    del kwargs
    if "Mclust" in _classes(x):
        return as_density_mclust_mclust(x)
    return as_density_mclust_default(x)


def as_density_mclust_default(x: Any, **kwargs: Any) -> Any:
    """Return an existing densityMclust object or reject the coercion."""
    del kwargs
    if "densityMclust" in _classes(x):
        return x
    raise TypeError("argument 'x' cannot be coerced to class 'densityMclust'")


def as_density_mclust_mclust(x: Any, **kwargs: Any) -> dict[str, Any]:
    """Mark an Mclust object as densityMclust and evaluate its density."""
    del kwargs
    out = _copy_object(x)
    old = _classes(x)
    out["_class"] = ["densityMclust"] + old
    out["density"] = dens(
        data=out["data"],
        modelName=out["modelName"],
        parameters=out["parameters"],
        logarithm=False,
    )
    return out
