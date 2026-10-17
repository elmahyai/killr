"""Return whether pbapply should show a progress bar."""

from __future__ import annotations

from typing import Any, Sequence

_session_options: dict[str, Any] = {}


def replace_session_options(**tags: Any) -> dict[str, Any]:
    """Set R-style session options; proof scripts use this for knitr.in.progress."""
    former: dict[str, Any] = {}
    for key, value in tags.items():
        if key in _session_options:
            former[key] = _session_options[key]
        if value is None:
            _session_options.pop(key, None)
        else:
            _session_options[key] = value
    return former


def reset_session_options(former: dict[str, Any] | None = None) -> None:
    """Restore session options from replace_session_options."""
    if former is None:
        _session_options.clear()
        return
    for key in list(_session_options):
        if key not in former:
            del _session_options[key]
    for key, value in former.items():
        _session_options[key] = value


def dopb() -> bool:
    """Mirror pbapply::dopb using the module pboptions dict and session options."""
    from pbapply.startpb import _pboptions, _pbtypes

    progress_bar = _pboptions.get("type")
    if progress_bar is not None:
        progress_bar = _match_arg(progress_bar, _pbtypes())
        if progress_bar == "none":
            progress_bar = None
        if _session_options.get("knitr.in.progress") is not None:
            progress_bar = None
    return progress_bar is not None


def _match_arg(arg: Any, choices: Sequence[str]) -> str:
    choices_tuple = tuple(choices)
    if not isinstance(arg, str):
        raise ValueError("'arg' must be NULL or a character vector")
    exact = [choice for choice in choices_tuple if choice == arg]
    if len(exact) == 1:
        return exact[0]
    partial = [choice for choice in choices_tuple if choice.startswith(arg)]
    if len(partial) == 1:
        return partial[0]
    quoted = ", ".join("\u201c" + choice + "\u201d" for choice in choices_tuple)
    raise ValueError(f"'arg' should be one of {quoted}")
