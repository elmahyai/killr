import contextlib
import io
import statistics
import time
from cli._options import options
options(**{"cli.num_colors": 8, "cli.unicode": True, "cli.width": 80})
from cli import *
from cli.messages import format_sitrep

def message(fn):
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        fn()
    return "\n".join(buf.getvalue().splitlines())

def style_text(style):
    width = max(len(name) for name in style)
    return "\n".join(f"{name.ljust(width)} {style[name]}" for name in style)

def link_of():
    options(**{"cli.hyperlink": True})
    try:
        return style_hyperlink("click", "https://example.com")
    finally:
        options(**{"cli.hyperlink": None})

def demo_error():
    try:
        demo_spinners("nope")
    except ValueError as exc:
        return str(exc)

def key_error():
    try:
        keypress()
    except RuntimeError as exc:
        return str(exc)

def abort_message():
    try:
        cli_abort("nope")
    except RuntimeError as exc:
        return str(exc)

def printed():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cat_print("hi")
    return "\n".join(buf.getvalue().splitlines())

def emit(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int) and not isinstance(value, bool):
        return format(value, ".17g") if False else str(value)
    if isinstance(value, float):
        return format(value, ".17g")
    return "" if value is None else str(value)

def one():
    return format_message("hello")

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if value is None:
    print('NULL')
elif isinstance(value, bool):
    print('TRUE' if value else 'FALSE')
elif isinstance(value, int) and not isinstance(value, bool):
    print(f'NUM {value}')
elif isinstance(value, float):
    print(f'NUM {value:.17g}')
else:
    print('STR ' + ','.join(str(byte) for byte in str(value).encode()))
print(f'MS {statistics.median(elapsed):.17g}')
