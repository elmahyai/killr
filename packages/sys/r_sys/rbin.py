"""Run the R binary through exec_wait."""

import os
import subprocess

from r_sys.exec import exec_background, exec_internal, exec_wait


def rbin():
    home = os.environ.get("R_HOME")
    if not home:
        home = subprocess.check_output(["R", "RHOME"], text=True).strip()
    name = "Rterm" if os.name == "nt" else "R"
    return os.path.join(home, "bin", name)


def r_wait(args="--vanilla", std_out=None, std_err=None, std_in=None):
    """Run R and wait. The default arguments are ``--vanilla``."""
    if std_out is None:
        std_out = True
    if std_err is None:
        std_err = True
    return exec_wait(rbin(), args=args, std_out=std_out, std_err=std_err, std_in=std_in)


def r_internal(args="--vanilla", std_in=None, error=True):
    """Run R and capture both streams."""
    return exec_internal(rbin(), args=args, std_in=std_in, error=error)


def r_background(args="--vanilla", std_out=True, std_err=True, std_in=None):
    """Start R and return the process id."""
    return exec_background(rbin(), args=args, std_out=std_out, std_err=std_err, std_in=std_in)
