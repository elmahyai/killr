"""``nlme`` generic (nlme ``nlme``): dispatch on the class of ``model``.

R's ``nlme`` is an S3 generic. ``nlsList`` objects go to ``nlme.nlsList`` and
formulas go to ``nlme.formula``. Other classes have no method here, so they
raise the same "no applicable method" error as an unknown class.
"""

from __future__ import annotations

from typing import Any

from nlme.lme_family import nlme_formula
from nlme.nlme_random import nlme_random_formula, random_is_intercept_only
from nlme.nlme_nlslist import nlme_nlsList
from nlme.nlslistformula import NlsList

__all__ = ["nlme"]


def nlme(
    model: Any,
    data: Any = None,
    fixed: Any = None,
    random: Any = None,
    groups: Any = None,
    start: Any = None,
    correlation: Any = None,
    weights: Any = None,
    subset: Any = None,
    method: Any = "ML",
    na_action: Any = None,
    naPattern: Any = None,
    control: Any = None,
    verbose: bool = False,
):
    """Fit a nonlinear mixed-effects model; the method follows the class of ``model``."""
    if isinstance(model, NlsList):
        return nlme_nlsList(
            model,
            data=data,
            fixed=fixed,
            random=random,
            groups=groups,
            start=start,
            correlation=correlation,
            weights=weights,
            subset=subset,
            method=method,
            na_action=na_action,
            naPattern=naPattern,
            control=control,
            verbose=verbose,
        )
    if isinstance(model, str) and "~" in model:
        if fixed is None:
            raise ValueError('argument "fixed" is missing, with no default')
        if start is None:
            raise NotImplementedError("the self-starting nlme path (nlsList with selfStart) is not translated")
        effective = fixed if random is None else random
        if correlation is None and weights is None and subset is None and not random_is_intercept_only(effective):
            return nlme_random_formula(
                model,
                data,
                fixed,
                random=random,
                groups=groups,
                start=start,
                method=method,
                control=control,
            )
        return nlme_formula(
            model,
            data,
            fixed,
            random=random,
            groups=groups,
            start=start,
            correlation=correlation,
            weights=weights,
            subset=subset,
            method=method,
            na_action=na_action,
            naPattern=naPattern,
            control=control,
            verbose=verbose,
        )
    raise TypeError(f"no applicable method for 'nlme' applied to an object of class \"{type(model).__name__}\"")
