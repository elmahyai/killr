"""Extreme limiting dilution analysis.

Translated from statmod 1.5.2 ``limdil``.  In that release ``limdil`` and
``elda`` have the same implementation; this public entry point preserves the
original name while sharing the tested Python implementation.
"""

from __future__ import annotations

from statmod.elda import elda


def limdil(
    response,
    dose,
    tested=None,
    group=None,
    observed=False,
    confidence=0.95,
    test_unit_slope=False,
):
    """Estimate active-cell frequency from limiting-dilution assays."""
    return elda(
        response=response,
        dose=dose,
        tested=tested,
        group=group,
        observed=observed,
        confidence=confidence,
        test_unit_slope=test_unit_slope,
    )
