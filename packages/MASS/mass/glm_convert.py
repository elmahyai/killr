"""Convert a ``glm.nb`` fit to a ``glm`` fit with fixed theta (MASS ``glm.convert``)."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

import numpy as np

from mass.glm_nb import GlmControl, NegbinFit


@dataclass
class GlmConvertedFit:
    """Fitted model after ``glm.convert`` (R classes ``glm``, ``lm``)."""

    coefficients: np.ndarray
    fitted_values: np.ndarray
    theta: float
    se_theta: float
    twologlik: float
    deviance: float
    df_residual: int
    rank: int
    formula: str
    link: str
    klass: tuple[str, ...] = ("glm", "lm")
    terms: Any = None
    call: dict[str, Any] = field(default_factory=dict)
    prior_weights: np.ndarray | None = None
    offset: np.ndarray | None = None
    y: np.ndarray | None = None
    model: Any = None
    th_warn: str | None = None
    aic: float | None = None
    control: GlmControl | None = None
    method: str = "glm.fit"


def _negbin_link(object: NegbinFit) -> str | None:
    link = getattr(object, "link", None)
    if link is not None:
        if isinstance(link, str):
            return link
        name = getattr(link, "__name__", None)
        if name:
            return str(name)
        return str(link)
    return None


def _converted_call(object: NegbinFit, link: str) -> dict[str, Any]:
    call = dict(object.call)
    call.pop("init_theta", None)
    call.pop("init.theta", None)
    call.pop("link", None)
    call["fn"] = "stats::glm"
    call["family"] = {
        "fn": "negative.binomial",
        "theta": float(object.theta),
        "link": link,
    }
    return call


def glm_convert(object: NegbinFit) -> GlmConvertedFit:
    """Change a negative-binomial ``glm.nb`` fit into a ``glm`` fit with fixed ``theta``."""
    link = _negbin_link(object)
    if link is None:
        link = "log"
    call = _converted_call(object, link)
    kwargs: dict[str, Any] = {}
    for item in fields(NegbinFit):
        if item.name == "call":
            continue
        kwargs[item.name] = getattr(object, item.name)
    return GlmConvertedFit(**kwargs, link=link, call=call)


def proof_vector(object: GlmConvertedFit) -> np.ndarray:
    """Numeric summary aligned with ``proof/glm.convert-r.R``."""
    fam = object.call["family"]
    class_map = {"negbin": 1.0, "glm": 2.0, "lm": 3.0}
    classes = list(object.klass)
    flags = np.array(
        [
            fam["theta"],
            class_map.get(classes[0], 0.0),
            class_map.get(classes[1], 0.0) if len(classes) > 1 else 0.0,
            1.0 if object.call.get("init_theta") is None and "init.theta" not in object.call else 0.0,
            1.0 if object.call.get("link") is None else 0.0,
            1.0 if object.call.get("fn") == "stats::glm" else 0.0,
            1.0 if fam.get("fn") == "negative.binomial" else 0.0,
            1.0 if fam.get("link") == "log" else 0.0,
        ],
        dtype=float,
    )
    return np.concatenate(
        [
            np.asarray(object.coefficients, dtype=float).reshape(-1),
            np.array(
                [
                    object.theta,
                    object.deviance,
                    float(object.df_residual),
                    float(object.rank),
                ],
                dtype=float,
            ),
            flags,
        ]
    )
