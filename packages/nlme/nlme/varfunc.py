"""Variance-function constructor (nlme varFunc)."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from nlme.asoneformula import _all_vars
from nlme.getcovariateformula import getCovariateFormula
from nlme.varcomb import VarFunc, _is_var_func
from nlme.varconstpower import _as_one_sided_formula, _get_groups_formula


@dataclass(slots=True)
class _FixedFormulaVarFunc(VarFunc):
    """What ``varFixed(asOneSidedFormula(form))`` returns for a formula.

    Holds the covariate formula and the class vector ``varFixed``/``varFunc``.
    It carries no parameters. The ``varFixed`` function itself is not translated
    yet, so this is the local stand-in that ``varFunc`` needs.
    """

    formula: str
    values: np.ndarray = field(default_factory=lambda: np.array([], dtype=np.float64))
    weights: np.ndarray | None = None

    @property
    def classes(self) -> tuple[str, ...]:
        return ("varFixed", "varFunc")

    def __len__(self) -> int:
        return 0


def varFunc(object: Any = None) -> Any:
    """Return a ``varFunc`` object.

    ``None`` stays ``None`` and an existing ``varFunc`` object is returned as is.
    A formula or character string builds a fixed-weights structure from its
    covariate. Anything else raises an error, as the R function does.
    """
    if object is None:
        return None
    if _is_var_func(object):
        return object
    if isinstance(object, str):
        return _fixed_from_formula(object)
    raise ValueError(
        'can only construct "varFunc" object from another "varFunc" object, '
        "a formula, or a character string"
    )


def _fixed_from_formula(form: str) -> _FixedFormulaVarFunc:
    """Checks and attributes of ``varFixed(asOneSidedFormula(form))``."""
    one_sided = _as_one_sided_formula(form)
    if len(_all_vars(getCovariateFormula(one_sided).text)) == 0:
        raise ValueError("'form' must have a covariate")
    if _get_groups_formula(one_sided) is not None:
        one_sided = getCovariateFormula(one_sided).text
        warnings.warn('ignoring \'group\' in "varFixed" formula', stacklevel=3)
    return _FixedFormulaVarFunc(one_sided)
