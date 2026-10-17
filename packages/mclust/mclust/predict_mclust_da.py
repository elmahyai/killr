"""predict.MclustDA"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

from mclust.density import dens
from mclust._mclust_mutils import softmax_rows

__all__ = ["predict_mclust_da"]


def predict_mclust_da(
    fit_object: Mapping[str, Any],
    newdata=None,
    prop: Sequence[float] | Mapping[str, float] | None = None,
    **kwargs,
):
    models = fit_object["models"]
    if isinstance(models, Mapping):
        class_names = list(models)
        model_list = [models[k] for k in class_names]
    else:
        model_list = list(models)
        class_names = [str(i + 1) for i in range(len(model_list))]
    nclass = len(model_list)
    if newdata is None:
        newdata = fit_object["data"]
    newdata = np.asarray(newdata, dtype=float)
    if newdata.ndim == 1:
        newdata = newdata.reshape(-1, 1)
    if prop is None:
        prop = kwargs.pop("prior", None)
    if prop is None:
        prop = fit_object.get("prop")
    if prop is None:
        prop_arr = np.array([m["n"] for m in model_list], dtype=float)
    elif isinstance(prop, Mapping):
        prop_arr = np.array([float(prop[k]) for k in class_names], dtype=float)
    else:
        prop_arr = np.asarray(prop, dtype=float)
    if np.any(prop_arr < 0):
        raise ValueError("'prop' must be nonnegative")
    if prop_arr.size != nclass:
        raise ValueError("'prop' is of incorrect length")
    if not np.all(np.isfinite(prop_arr)) or prop_arr.sum() <= 0:
        raise ValueError("'prop' must contain at least one positive finite value")
    prop_arr = prop_arr / prop_arr.sum()
    z = np.full((newdata.shape[0], nclass), np.nan, dtype=float)
    for j, mod in enumerate(model_list):
        z[:, j] = dens(
            newdata,
            mod["modelName"],
            mod["parameters"],
            logarithm=True,
        )
    z = softmax_rows(z, np.log(prop_arr))
    cl = np.argmax(z, axis=1)
    classification = np.array([class_names[i] for i in cl], dtype=object)
    return {"classification": classification, "z": z}
