"""Run R CMD the way tools::Rcmd does."""

import os
import subprocess
import sys


def rcmd(args):
    """Run R CMD and return the status code. Output is written as R's system2 writes it."""
    if isinstance(args, str):
        args = [args]
    else:
        args = [str(arg) for arg in args]
    r_home = os.environ.get("R_HOME", "/usr/lib/R")
    if os.name == "nt":
        command = [os.path.join(r_home, "bin", "Rcmd.exe"), *args]
    else:
        command = [os.path.join(r_home, "bin", "R"), "CMD", *args]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.stdout:
        sys.stdout.write(completed.stdout)
    if completed.stderr:
        sys.stderr.write(completed.stderr)
    return completed.returncode
