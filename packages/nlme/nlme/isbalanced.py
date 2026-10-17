"""Balance check for grouped data (nlme ``isBalanced``)."""

from __future__ import annotations

from typing import Any

import numpy as np

from nlme.getcovariateformula import getCovariateFormula


def _group_name(formula: str) -> str:
    rhs = formula.split("~", 1)[1]
    if "|" not in rhs:
        raise ValueError("'object' has no groups formula")
    return rhs.split("|", 1)[1].strip().split("/", 1)[0].strip()


def _covariate_values(object: Any, formula: str) -> np.ndarray:
    cov_text = getCovariateFormula(formula).text.lstrip("~").strip()
    columns = object.columns
    n_rows = len(next(iter(columns.values())))
    if not cov_text or cov_text == "1":
        return np.ones(n_rows, dtype=np.float64)
    return np.asarray(columns[cov_text], dtype=np.float64)


def isBalanced(object: Any, countOnly: bool = False, level: Any = None) -> bool:
    """Return whether grouped data has the same count in every group, or in every cell.

    ``object`` is a groupedData stand-in with ``columns``, ``formula`` and
    ``group_levels``.  With ``countOnly`` only the group sizes are compared.
    Otherwise the covariate-by-group table, including zero cells, is compared.
    """
    classes = getattr(object, "classes", ())
    if "groupedData" not in classes:
        raise TypeError("isBalanced requires a groupedData object")
    if level is not None and level != 1:
        raise NotImplementedError("only one grouping level is implemented for isBalanced")
    formula = str(object.formula).strip()
    group_var = _group_name(formula)
    groups = np.asarray(object.columns[group_var], dtype=np.dtype("O"))
    levels = tuple(str(level_name) for level_name in object.group_levels)
    if countOnly:
        counts = [int(np.sum(groups == str(level_name))) for level_name in levels]
        return len(set(counts)) == 1
    covariate = _covariate_values(object, formula)
    cov_levels = sorted(set(covariate.tolist()))
    counts = [
        int(np.sum((covariate == cov) & (groups == str(level_name))))
        for cov in cov_levels
        for level_name in levels
    ]
    return len(set(counts)) == 1
