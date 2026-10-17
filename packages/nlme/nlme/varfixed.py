"""Fixed variance-weights constructor (nlme ``varFixed``)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import getCovariateFormula
from nlme.varcomb import VarFunc
from nlme.varconstpower import _as_one_sided_formula, _get_groups_formula


@dataclass(slots=True)
class VarFixed(VarFunc):
    """Storage for a varFixed object: no parameters, only the covariate formula."""

    formula: str
    values: np.ndarray

    @property
    def classes(self) -> tuple[str, ...]:
        return ("varFixed", "varFunc")


def varFixed(value: str = "~ 1") -> VarFixed:
    """Construct a varFixed object whose weights are the covariate ``form``."""
    text = str(value).strip()
    if "~" not in text:
        raise TypeError("'value' must be a one sided formula")
    form = _as_one_sided_formula(text)
    if len(_all_vars(getCovariateFormula(form).text)) == 0:
        raise ValueError("'form' must have a covariate")
    if _get_groups_formula(form) is not None:
        form = getCovariateFormula(form).text
        warnings.warn('ignoring \'group\' in "varFixed" formula', stacklevel=2)
    return VarFixed(form, np.array([], dtype=np.float64))


def proof_values(object: VarFixed) -> np.ndarray:
    """Numeric summary of a varFixed object for R comparison."""
    return np.array(
        [float(object.values.size), float(sum(map(ord, object.formula)))],
        dtype=np.float64,
    )
