"""Run a program with subprocess.

``exec_wait`` returns the exit code. ``exec_status`` returns the wait status
word used by waitpid: exit 1 is 256, and a signal is the signal number.
"""

from __future__ import annotations

import os
import signal
import subprocess
import threading
import time

_CHILDREN = {}


class SysError(Exception):
    """A condition raised by sys."""


def _args(cmd, args):
    if not isinstance(cmd, str):
        raise TypeError("cmd must be a string")
    cmd = os.path.expanduser(cmd)
    parts = [cmd]
    if args is None:
        return cmd, parts
    if isinstance(args, str):
        args = [args]
    if os.name == "nt":
        from r_sys.quote import windows_quote

        args = windows_quote(list(args))
    parts.extend(str(item) for item in args)
    return cmd, parts


def _status_word(returncode):
    if returncode is None:
        return None
    if returncode < 0:
        return -returncode
    if returncode == 0:
        return 0
    return returncode << 8


def _remember(process):
    _CHILDREN[process.pid] = process
    return process.pid


def _destination(target, default_stream):
    if target is True or target == "":
        return None
    if target is False:
        return subprocess.DEVNULL
    if isinstance(target, str):
        return open(os.path.abspath(target), "wb")
    if callable(target):
        return subprocess.PIPE
    raise SysError("std_out and std_err must be TRUE, FALSE, a filename, or a function")


def _feed(pipe, target, own_files):
    if pipe is None or not callable(target):
        return
    while True:
        chunk = pipe.read(65336)
        if not chunk:
            break
        target(chunk)


def exec_wait(cmd, args=None, std_out=True, std_err=True, std_in=None, timeout=0):
    """Run a command and return its exit code."""
    command, argv = _args(cmd, args)
    files = []
    try:
        out = _destination(std_out, None)
        err = _destination(std_err, None)
        if isinstance(out, object) and hasattr(out, "close") and not callable(std_out):
            if out not in (None, subprocess.DEVNULL, subprocess.PIPE):
                files.append(out)
        if err not in (None, subprocess.DEVNULL, subprocess.PIPE) and hasattr(err, "close"):
            files.append(err)
        stdin = subprocess.DEVNULL
        if isinstance(std_in, str):
            stdin = open(os.path.abspath(std_in), "rb")
            files.append(stdin)
        try:
            process = subprocess.Popen(
                argv,
                stdout=subprocess.PIPE if callable(std_out) else out,
                stderr=subprocess.PIPE if callable(std_err) else err,
                stdin=stdin,
            )
        except FileNotFoundError as exc:
            raise SysError(
                f"Failed to execute '{command}' (No such file or directory)"
            ) from exc
        limit = None if not timeout else time.monotonic() + float(timeout)
        try:
            if callable(std_out) or callable(std_err):
                _pump(process, std_out, std_err, limit, command, timeout)
            else:
                _wait(process, limit, command, timeout)
        finally:
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()
        code = process.returncode
        if code is None:
            code = process.wait()
        if code < 0:
            _killed(command, -code, timeout, limit)
        return int(code)
    finally:
        for handle in files:
            handle.close()


def _wait(process, limit, command, timeout):
    if limit is None:
        process.wait()
        return
    remaining = limit - time.monotonic()
    try:
        process.wait(timeout=max(0, remaining))
    except subprocess.TimeoutExpired:
        _timeout_kill(process, command, timeout)


def _read_pipe(pipe, target):
    while True:
        chunk = pipe.read(65336)
        if not chunk:
            break
        target(chunk)


def _pump(process, std_out, std_err, limit, command, timeout):
    threads = []
    if callable(std_out) and process.stdout is not None:
        threads.append(threading.Thread(target=_read_pipe, args=(process.stdout, std_out)))
    if callable(std_err) and process.stderr is not None:
        threads.append(threading.Thread(target=_read_pipe, args=(process.stderr, std_err)))
    for thread in threads:
        thread.start()
    try:
        _wait(process, limit, command, timeout)
    finally:
        for thread in threads:
            thread.join()


def _timeout_kill(process, command, timeout):
    process.send_signal(signal.SIGINT)
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    raise SysError(f"Program '{command}' terminated (timeout reached: {float(timeout):.2f}sec)")


def _killed(command, signum, timeout, limit):
    if timeout and limit is not None and time.monotonic() > limit:
        raise SysError(f"Program '{command}' terminated (timeout reached: {float(timeout):.2f}sec)")
    name = signal.strsignal(signum) or str(signum)
    raise SysError(f"Program '{command}' terminated by SIGNAL ({name})")


def exec_background(cmd, args=None, std_out=True, std_err=True, std_in=None):
    """Start a command and return its process id."""
    if not isinstance(std_out, (bool, str)):
        raise SysError("argument 'std_out' must be TRUE / FALSE or a filename")
    if not isinstance(std_err, (bool, str)):
        raise SysError("argument 'std_err' must be TRUE / FALSE or a filename")
    command, argv = _args(cmd, args)
    out = None if std_out is True else subprocess.DEVNULL if std_out is False else open(std_out, "wb")
    err = None if std_err is True else subprocess.DEVNULL if std_err is False else open(std_err, "wb")
    stdin = subprocess.DEVNULL
    if isinstance(std_in, str):
        stdin = open(std_in, "rb")
    try:
        process = subprocess.Popen(argv, stdout=out, stderr=err, stdin=stdin)
    except FileNotFoundError as exc:
        raise SysError(f"Failed to execute '{command}' (No such file or directory)") from exc
    return _remember(process)


def exec_internal(cmd, args=None, std_in=None, error=True, timeout=0):
    """Capture stdout and stderr. A non-zero exit is an error when error is true."""
    stdout = bytearray()
    stderr = bytearray()
    status = exec_wait(
        cmd,
        args=args,
        std_out=stdout.extend,
        std_err=stderr.extend,
        std_in=std_in,
        timeout=timeout,
    )
    if error and status != 0:
        raise SysError(f"Executing '{cmd}' failed with status {status}")
    return {"status": status, "stdout": bytes(stdout), "stderr": bytes(stderr)}


def exec_status(pid, wait=True):
    """Return the wait status, or None while the process is still running."""
    process = _CHILDREN.get(int(pid))
    if process is None:
        if not wait:
            return None
        waited, word = os.waitpid(int(pid), 0)
        return int(word)
    if wait:
        process.wait()
    else:
        process.poll()
    return _status_word(process.returncode)
