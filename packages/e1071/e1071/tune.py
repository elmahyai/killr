"""Tuning settings. The search itself stays with the model it calls."""

from __future__ import annotations


def tune_control(
    random=False,
    nrepeat=1,
    sampling="cross",
    cross=10,
    fix=2 / 3,
    nboot=10,
    boot_size=9 / 10,
    best_model=True,
    performances=True,
):
    choices = ("cross", "fix", "bootstrap")
    matches = [name for name in choices if name.startswith(sampling)]
    if len(matches) != 1:
        raise ValueError("invalid sampling")
    return {
        "random": bool(random),
        "nrepeat": nrepeat,
        "sampling": matches[0],
        "cross": cross,
        "fix": fix,
        "nboot": nboot,
        "boot_size": boot_size,
        "best_model": bool(best_model),
        "performances": bool(performances),
    }
