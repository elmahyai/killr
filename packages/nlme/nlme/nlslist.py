"""List of ``nls`` fits by group (nlme ``nlsList`` generic).

Only the formula method is wired here. It calls ``nlsList_formula``, which
fits the ``SSasympOff`` model and no other. The ``selfStart`` method needs the
R session to look up the model function, so it is not translated.
"""

from __future__ import annotations

from typing import Any

from nlme.nlslistformula import nlsList_formula


def nlsList(
    model: Any,
    data: Any,
    start: Any = None,
    control: Any = None,
    level: Any = None,
    subset: Any = None,
    na_action: Any = None,
    pool: bool = True,
    warn_nls: Any = None,
):
    """Fit ``nls`` separately for each group of a grouped formula."""
    if not (isinstance(model, str) and "~" in model):
        raise NotImplementedError("nlsList.selfStart is not translated; pass a formula string")
    kwargs: dict[str, Any] = {"pool": pool}
    if start is not None:
        kwargs["start"] = start
    if control is not None:
        kwargs["control"] = control
    if level is not None:
        kwargs["level"] = level
    if subset is not None:
        kwargs["subset"] = subset
    if na_action is not None:
        kwargs["na_action"] = na_action
    if warn_nls is not None:
        kwargs["warn_nls"] = warn_nls
    return nlsList_formula(model, data, **kwargs)
