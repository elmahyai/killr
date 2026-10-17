"""Pager constructors against diffobj 0.3.9."""

import os
import subprocess
import warnings

import pytest

from diffobj.pager import (
    NA_character_,
    NA_logical,
    Pager,
    PagerBrowser,
    PagerOff,
    PagerSystem,
    PagerSystemLess,
    recorded_urls,
    view_or_browse,
)

R_SLOTS = r"""
suppressPackageStartupMessages(library(diffobj))
line <- function(name, obj) {
  mb <- if (is.na(obj@make.blocking)) "NA" else if (isTRUE(obj@make.blocking)) "TRUE" else "FALSE"
  ansi <- if (isTRUE(obj@ansi)) "TRUE" else "FALSE"
  flags <- if ("flags" %in% slotNames(obj)) obj@flags else ""
  cat(name, obj@threshold, obj@file.ext, ansi, mb, flags, sep = "|", "\n")
}
line("PagerOff", PagerOff())
line("PagerSystem", PagerSystem())
line("PagerSystemLess", PagerSystemLess())
line("PagerBrowser", PagerBrowser())
line("Pager", Pager())
line("PagerAnsi", Pager(ansi = TRUE))
line("SystemExt", PagerSystem(file.ext = "txt"))
line("LessExt", PagerSystemLess(file.ext = "txt"))
"""


def _r(script: str) -> str:
    env = os.environ.copy()
    env["R_LIBS_USER"] = os.path.expanduser("~/R/library")
    return subprocess.check_output(["Rscript", "-e", script], text=True, env=env)


def _py_line(name, obj) -> str:
    if obj.make_blocking == NA_logical or obj.make_blocking is NA_logical:
        mb = "NA"
    elif obj.make_blocking is True:
        mb = "TRUE"
    else:
        mb = "FALSE"
    ansi = "TRUE" if obj.ansi is True else "FALSE"
    flags = getattr(obj, "flags", "")
    return "|".join([name, str(obj.threshold), obj.file_ext, ansi, mb, flags]).rstrip("|")


def test_slots_match_r():
    text = _r(R_SLOTS)
    expected = {}
    for line in text.splitlines():
        if "|" not in line:
            continue
        name = line.split("|", 1)[0]
        expected[name] = line.rstrip("|")
    objects = {
        "PagerOff": PagerOff(),
        "PagerSystem": PagerSystem(),
        "PagerSystemLess": PagerSystemLess(),
        "PagerBrowser": PagerBrowser(),
        "Pager": Pager(),
        "PagerAnsi": Pager(ansi=True),
        "SystemExt": PagerSystem(**{"file.ext": "txt"}),
        "LessExt": PagerSystemLess(**{"file.ext": "txt"}),
    }
    for name, obj in objects.items():
        assert _py_line(name, obj) == expected[name]


def test_class_names_and_inheritance():
    off = PagerOff()
    system = PagerSystem()
    less = PagerSystemLess()
    browser = PagerBrowser()
    plain = Pager()
    assert off.class_name == "PagerOff"
    assert system.class_name == "PagerSystem"
    assert less.class_name == "PagerSystemLess"
    assert browser.class_name == "PagerBrowser"
    assert plain.class_name == "Pager"
    assert isinstance(off, Pager)
    assert isinstance(less, PagerSystem)
    assert isinstance(less, Pager)
    assert isinstance(browser, Pager)
    assert less.slots["flags"] == "R"
    assert less.ansi is True
    assert browser.make_blocking == NA_logical
    assert browser.file_ext == "html"
    assert plain.slots["file.path"] is NA_character_


def test_validity_and_initialize_errors():
    with pytest.raises(ValueError) as exc:
        Pager(threshold=1.5)
    assert str(exc.value) == "invalid class “Pager” object: Invalid `threshold` slot"
    with pytest.raises(ValueError) as exc:
        Pager(threshold=True)
    assert str(exc.value) == "invalid class “Pager” object: Invalid `threshold` slot"
    with pytest.raises(ValueError) as exc:
        Pager(**{"file.ext": NA_character_})
    assert str(exc.value) == "invalid class “Pager” object: Invalid `file.ext` slot"
    with pytest.raises(ValueError) as exc:
        Pager(**{"file.path": ["a", "b"]})
    assert str(exc.value) == "Argument `file.path` must be length 1."
    with pytest.raises(ValueError) as exc:
        Pager(**{"file.path": 1})
    assert str(exc.value) == "Argument `file.path` must be character."
    path = Pager(**{"file.path": float("nan")})
    assert path.file_path == NA_character_
    with pytest.raises(ValueError) as exc:
        PagerSystemLess(flags=1)
    assert str(exc.value) == "Argument `flags` must be character(1L) and not NA"
    with pytest.raises(ValueError) as exc:
        PagerSystemLess(ansi=NA_logical)
    assert str(exc.value) == "invalid class “PagerSystemLess” object: Invalid `ansi` slot"
    kept = Pager(ansi="x")
    assert kept.ansi is False
    swallowed = PagerSystem(**{"file.ext": 1})
    assert swallowed.file_ext == ""


def test_default_pager_writes_lines(tmp_path, capsys):
    target = tmp_path / "lines.txt"
    target.write_text("a\nb\n", encoding="utf-8")
    Pager().pager(target)
    assert capsys.readouterr().out == "a\nb\n"


def test_less_flags_are_set_only_during_the_call(monkeypatch):
    monkeypatch.delenv("LESS", raising=False)
    seen = {}

    def capture(path):
        seen["during"] = os.environ.get("LESS")

    pager = PagerSystemLess(pager=capture, flags="RX")
    pager.pager("ignored")
    assert seen["during"] == "-RX"
    assert "LESS" not in os.environ
    assert pager.flags == "RX"


def test_view_or_browse_invalid_url_and_no_display(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("DIFFOBJ_VIEWER", raising=False)
    recorded_urls.clear()
    with pytest.raises(ValueError) as exc:
        view_or_browse("")
    assert str(exc.value) == "'url' must be a non-empty character string"
    with pytest.raises(ValueError) as exc:
        view_or_browse(1)
    assert str(exc.value) == "'url' must be a non-empty character string"
    result = view_or_browse("http://example.com")
    assert result is None
    assert recorded_urls[-1] == "http://example.com"


def test_viewer_success_skips_browser_and_failure_warns(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    recorded_urls.clear()

    def ok(url):
        return 42

    assert view_or_browse("http://example.com", viewer=ok) == 42

    def boom(url):
        raise RuntimeError("boom")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError) as exc:
            view_or_browse("", viewer=boom)
    assert str(exc.value) == "'url' must be a non-empty character string"
    assert caught
    assert str(caught[0].message) == "IDE viewer failed with error boom; falling back to `browseURL`"
