"""Evaluate source and replay what it produced."""

from __future__ import annotations

import inspect
import sys
import warnings

from evaluate.extras import flush_console, inject_funs, remove_hooks, set_console_flusher, set_hooks
from evaluate.graphics import (
    Device,
    draw_plot,
    lines,
    looks_different,
    makes_visual_change,
    par,
    plot,
    plot_new,
    points,
    text,
    trim_intermediate_plots,
)
from evaluate.handlers import (
    handle_value,
    identity,
    new_output_handler,
    new_source,
    show_value,
)
from evaluate.parse import (
    Binary,
    Brace,
    Call,
    For,
    Function,
    If,
    Literal,
    Name,
    Paren,
    ParseError,
    Unary,
    deparse,
    parse_all,
    parse_expr,
)
from evaluate.show import as_list, cat, format_atom, r_print
from evaluate.state import SENTINEL, STATE, dev_cur, push_handlers
from evaluate.types import (
    Error,
    Evaluation,
    Invisible,
    Message,
    RecordedPlot,
    Restart,
    Source,
    Vector,
    Warning,
    format_condition,
    new_evaluation,
    output_type,
)


class RFunction:
    def __init__(self, params, body, enclos) -> None:
        self.params = params
        self.body = body
        self.enclos = enclos


class _Sink:
    def __init__(self, echo: bool, real) -> None:
        self.parts: list[str] = []
        self.echo = echo
        self.real = real

    def write(self, text: str) -> int:
        self.parts.append(text)
        if self.echo:
            self.real.write(text)
        return len(text)

    def flush(self) -> None:
        return None

    def getvalue(self) -> str:
        return "".join(self.parts)

    def clear(self) -> None:
        self.parts.clear()


def _paste(args, sep: str = "") -> str:
    parts = []
    for arg in args:
        if isinstance(arg, Vector):
            parts.append(sep.join(format_atom(item) for item in arg.data))
        else:
            parts.append(format_atom(arg))
    return sep.join(parts)


def _caller_call():
    if STATE.stack:
        return STATE.stack[-1]
    return SENTINEL


def stop(*args, call=None):
    text = _paste(args)
    raise Error(text, call=_caller_call() if call is None else call)


def warning(*args, call=None):
    message = _paste(args)
    warn = STATE.options.get("warn", 0)
    if warn >= 2:
        raise Error("(converted from warning) " + message, call=_caller_call() if call is None else call)
    if warn < 0:
        return Invisible(None)
    condition = Warning(message, call=_caller_call() if call is None else call)
    _signal("warning", condition)
    return Invisible(None)


def message(*args, sep: str = ""):
    text = _paste(args, sep=sep)
    if not text.endswith("\n"):
        text += "\n"
    condition = Message(text, call=_caller_call())
    _signal("message", condition)
    return Invisible(None)


def invisible(value=None):
    return Invisible(value)


def c(*args):
    data = []
    for arg in args:
        if isinstance(arg, Vector):
            data.extend(arg.data)
        else:
            data.append(arg)
    return Vector(data)


def _signal(kind: str, condition) -> None:
    try:
        for table in list(STATE.handlers):
            fn = table.get(kind)
            if fn is not None:
                fn(condition)
    except Restart as restart:
        if restart.name in {"muffleMessage", "muffleWarning"}:
            return
        raise
    if kind == "message":
        text = condition.message
        if not text.endswith("\n"):
            text += "\n"
        sys.stderr.write(text)
    elif kind == "warning":
        sys.stderr.write(format_condition(condition) + "\n")


def _base_env():
    env = Env()
    env.set("c", c)
    env.set("cat", cat)
    env.set("print", r_print)
    env.set("message", message)
    env.set("warning", warning)
    env.set("stop", stop)
    env.set("plot", plot)
    env.set("text", text)
    env.set("lines", lines)
    env.set("points", points)
    env.set("par", par)
    env.set("plot.new", plot_new)
    env.set("invisible", invisible)
    env.set("flush_console", flush_console)
    env.set("TRUE", True)
    env.set("FALSE", False)
    env.set("NULL", None)
    env.set("NA", None)
    env.set("Inf", float("inf"))
    env.set("NaN", float("nan"))
    return env


class Env:
    def __init__(self, bindings=None, parent=None) -> None:
        self.bindings = {} if bindings is None else bindings
        self.parent = parent

    def get(self, name):
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise Error(f"object '{name}' not found", call=_caller_call())

    def set(self, name, value) -> None:
        self.bindings[name] = value


BASE = _base_env()


def _truth(value) -> bool:
    if isinstance(value, Vector):
        if len(value.data) != 1:
            raise Error("condition has length other than 1", call=_caller_call())
        return _truth(value.data[0])
    return bool(value)


def _colon(left, right) -> Vector:
    start = int(left)
    end = int(right)
    step = 1 if end >= start else -1
    return Vector(list(range(start, end + step, step)))


def _scalar_bin(op, left, right):
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        return left / right
    if op == "^":
        return left ** right
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if op == "<":
        return left < right
    if op == ">":
        return left > right
    if op == "<=":
        return left <= right
    if op == ">=":
        return left >= right
    if op == "&":
        return bool(left) and bool(right)
    if op == "|":
        return bool(left) or bool(right)
    raise Error(f"unsupported operator {op}", call=_caller_call())


def _binop(op, left, right):
    if isinstance(left, Vector) or isinstance(right, Vector):
        aa = as_list(left)
        bb = as_list(right)
        if len(aa) == 1 and len(bb) != 1:
            aa = aa * len(bb)
        if len(bb) == 1 and len(aa) != 1:
            bb = bb * len(aa)
        return Vector([_scalar_bin(op, a, b) for a, b in zip(aa, bb)])
    return _scalar_bin(op, left, right)


def _assign(target, value, env: Env) -> None:
    if isinstance(target, Name):
        env.set(target.name, value)
        return
    raise Error("invalid assignment", call=_caller_call())


def eval_visible(node, env: Env):
    if isinstance(node, Literal):
        return node.value, True
    if isinstance(node, Name):
        return env.get(node.name), True
    if isinstance(node, Paren):
        return eval_visible(node.expr, env)
    if isinstance(node, Brace):
        value, visible = None, False
        for expr in node.body:
            value, visible = eval_visible(expr, env)
        return value, visible
    if isinstance(node, Unary):
        value, _visible = eval_visible(node.expr, env)
        if node.op == "-":
            if isinstance(value, Vector):
                return Vector([-item for item in value.data]), True
            return -value, True
        if node.op == "+":
            return value, True
        if node.op == "!":
            return (not _truth(value)), True
        raise Error(f"unsupported operator {node.op}", call=_caller_call())
    if isinstance(node, Binary):
        if node.op in {"<-", "<<-", "="}:
            value, _visible = eval_visible(node.right, env)
            _assign(node.left, value, env)
            return value, False
        if node.op in {"->", "->>"}:
            value, _visible = eval_visible(node.left, env)
            _assign(node.right, value, env)
            return value, False
        if node.op == "&&":
            left, _visible = eval_visible(node.left, env)
            if not _truth(left):
                return False, True
            right, _visible = eval_visible(node.right, env)
            return _truth(right), True
        if node.op == "||":
            left, _visible = eval_visible(node.left, env)
            if _truth(left):
                return True, True
            right, _visible = eval_visible(node.right, env)
            return _truth(right), True
        if node.op == ":":
            left, _visible = eval_visible(node.left, env)
            right, _visible = eval_visible(node.right, env)
            return _colon(left, right), True
        left, _visible = eval_visible(node.left, env)
        right, _visible = eval_visible(node.right, env)
        return _binop(node.op, left, right), True
    if isinstance(node, If):
        cond, _visible = eval_visible(node.cond, env)
        if _truth(cond):
            return eval_visible(node.then, env)
        if node.else_ is not None:
            return eval_visible(node.else_, env)
        return None, False
    if isinstance(node, For):
        seq, _visible = eval_visible(node.seq, env)
        for item in as_list(seq):
            env.set(node.var, item)
            eval_visible(node.body, env)
        return None, False
    if isinstance(node, Function):
        return RFunction(node.params, node.body, env), True
    if isinstance(node, Call):
        return _call(node, env)
    raise Error("cannot evaluate expression", call=_caller_call())


def _call(node: Call, env: Env):
    if isinstance(node.func, Name):
        try:
            fn = env.get(node.func.name)
        except Error:
            raise
    else:
        fn, _visible = eval_visible(node.func, env)
    pairs = []
    for name, arg in node.args:
        value, _visible = eval_visible(arg, env)
        pairs.append((name, value))
    if isinstance(fn, RFunction):
        return _call_r(fn, node, pairs)
    if not callable(fn):
        raise Error("attempt to apply non-function", call=_caller_call())
    positional = [value for name, value in pairs if name is None]
    keywords = {name: value for name, value in pairs if name is not None}
    try:
        result = fn(*positional, **keywords)
    except (Error, Restart):
        raise
    except Exception as exc:
        raise Error(str(exc), call=_caller_call()) from exc
    if isinstance(result, Invisible):
        return result.value, False
    return result, True


def _call_r(fn: RFunction, node: Call, pairs):
    local = Env({}, parent=fn.enclos)
    positional = [value for name, value in pairs if name is None]
    named = {name: value for name, value in pairs if name is not None}
    index = 0
    for name, default in fn.params:
        if name == "...":
            continue
        if name in named:
            local.set(name, named.pop(name))
        elif index < len(positional):
            local.set(name, positional[index])
            index += 1
        elif default is not None:
            value, _visible = eval_visible(default, local)
            local.set(name, value)
        else:
            raise Error(f"argument \"{name}\" is missing, with no default", call=node)
    STATE.stack.append(node)
    try:
        return eval_visible(fn.body, local)
    finally:
        STATE.stack.pop()


class Watcher:
    def __init__(self, handler, debug: bool, real_stdout) -> None:
        self.handler = handler
        self.output = []
        self.last_dl = None
        self.sink = _Sink(debug, real_stdout)
        self.device_at_start = len(STATE.devices)

    def push(self, value) -> None:
        self.output.append(value)
        kind = output_type(value)
        handler = {
            "plot": self.handler["graphics"],
            "text": self.handler["text"],
            "message": self.handler["message"],
            "warning": self.handler["warning"],
            "error": self.handler["error"],
        }.get(kind)
        if handler is not None and handler is not identity:
            handler(value)
        elif handler is identity:
            handler(value)

    def push_source(self, src, exprs) -> None:
        source = new_source(src, exprs, self.handler["source"])
        if source is not None:
            self.push(source)

    def capture_plot(self, incomplete: bool = False) -> None:
        dev = dev_cur()
        if dev is None:
            return
        if not dev.page() and not incomplete:
            return
        if not makes_visual_change(dev.dl):
            return
        if not looks_different(self.last_dl, dev.dl):
            return
        self.last_dl = list(dev.dl)
        self.push(RecordedPlot(self.last_dl))

    def capture_output(self) -> None:
        text = self.sink.getvalue()
        self.sink.clear()
        if text:
            self.push(text)

    def capture_plot_and_output(self) -> None:
        self.capture_plot()
        self.capture_output()

    def print_value(self, value, visible, env) -> None:
        if not show_value(self.handler, visible):
            return
        result, result_visible = handle_value(self.handler, value, visible, env)
        self.capture_plot_and_output()
        if result_visible:
            self.push(result)

    def check_devices(self) -> None:
        return None

    def get(self) -> Evaluation:
        return new_evaluation(self.output)


def _sanitize(condition):
    if deparse(condition.call) == "eval(expr, envir)":
        condition.call = None
    return condition


def _condition_handlers(watcher: Watcher, on_error: str, on_warning: dict, on_message: dict):
    def on_message_fn(condition):
        watcher.capture_plot_and_output()
        if on_message["capture"]:
            watcher.push(condition)
        if on_message["silence"]:
            raise Restart("muffleMessage")

    def on_warning_fn(condition):
        warn = STATE.options.get("warn", 0)
        if warn >= 2 or warn < 0:
            return
        watcher.capture_plot_and_output()
        if on_warning["capture"]:
            watcher.push(_sanitize(condition))
        if on_warning["silence"]:
            raise Restart("muffleWarning")

    def on_error_fn(condition):
        watcher.capture_plot_and_output()
        watcher.push(_sanitize(condition))
        if on_error == "continue":
            raise Restart("eval_continue")
        if on_error == "stop":
            raise Restart("eval_stop")
        raise condition

    return {"message": on_message_fn, "warning": on_warning_fn, "error": on_error_fn}


def _check_stop_on_error(value) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("`stop_on_error` must be 0, 1, or 2.")
    if value != value:
        raise ValueError("`stop_on_error` must be 0, 1, or 2.")
    if value == 0:
        return "continue"
    if value == 1:
        return "stop"
    if value == 2:
        return "error"
    raise ValueError("`stop_on_error` must be 0, 1, or 2.")


def _check_keep(value, arg: str, log: bool = False) -> dict:
    if not isinstance(value, bool) and value is not None:
        raise ValueError(f"`{arg}` must be TRUE, FALSE, or NA.")
    if isinstance(value, bool) and not isinstance(value, bool):
        raise ValueError(f"`{arg}` must be TRUE, FALSE, or NA.")
    return {"capture": value is True, "silence": value is not None and not log}


def _can_parse(value) -> bool:
    if not _is_character(value):
        return True
    try:
        parse_all(value)
    except ParseError:
        return False
    return True


def _is_character(value) -> bool:
    if isinstance(value, str):
        return True
    return isinstance(value, (list, tuple)) and all(isinstance(item, str) for item in value)


def _parse_error_for(value) -> Error:
    try:
        parse_all(value)
    except ParseError as exc:
        return Error(exc.message, call=Name(1, 1, "parse(text = input)"))
    raise Error("parse failed", call=None)


def line_prompt(x: str, prompt=None, continue_=None) -> str:
    if prompt is None:
        prompt = STATE.options.get("prompt", "> ")
    if continue_ is None:
        continue_ = STATE.options.get("continue", "+ ")
    lines = x.split("\n")
    if x.endswith("\n"):
        lines = lines[:-1]
    if not lines:
        lines = [""]
    lines[0] = f"{prompt}{lines[0]}"
    for index in range(1, len(lines)):
        lines[index] = f"{continue_}{lines[index]}"
    return "".join(line + "\n" for line in lines)


def replay(x):
    if isinstance(x, (Evaluation, list)) and not isinstance(x, (str, Vector, RecordedPlot)):
        for item in x:
            replay(item)
        return None
    if isinstance(x, str):
        sys.stdout.write(x)
        return None
    if isinstance(x, Source):
        sys.stdout.write(line_prompt(x.src))
        return None
    if isinstance(x, (Message, Warning, Error)):
        sys.stdout.write(format_condition(x) + "\n")
        return None
    if isinstance(x, RecordedPlot):
        draw_plot(x)
        return None
    r_print(x)
    return None


def create_traceback(callstack) -> list[str] | None:
    if callstack is None or len(callstack) == 0:
        return None
    rendered = []
    for index, call in enumerate(callstack, start=1):
        if isinstance(call, str):
            text = deparse(parse_expr(call), width=500)
        else:
            text = deparse(call, width=500)
        text = text.replace("\n", "\n   ", 1)
        rendered.append(f"{index}: {text}")
    return rendered


def try_capture_stack(quoted_code, env=None):
    if isinstance(quoted_code, str):
        quoted_code = parse_expr(quoted_code)
    if env is None:
        env = Env({}, parent=BASE)
    elif not isinstance(env, Env):
        env = Env(dict(env), parent=BASE)
    STATE.stack.append(SENTINEL)
    try:
        try:
            eval_visible(quoted_code, env)
        except Error as exc:
            calls = [quoted_code]
            exc.calls = calls
            return exc
        return None
    finally:
        STATE.stack.pop()


def evaluate(
    input,
    envir=None,
    enclos=None,
    debug: bool = False,
    stop_on_error=0,
    keep_warning=True,
    keep_message=True,
    log_echo: bool = False,
    log_warning: bool = False,
    new_device: bool = True,
    output_handler=None,
    filename=None,
    include_timing: bool = False,
):
    on_error = _check_stop_on_error(stop_on_error)
    if _env_true("R_EVALUATE_BYPASS_MESSAGES"):
        keep_message = None
        keep_warning = None
    if _env_true("ACTIONS_STEP_DEBUG"):
        log_warning = True
        log_echo = True
    on_message = _check_keep(keep_message, "keep_message")
    on_warning = _check_keep(keep_warning, "keep_warning", log_warning)
    if output_handler is None:
        output_handler = new_output_handler()
    if include_timing is True:
        warnings.warn("`evaluate(include_timing)` is deprecated", stacklevel=2)

    if envir is None:
        frame = inspect.currentframe()
        caller = frame.f_back if frame is not None else None
        bindings = dict(caller.f_locals) if caller is not None else {}
        envir = Env(bindings, parent=BASE)
    elif not isinstance(envir, Env):
        parent = enclos if isinstance(enclos, Env) else BASE
        envir = Env(envir, parent=parent)

    real_stdout = sys.stdout
    watcher = Watcher(output_handler, debug, real_stdout)
    STATE.watcher = watcher
    sys.stdout = watcher.sink
    opened = False
    if new_device:
        STATE.devices.append(Device())
        opened = True
    hook_list = {
        "persp": watcher.capture_plot_and_output,
        "before.plot.new": watcher.capture_plot_and_output,
        "before.grid.newpage": watcher.capture_plot_and_output,
    }
    set_hooks(hook_list)
    old_flusher = set_console_flusher(watcher.capture_output)
    injected = _install_injected(envir)
    try:
        if on_error != "error" and not _can_parse(input):
            err = _parse_error_for(input)
            shown = input if isinstance(input, str) else "\n".join(input)
            watcher.push_source(shown, [])
            watcher.push(_sanitize(err))
            return watcher.get()
        parsed = parse_all(input, filename=filename)
        handlers = []
        if output_handler["calling_handlers"]:
            handlers.append(output_handler["calling_handlers"])
        handlers.append(_condition_handlers(watcher, on_error, on_warning, on_message))
        for src, exprs in parsed.rows:
            watcher.push_source(src, exprs)
            if debug or log_echo:
                sys.stderr.write(src + "\n")
            try:
                with push_handlers(handlers):
                    try:
                        for expr in exprs:
                            STATE.stack.append(SENTINEL)
                            try:
                                value, visible = eval_visible(expr, envir)
                            finally:
                                if STATE.stack and STATE.stack[-1] is SENTINEL:
                                    STATE.stack.pop()
                            watcher.capture_plot_and_output()
                            watcher.print_value(value, visible, envir)
                    except Error as exc:
                        for table in STATE.handlers:
                            fn = table.get("error")
                            if fn is not None:
                                fn(exc)
                        raise exc
            except Restart as restart:
                if restart.name == "eval_stop":
                    break
                if restart.name == "eval_continue":
                    continue
                raise
        watcher.capture_plot(True)
        return watcher.get()
    finally:
        set_console_flusher(old_flusher)
        remove_hooks(hook_list)
        for name in injected:
            envir.bindings.pop(name, None)
        if opened and STATE.devices:
            STATE.devices.pop()
        sys.stdout = real_stdout
        STATE.watcher = None


def _install_injected(env: Env) -> list[str]:
    names = []
    for name, fn in STATE.inject.items():
        if name not in env.bindings and callable(fn):
            env.set(name, fn)
            names.append(name)
    return names


def _env_true(name: str) -> bool:
    from evaluate.state import env_var_is_true

    return env_var_is_true(name)


# The default handler used by evaluate(). Built once, as in the R package.
evaluate_default_handler = None
