"""Regression-band convenience wrapper."""


def regband(formula, what=("CP", "GCV", "GKK", "RSW"), deg=1, **kwargs):
    fit = kwargs.pop("locfit", None)
    if fit is None:
        try:
            from .locfit import locfit
        except ImportError as exc:
            raise ImportError("regband requires the locfit translation") from exc
        fit = locfit
    values = fit(formula, geth=3, deg=(deg, 4), deriv=tuple(what), **kwargs)
    return {name: values[name] for name in what} if isinstance(values, dict) else values
