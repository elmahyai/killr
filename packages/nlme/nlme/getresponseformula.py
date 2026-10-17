"""Extract the response side of a model formula (nlme getResponseFormula)."""

from __future__ import annotations

from dataclasses import dataclass

from nlme.getcovariateformula import (
    CovariateFormula,
    _deparse,
    _formula_text as _covariate_formula_text,
    _parse_bar,
    _tokenize,
)


@dataclass(frozen=True, slots=True)
class ResponseFormula:
    """One-sided formula for the response variable."""

    text: str

    def __str__(self) -> str:
        return self.text


def getResponseFormula(object) -> ResponseFormula:
    """Return the response expression from ``formula(object)`` as a one-sided formula."""
    text = _formula_text(object)
    if text is None:
        raise ValueError("'form' must be a two-sided formula")
    lhs, rhs = text.split("~", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    if not lhs or not rhs:
        raise ValueError("'form' must be a two-sided formula")
    tokens = _tokenize(lhs)
    tree, pos = _parse_bar(tokens, 0)
    if pos != len(tokens):
        raise ValueError("'form' must be a two-sided formula")
    return ResponseFormula(f"~{_deparse(tree)}")


def _formula_text(object) -> str | None:
    if isinstance(object, ResponseFormula):
        return object.text
    if isinstance(object, CovariateFormula):
        return object.text
    return _covariate_formula_text(object)
