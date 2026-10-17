"""Progress bars in a session that is not a dynamic terminal.

A non-interactive Rscript session does not draw the bar. The variables
stay empty until a formatter asks for them, and the demo captures no
live frames. This module follows that session.
"""

from __future__ import annotations

from pathlib import Path

from cli.messages import new_uuid

_BARS: dict[str, dict] = {}


def _handlers() -> list[str]:
    path = Path(__file__).parent / "data" / "progress_handlers.txt"
    return path.read_text(encoding="utf-8").splitlines()


def cli_progress_builtin_handlers() -> list[str]:
    return _handlers()


def cli_progress_styles() -> dict:
    return {
        "classic": {"complete": "#", "incomplete": "\u00a0"},
        "squares": {"complete": "■", "incomplete": "\u00a0"},
        "dot": {"complete": "─", "incomplete": "─"},
        "fillsquares": {"complete": "■", "incomplete": "□"},
        "bar": {"complete": "█", "incomplete": "█"},
    }


def cli_progress_num() -> int:
    return len(_BARS)


def cli_progress_bar(
    name=None,
    status=None,
    type="iterator",
    total=None,
    format=None,
    format_done=None,
    format_failed=None,
    clear=True,
    current=True,
    auto_terminate=True,
    extra=None,
    auto_close=True,
    envir=None,
):
    ident = new_uuid()
    _BARS[ident] = {
        "id": ident,
        "name": name,
        "status": status,
        "total": total,
        "current": 0 if current is True else current,
    }
    return ident


def cli_progress_update(inc=None, set=None, total=None, status=None, id=None, force=False, envir=None):
    if not _BARS:
        raise RuntimeError("there is no current progress bar")
    ident = id or next(reversed(_BARS))
    bar = _BARS.get(ident)
    if bar is None:
        return None
    if set is not None:
        bar["current"] = set
    elif inc is not None:
        bar["current"] = (bar["current"] or 0) + inc
    else:
        bar["current"] = (bar["current"] or 0) + 1
    if total is not None:
        bar["total"] = total
    if status is not None:
        bar["status"] = status
    return ident


def cli_progress_done(id=None, result="done", envir=None):
    if _BARS:
        ident = id or next(reversed(_BARS))
        _BARS.pop(ident, None)
    return True


def cli_progress_cleanup():
    _BARS.clear()
    return None


def cli_progress_output(text, id=None, envir=None):
    if not _BARS:
        raise RuntimeError("there is no current progress bar")
    return None


def cli_progress_message(msg, current=True, id=None, envir=None):
    return new_uuid()


def cli_progress_step(msg, spinner=False, class_=None, envir=None):
    return cli_progress_bar(name=msg)


def cli_progress_along(x, name=None, total=None, envir=None):
    cli_progress_bar(name=name, total=len(x) if total is None else total)
    return list(range(1, len(x) + 1))


def cli_progress_demo(
    name=None,
    status=None,
    type="iterator",
    total=None,
    envir=None,
    at=None,
    show_after=0,
    live=False,
    delay=0,
    start=5,
):
    return {"lines": []}


def __cli_update_due():
    return False


def cli_tick_reset():
    return None


def ccli_tick_reset():
    return None


def ticking(cond, name=None, envir=None):
    if cond:
        if not _BARS:
            cli_progress_bar(name=name)
        cli_progress_update()
    else:
        cli_progress_done()
    return cond


def _empty():
    return ""


pb_bar = pb_current = pb_current_bytes = pb_elapsed = pb_elapsed_clock = _empty
pb_elapsed_raw = pb_eta = pb_eta_raw = pb_eta_str = pb_extra = pb_id = _empty
pb_name = pb_percent = pb_pid = pb_rate = pb_rate_bytes = pb_rate_raw = _empty
pb_spin = pb_status = pb_timestamp = pb_total = pb_total_bytes = _empty


def cli_status(msg, msg_done=None, msg_failed=None, id=None, auto_close=True, envir=None, auto_result="auto"):
    from cli.messages import format_inline
    import sys

    rendered = format_inline(msg, envir=envir) if isinstance(msg, str) else str(msg)
    sys.stderr.write(rendered + "\n")
    return id or new_uuid()


def cli_status_update(id, msg=None, msg_done=None, msg_failed=None, envir=None):
    if msg is not None:
        return cli_status(msg, msg_done, msg_failed, id=id, envir=envir)
    return id


def cli_status_clear(id=None, result="clear", envir=None):
    return None


def cli_process_start(
    msg,
    msg_done=None,
    msg_failed=None,
    on_exit="auto",
    msg_class="alert-info",
    done_class="alert-success",
    failed_class="alert-danger",
    auto_close=True,
    envir=None,
):
    if msg_done is None:
        msg_done = f"{msg} ... done"
    if msg_failed is None:
        msg_failed = f"{msg} ... failed"
    if msg_class:
        msg = "{." + msg_class + " " + msg + "}"
    return cli_status(msg, msg_done, msg_failed, envir=envir)


def cli_process_done(id=None, msg=None, msg_done=None, envir=None):
    return None


def cli_process_failed(id=None, msg=None, msg_failed=None, envir=None):
    return None
