"""Signal numbers, pskill, and psnice. The numbers are the host's POSIX signals."""

from __future__ import annotations

import os
import signal

SIGCHLD = signal.SIGCHLD
SIGCONT = signal.SIGCONT
SIGHUP = signal.SIGHUP
SIGINT = signal.SIGINT
SIGKILL = signal.SIGKILL
SIGQUIT = signal.SIGQUIT
SIGSTOP = signal.SIGSTOP
SIGTERM = signal.SIGTERM
SIGTSTP = signal.SIGTSTP
SIGUSR1 = signal.SIGUSR1
SIGUSR2 = signal.SIGUSR2


def pskill(pid: int, signal_number: int = SIGTERM) -> bool:
    """Send a signal. False when the process does not exist or the signal is refused."""
    number = int(pid)
    if number <= 0:
        return False
    try:
        os.kill(number, int(signal_number))
    except OSError:
        return False
    return True


def psnice(pid: int | None = None, value: int | None = None) -> int:
    """Read the nice value, or set it when value is an integer. None means NA."""
    if pid is None:
        pid = os.getpid()
    current = os.getpriority(os.PRIO_PROCESS, pid)
    if value is None:
        return current
    os.setpriority(os.PRIO_PROCESS, pid, int(value))
    return current
