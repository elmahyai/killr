"""Non-interactive refusal, parsing, and a clipboard round trip."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from clipr import (
    clear_clip,
    clipr_available,
    dr_clipr,
    read_clip,
    read_clip_tbl,
    write_clip,
    write_last_clip,
)


def test_noninteractive_session_is_refused(monkeypatch, capsys):
    monkeypatch.delenv("CLIPR_ALLOW", raising=False)
    assert clipr_available() is False
    text = dr_clipr()
    assert "CLIPR_ALLOW" in text
    assert "CLIPR_ALLOW" in capsys.readouterr().err
    with pytest.raises(RuntimeError, match="allow_non_interactive"):
        write_clip("nope")
    with pytest.raises(RuntimeError, match="allow_non_interactive"):
        read_clip()


def test_read_clip_tbl_parses_a_character_vector():
    table = read_clip_tbl(["Name's\tAge", "Alice\t30", "Bob\t25"])
    assert list(table.columns) == ["Name.s", "Age"]
    assert table.columns["Name.s"] == ["Alice", "Bob"]
    assert table.columns["Age"] == [30, 25]
    assert table.row_names is None


def test_read_clip_tbl_uses_a_leading_tab_as_row_names():
    table = read_clip_tbl(["\tc\td", "a\t1\t3", "b\t2\t4"])
    assert table.row_names == ["a", "b"]
    assert table.columns == {"c": [1, 2], "d": [3, 4]}


def test_read_clip_tbl_rejects_the_interactive_flag():
    with pytest.raises(TypeError, match="allow_non_interactive"):
        read_clip_tbl(["a"], allow_non_interactive=True)


def _clipboard_ready() -> bool:
    if shutil.which("xclip") is None:
        return False
    seeded = subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=b"seed",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if seeded.returncode != 0:
        return False
    probe = subprocess.run(
        ["xclip", "-o", "-selection", "clipboard"],
        capture_output=True,
    )
    return probe.returncode == 0


@pytest.mark.skipif(not _clipboard_ready(), reason="xclip cannot open the clipboard")
def test_clipboard_round_trip(monkeypatch):
    monkeypatch.setenv("CLIPR_ALLOW", "TRUE")
    assert write_clip(["Write", "to", "clipboard"], return_new=True) == "Write\nto\nclipboard"
    assert read_clip() == ["Write", "to", "clipboard"]
    assert write_last_clip("last-value", return_new=True) == "last-value"
    assert read_clip() == ["last-value"]
    assert clipr_available() is True
    assert dr_clipr() == "clipr has read/write access to the system clipboard!"
    assert clear_clip() == ""
    with pytest.warns(UserWarning, match="no readable text"):
        assert read_clip() is None
