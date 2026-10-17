"""Residual variance accessor."""


def rv(fit):
    """Extract ``rv`` from a fit result or its ``dp`` mapping."""
    if isinstance(fit, dict):
        if "dp" in fit:
            return fit["dp"]["rv"]
        return fit["rv"]
    try:
        return fit.dp["rv"]
    except AttributeError:
        return fit["rv"]
