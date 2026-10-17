"""Simultaneous confidence-band convenience wrapper."""


def scb(x, *args, ev=None, simul=True, type=1, **kwargs):
    fit = kwargs.pop("locfit_raw", None)
    if fit is None:
        try:
            from .locfit_raw import locfit_raw as fit
        except ImportError as exc:
            raise ImportError("scb requires the locfit.raw translation") from exc
    if ev is None:
        try:
            from .lfgrid import lfgrid
            ev = lfgrid(20)
        except ImportError:
            ev = None
    result = fit(x, *args, ev=ev, geth=70 + int(type) + 10 * int(simul), **kwargs)
    if isinstance(result, dict):
        result = dict(result)
        result["class"] = "scb"
    return result
