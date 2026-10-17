import re

import pytest

from prettyunits.p_value import pretty_p_value

_MINVAL_TYPE = "is.numeric(minval) & !is.factor(minval) & !is.na(minval)"
_MINVAL_RANGE = "minval < 1 & minval > 0"
_X_TYPE = "is.numeric(x) & !is.factor(x)"
_X_RANGE = "is.na(x) | (x <= 1 & x >= 0)"


def test_p_value_examples_and_recorded_case():
    assert pretty_p_value([1, 0, None, 0.01, 1e-7]) == [
        "1.0000",
        "<0.0001",
        None,
        "0.0100",
        "<0.0001",
    ]
    assert pretty_p_value([1, 0, None, 0.01, 0.0000001]) == [
        "1.0000",
        "<0.0001",
        None,
        "0.0100",
        "<0.0001",
    ]
    assert pretty_p_value([1, 0, None, 0.01, 0.0000001], minval=0.05) == [
        "1.00",
        "<0.05",
        None,
        "<0.05",
        "<0.05",
    ]
    assert pretty_p_value(None) is None
    assert pretty_p_value(float("nan")) is None


def test_p_value_stopifnot_conditions():
    with pytest.raises(ValueError, match=re.escape(_MINVAL_TYPE)):
        pretty_p_value(1, minval="A")
    with pytest.raises(ValueError, match=re.escape(_MINVAL_TYPE)):
        pretty_p_value(0.5, minval=True)
    with pytest.raises(ValueError, match=re.escape(_MINVAL_TYPE)):
        pretty_p_value(0.5, minval=None)
    with pytest.raises(ValueError, match=re.escape(_MINVAL_TYPE)):
        pretty_p_value(0.5, minval=float("nan"))
    with pytest.raises(ValueError, match=re.escape(_X_TYPE)):
        pretty_p_value("A")
    with pytest.raises(ValueError, match=re.escape(_X_TYPE)):
        pretty_p_value(True)
    with pytest.raises(ValueError, match=re.escape(_X_RANGE)):
        pretty_p_value(1.1)
    with pytest.raises(ValueError, match=re.escape(_X_RANGE)):
        pretty_p_value(-1)
    with pytest.raises(ValueError, match=re.escape(_X_RANGE)):
        pretty_p_value(float("inf"))
    with pytest.raises(ValueError, match=re.escape(_MINVAL_RANGE)):
        pretty_p_value(0.5, minval=0)
    with pytest.raises(ValueError, match=re.escape(_MINVAL_RANGE)):
        pretty_p_value(0.5, minval=1)


def test_p_value_missing_stays_missing_and_shape():
    assert pretty_p_value([None, None]) == [None, None]
    assert pretty_p_value([float("nan"), float("nan")]) == [None, None]
    assert pretty_p_value([0.5, float("nan")]) == ["0.5000", None]
    assert pretty_p_value([0, 1], minval=0.5) == ["<0.5", "1.0"]
    assert pretty_p_value([]) == []
    assert pretty_p_value([None]) == [None]
    assert pretty_p_value(0.5) == "0.5000"
    assert isinstance(pretty_p_value(0.5), str)
    assert "NA" not in pretty_p_value([1, None, 0])
