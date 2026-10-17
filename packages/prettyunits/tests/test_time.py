import pytest

from prettyunits._difftime import Difftime
from prettyunits.time import pretty_dt, pretty_ms, pretty_sec

_VECTOR = [
    0,
    0.1,
    1,
    1400,
    2400,
    1000 * 55,
    1000 * 67,
    1000 * 60 * 5,
    1000 * 60 * 67,
    1000 * 60 * 60 * 12,
    1000 * 60 * 60 * 40,
    1000 * 60 * 60 * 999,
]
_LABELS = [
    "0ms",
    "1ms",
    "1ms",
    "1.4s",
    "2.4s",
    "55s",
    "1m 7s",
    "5m",
    "1h 7m",
    "12h",
    "1d 16h",
    "41d 15h",
]


def test_pretty_ms_works():
    assert pretty_ms(0) == "0ms"
    assert pretty_ms(0.1) == "1ms"
    assert pretty_ms(1) == "1ms"
    assert pretty_ms(1000 + 400) == "1.4s"
    assert pretty_ms(1000 * 2 + 400) == "2.4s"
    assert pretty_ms(1000 * 55) == "55s"
    assert pretty_ms(1000 * 67) == "1m 7s"
    assert pretty_ms(1000 * 60 * 5) == "5m"
    assert pretty_ms(1000 * 60 * 67) == "1h 7m"
    assert pretty_ms(1000 * 60 * 60 * 12) == "12h"
    assert pretty_ms(1000 * 60 * 60 * 40) == "1d 16h"
    assert pretty_ms(1000 * 60 * 60 * 999) == "41d 15h"


def test_compact_pretty_ms_works():
    assert pretty_ms(1000 + 4, compact=True) == "~1s"
    assert pretty_ms(1000 * 60 * 60 * 999, compact=True) == "~41d"


def test_pretty_ms_handles_vectors():
    assert pretty_ms(_VECTOR) == _LABELS
    assert pretty_ms([]) == []
    assert pretty_ms([0]) == ["0ms"]


def test_pretty_sec_works():
    assert pretty_sec(0 / 1000) == "0ms"
    assert pretty_sec(0.1 / 1000) == "1ms"
    assert pretty_sec(1 / 1000) == "1ms"
    assert pretty_sec((1000 + 400) / 1000) == "1.4s"
    assert pretty_sec((1000 * 2 + 400) / 1000) == "2.4s"
    assert pretty_sec(1000 * 55 / 1000) == "55s"
    assert pretty_sec(1000 * 67 / 1000) == "1m 7s"
    assert pretty_sec(1000 * 60 * 5 / 1000) == "5m"
    assert pretty_sec(1000 * 60 * 67 / 1000) == "1h 7m"
    assert pretty_sec(1000 * 60 * 60 * 12 / 1000) == "12h"
    assert pretty_sec(1000 * 60 * 60 * 40 / 1000) == "1d 16h"
    assert pretty_sec(1000 * 60 * 60 * 999 / 1000) == "41d 15h"


def test_compact_pretty_sec_works():
    assert pretty_sec((1000 + 4) / 1000, compact=True) == "~1s"
    assert pretty_sec(1000 * 60 * 60 * 999 / 1000, compact=True) == "~41d"


def test_pretty_sec_handles_vectors():
    seconds = [value / 1000 for value in _VECTOR]
    assert pretty_sec(seconds) == _LABELS
    assert pretty_sec([]) == []


def test_pretty_dt_works():
    assert pretty_dt(Difftime(0 / 1000, units="secs")) == "0ms"
    assert pretty_dt(Difftime(0.1 / 1000, units="secs")) == "1ms"
    assert pretty_dt(Difftime(1 / 1000, units="secs")) == "1ms"
    assert pretty_dt(Difftime((1000 + 400) / 1000, units="secs")) == "1.4s"
    assert pretty_dt(Difftime((1000 * 2 + 400) / 1000, units="secs")) == "2.4s"
    assert pretty_dt(Difftime(1000 * 55 / 1000, units="secs")) == "55s"
    assert pretty_dt(Difftime(1000 * 67 / 1000, units="secs")) == "1m 7s"
    assert pretty_dt(Difftime(1000 * 60 * 5 / 1000, units="secs")) == "5m"
    assert pretty_dt(Difftime(1000 * 60 * 67 / 1000, units="secs")) == "1h 7m"
    assert pretty_dt(Difftime(1000 * 60 * 60 * 12 / 1000, units="secs")) == "12h"
    assert pretty_dt(Difftime(1000 * 60 * 60 * 40 / 1000, units="secs")) == "1d 16h"
    assert pretty_dt(Difftime(1000 * 60 * 60 * 999 / 1000, units="secs")) == "41d 15h"


def test_compact_pretty_dt_works():
    assert pretty_dt(Difftime((1000 + 4) / 1000, units="secs"), compact=True) == "~1s"
    assert (
        pretty_dt(Difftime(1000 * 60 * 60 * 999 / 1000, units="secs"), compact=True)
        == "~41d"
    )


def test_pretty_dt_handles_vectors():
    seconds = [value / 1000 for value in _VECTOR]
    assert pretty_dt(Difftime(seconds, units="secs")) == _LABELS
    assert pretty_dt(Difftime([], units="secs")) == []


def test_pretty_dt_works_with_nas():
    interval = Difftime([None, 1], units="secs")
    assert pretty_dt(interval, compact=True) == [None, "~1s"]
    assert pretty_dt(interval, compact=False) == [None, "1s"]


def test_missing_values_are_none_not_the_string_na():
    assert pretty_ms(None) is None
    assert pretty_ms(float("nan")) is None
    assert pretty_ms(None, compact=True) is None
    assert pretty_ms(float("nan"), compact=True) is None
    assert pretty_sec(None) is None
    assert pretty_sec(float("nan")) is None
    assert pretty_ms([0, None, 1400, float("nan")]) == ["0ms", None, "1.4s", None]


def test_zero_compact_and_non_numeric_inputs():
    assert pretty_ms(0, compact=True) is None
    assert pretty_ms(0.1, compact=True) is None
    assert pretty_ms([0, 1400], compact=True) == [None, "~1.4s"]
    with pytest.raises(ValueError):
        pretty_ms(True)
    with pytest.raises(ValueError):
        pretty_ms([1, False])
    with pytest.raises(ValueError):
        pretty_sec(True)
    with pytest.raises(ValueError):
        pretty_dt(1.4)
    with pytest.raises(ValueError):
        pretty_dt(None)


def test_infinite_input_and_tie_rounding():
    with pytest.raises(ValueError):
        pretty_ms(float("inf"))
    with pytest.raises(ValueError):
        pretty_ms(float("-inf"))
    with pytest.raises(ValueError):
        pretty_ms([1000, float("inf")])
    assert pretty_ms(float("inf"), compact=True) == "~Infd"
    assert pretty_ms(float("-inf"), compact=True) is None
    assert pretty_ms(1250) == "1.2s"
    assert pretty_ms(1350) == "1.4s"
    assert pretty_ms(59960) == "60s"
    assert pretty_ms(-1.2) == "-1ms"
    assert pretty_ms(-0.1) == "0ms"
    assert pretty_ms(-5000, compact=True) == "~23h"
    assert pretty_ms(-90000000) == "-9e+07ms"
