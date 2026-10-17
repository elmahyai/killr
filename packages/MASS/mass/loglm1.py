"""MASS ``loglm1`` — log-linear fit on a contingency table or model frame."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any, Iterator

import numpy as np

from mass.errors import MassError
from mass.loglm import (
    LoglmResult,
    Terms,
    _FreqArray,
    _loglm1_data_frame,
    _loglm1_default,
)


class ModelFrame(MutableMapping[str, Sequence[Any]]):
    """Model frame with an R-style ``terms`` attribute (``loglm1.data.frame``)."""

    terms: Terms

    def __init__(self, data: Mapping[str, Sequence[Any]], terms: Terms) -> None:
        self._data = {k: list(v) for k, v in data.items()}
        self.terms = terms

    def __getitem__(self, key: str) -> Sequence[Any]:
        return self._data[key]

    def __setitem__(self, key: str, value: Sequence[Any]) -> None:
        self._data[key] = list(value)

    def __delitem__(self, key: str) -> None:
        del self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def keys(self) -> Any:
        return self._data.keys()


def _as_freq_array(data: np.ndarray) -> _FreqArray:
    """``loglm1.xtabs`` / ``loglm1.default`` — array with optional dimnames and terms."""
    if isinstance(data, _FreqArray):
        freq = data
    else:
        freq = np.asarray(data, dtype=float).view(_FreqArray)
        freq._dimnames = getattr(data, "_dimnames", None)
        freq.terms = getattr(data, "terms", None)
    return freq


def loglm1(formula: str, data: Any, **kwargs: Any) -> LoglmResult:
    """Fit a log-linear model (MASS ``loglm1``; dispatches on ``data``)."""
    if isinstance(data, Mapping) and not isinstance(data, np.ndarray):
        terms = getattr(data, "terms", None)
        if terms is None:
            raise MassError("'data' has no 'terms' attribute")
        return _loglm1_data_frame(formula, data, terms, **kwargs)
    if isinstance(data, np.ndarray):
        return _loglm1_default(formula, _as_freq_array(data), **kwargs)
    raise MassError("unsupported 'data' type for loglm1")
