"""txtProgressBar and winProgressBar against utils 4.5.0."""

import io
from pathlib import Path

import pytest

from utils import (
    ProgressError,
    close,
    getTxtProgressBar,
    getWinProgressBar,
    setTxtProgressBar,
    setWinProgressBar,
    txtProgressBar,
    winProgressBar,
)


def _style3() -> str:
    buf = io.StringIO()
    bar = txtProgressBar(min=0, max=10, style=3, file=buf)
    setTxtProgressBar(bar, 5)
    close(bar)
    return buf.getvalue()


def test_style3_matches_the_r_bytes():
    text = _style3()
    expected = (
        Path(__file__).resolve().parents[1] / "docs" / "output" / "txtProgressBar-r.txt"
    ).read_bytes().decode("utf-8")
    assert text == expected
    assert text.endswith("|  50%\n")
    assert len(text) == 321


def test_set_returns_the_previous_value_and_ignores_an_out_of_range_update():
    buf = io.StringIO()
    bar = txtProgressBar(min=0, max=10, style=1, file=buf)
    assert setTxtProgressBar(bar, 4) == 0
    assert getTxtProgressBar(bar) == 4
    assert setTxtProgressBar(bar, 11) == 4
    assert getTxtProgressBar(bar) == 4
    close(bar)


def test_rejected_arguments_use_the_r_messages():
    with pytest.raises(ProgressError, match="must have 'max' > 'min'"):
        txtProgressBar(min=1, max=1)
    with pytest.raises(ProgressError, match="non-zero width"):
        txtProgressBar(char="")
    with pytest.raises(ProgressError, match="open connection"):
        txtProgressBar(file=1)
    with pytest.raises(ProgressError, match="length > 1"):
        txtProgressBar(style=[1, 2])
    with pytest.raises(ProgressError, match="txtProgressBar"):
        getTxtProgressBar(1)


def test_windows_bar_keeps_the_value_title_and_label():
    bar = winProgressBar("test progress bar", "Some information", 0, 100, 50, width=-1)
    assert bar.width == 200
    assert setWinProgressBar(bar, 75, "test", "75% done") == 50
    assert getWinProgressBar(bar) == 75
    assert bar.title == "test"
    assert bar.label == "75% done"
    assert setWinProgressBar(bar, 1000) == 75
    assert getWinProgressBar(bar) == 75
    close(bar)
    with pytest.raises(ProgressError, match="has it been closed"):
        setWinProgressBar(bar, 1)
