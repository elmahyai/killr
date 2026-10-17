"""OLS regressions of an unrestricted VECM (``cajools``)."""

import numpy as np

from urca.johansen import CaJo, CaJoTest, Lm


def cajools(z, reg_number=None):
    """OLS of the unrestricted VECM; returns ``Lm`` fits like R ``lm`` without intercept."""
    if not isinstance(z, (CaJo, CaJoTest)):
        raise TypeError(
            "\nPlease, provide object of class 'ca.jo' or 'cajo.test' as 'z'.\n"
        )
    p = int(z.P)
    z0 = np.asarray(z.Z0, dtype=float)
    z1 = np.asarray(z.Z1, dtype=float)
    zk = np.asarray(z.ZK, dtype=float)
    n_eq = z0.shape[1]
    z1_names = list(
        getattr(z, "z1_names", [f"X{i + 1}" for i in range(z1.shape[1])])
    )
    zk_names = list(
        getattr(z, "zk_names", [f"X{i + 1}" for i in range(zk.shape[1])])
    )
    coef_names = z1_names + zk_names
    design = np.column_stack([z1, zk])
    if reg_number is not None:
        reg_number = int(reg_number)
        if reg_number < 1 or reg_number > n_eq:
            raise ValueError(
                "\nPlease, provide a valid number of the regression within \n"
                " the VECM, numbering from 1st to last row.\n"
            )
        y = z0[:, reg_number - 1]
        coef, _resid, _rank, _sv = np.linalg.lstsq(design, y, rcond=None)
        fitted = design @ coef
        residuals = y - fitted
        return Lm(coef=coef, residuals=residuals, fitted=fitted, coef_names=coef_names)
    coef, _resid, _rank, _sv = np.linalg.lstsq(design, z0, rcond=None)
    fitted = design @ coef
    residuals = z0 - fitted
    return Lm(coef=coef, residuals=residuals, fitted=fitted, coef_names=coef_names)
