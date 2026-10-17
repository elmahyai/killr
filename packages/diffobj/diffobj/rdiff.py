"""Wrappers around the system diff, as ``Rdiff_chr`` and ``Rdiff_obj`` are.

``tools::Rdiff`` is still unfinished as an export. These wrappers call the
``useDiff = TRUE`` path that already lives in ``tools.rdiff``: clean the lines,
then run ``diff -bw``. ``minimal`` drops the lines that start with ``<``,
``>``, or ``-``.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from diffobj.capt import r_print

try:
    from tools.rdiff import rdiff as _tools_rdiff
except ImportError:
    import sys

    _tools_root = Path(__file__).resolve().parents[2] / "tools"
    sys.path.insert(0, str(_tools_root))
    from tools.rdiff import rdiff as _tools_rdiff


def _true_false(value, name: str) -> None:
    if value is True or value is False:
        return
    shown = "TRUE" if name == "silent" else "FALSE"
    del shown
    raise ValueError(f"isTRUE({name}) || identical({name}, FALSE) is not TRUE")


def _as_character(value, role: str) -> list[str]:
    """``as.character`` for the vectors ``Rdiff_chr`` writes to temp files."""

    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        lines = []
        for item in value:
            if item is None:
                lines.append("NA")
            elif isinstance(item, str):
                lines.append(item)
            elif isinstance(item, bool):
                lines.append("TRUE" if item else "FALSE")
            elif isinstance(item, int):
                lines.append(str(item))
            elif isinstance(item, float):
                if item != item:
                    lines.append("NaN")
                elif item == float("inf"):
                    lines.append("Inf")
                elif item == float("-inf"):
                    lines.append("-Inf")
                else:
                    lines.append(str(item) if item != int(item) else str(int(item)))
            else:
                raise ValueError(f"Unable to coerce `{role}` to character.")
        return lines
    if value is None:
        return ["NA"]
    raise ValueError(f"Unable to coerce `{role}` to character.")


def _write_lines(lines: list[str], path: Path) -> None:
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


def _diff_lines(left: Path, right: Path, null_pointers: bool) -> list[str]:
    if shutil.which("diff") is None:
        raise RuntimeError(
            "`tools::Rdiff` returned a warning; this likely means you are running "
            "without a `diff` utility accessible to R"
        )
    result = _tools_rdiff(
        str(left),
        str(right),
        use_diff=True,
        log=True,
        null_pointers=null_pointers,
    )
    out = result["out"]
    if isinstance(out, str):
        return [] if out == "" else out.splitlines()
    return list(out)


def _finish(lines: list[str], silent: bool, minimal: bool) -> list[str]:
    if minimal:
        lines = [line for line in lines if not line[:1] in "<>-"]
    if not silent:
        print("\n".join(lines))
    return lines


def Rdiff_chr(source, target, silent=False, minimal=False, nullPointers=True, **kwargs):
    """Diff two character vectors with ``diff -bw``."""

    if "null.pointers" in kwargs or "null_pointers" in kwargs:
        nullPointers = kwargs.pop("null.pointers", kwargs.pop("null_pointers", nullPointers))
    if kwargs:
        unknown = ", ".join(kwargs)
        raise TypeError(f"unused arguments ({unknown})")
    _true_false(silent, "silent")
    _true_false(minimal, "minimal")
    left = _as_character(source, "target")
    right = _as_character(target, "current")
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        left_path = folder / "from"
        right_path = folder / "to"
        _write_lines(left, left_path)
        _write_lines(right, right_path)
        lines = _diff_lines(left_path, right_path, nullPointers)
    return _finish(lines, silent, minimal)


def _maybe_file(value):
    if isinstance(value, str) and value != "" and os.path.isfile(value):
        return value
    if isinstance(value, (list, tuple)) and len(value) == 1 and isinstance(value[0], str):
        if os.path.isfile(value[0]):
            return value[0]
    return None


def Rdiff_obj(source, target, silent=False, minimal=False, nullPointers=True, **kwargs):
    """Diff the printed form of two objects with ``diff -bw``."""

    if "null.pointers" in kwargs or "null_pointers" in kwargs:
        nullPointers = kwargs.pop("null.pointers", kwargs.pop("null_pointers", nullPointers))
    if kwargs:
        unknown = ", ".join(kwargs)
        raise TypeError(f"unused arguments ({unknown})")
    _true_false(silent, "silent")
    _true_false(minimal, "minimal")
    paths = []
    try:
        for value in (source, target):
            path = _maybe_file(value)
            shown = path if path is not None else value
            lines = r_print(shown if path is None else path, 80)
            folder = Path(tempfile.mkdtemp())
            file_path = folder / "obj"
            _write_lines(lines, file_path)
            paths.append(file_path)
        lines = _diff_lines(paths[0], paths[1], nullPointers)
    except ValueError:
        raise ValueError("Unable to store text representation of objects") from None
    finally:
        for file_path in paths:
            file_path.unlink(missing_ok=True)
            file_path.parent.rmdir()
    return _finish(lines, silent, minimal)


def has_Rdiff(test_with=None) -> bool:
    """Whether ``diff -bw`` can be run. A missing ``diff`` is false."""

    if shutil.which("diff") is None:
        return False
    if test_with is None:
        test_with = _tools_rdiff
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        left = folder / "a"
        right = folder / "b"
        _write_lines(list("abc"), left)
        _write_lines(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), right)
        try:
            test_with(str(left), str(right), use_diff=True, log=True, null_pointers=False)
        except Warning:
            return False
    return True
