"""Previous and current integrator step sizes (deSolve global ``timesteps``)."""

from __future__ import annotations

_GLOB_TIMESTEPS: list[float] = [0.0, 0.0]


def _reset_timesteps() -> None:
    """Zero the pair, as ``call_rk4`` and ``terminate`` do in C."""
    _GLOB_TIMESTEPS[0] = 0.0
    _GLOB_TIMESTEPS[1] = 0.0


def _advance_timestep(dt: float) -> None:
    """Shift and store the step about to be tried, matching ``call_rk4``."""
    _GLOB_TIMESTEPS[0] = _GLOB_TIMESTEPS[1]
    _GLOB_TIMESTEPS[1] = float(dt)


def timestep(prev: bool = True) -> float:
    """Return the previous or current integrator step size.

    ``prev=True`` matches R ``timestep(prev = TRUE)`` (``out[1]``); ``prev=False``
    is the step currently tried (``out[2]``). Outside an integration both are 0.
    """
    index = 0 if prev else 1
    return _GLOB_TIMESTEPS[index]
