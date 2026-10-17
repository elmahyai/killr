"""Pure-Python fallback for coxfit6 (slow; install the coxfit6 crate)."""

from __future__ import annotations


def coxfit6(**kwargs):
    raise RuntimeError("install the coxfit6 Rust extension for Cox model fitting")


def coxmart(**kwargs):
    raise RuntimeError("install the coxfit6 Rust extension for Cox model fitting")
