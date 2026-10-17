"""Scalar accuracy measures between two vectors."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric


def rmserr(x, y, summary=False):
    if not is_r_numeric(x) or not is_r_numeric(y):
        raise PracmaError("Arguments 'x' and 'y' must be numeric vectors.")
    left = np.asarray(x, dtype=float).reshape(-1)
    right = np.asarray(y, dtype=float).reshape(-1)
    if left.size != right.size:
        raise PracmaError("Vectors 'x' and ' y' must have the same length.")
    count = left.size
    error = right - left
    mae = float(np.sum(np.abs(error)) / count)
    mse = float(np.sum(error ** 2) / count)
    rmse = float(np.sqrt(np.sum(error ** 2) / count))
    mape = float(np.sum(np.abs(error / left)) / count)
    nmse = float(np.sum(error ** 2) / np.sum((left - np.mean(left)) ** 2))
    rstd = float(np.sqrt(np.sum(error ** 2) / count) / np.mean(left))
    if summary:
        print("-- Error Terms --------------------------------------------------")
        print(f" MAE:   {mae: .4f}")
        print(f" MSE:   {mse: .4f}")
        print(f" RMSE:  {rmse: .4f}")
        print(f" MAPE:  {mape: .4f}")
        print(f" LMSE:  {nmse: .4f}")
        print(f" rSTD:  {rstd: .4f}")
        print("-----------------------------------------------------------------")
    return {"mae": mae, "mse": mse, "rmse": rmse, "mape": mape, "nmse": nmse, "rstd": rstd}
