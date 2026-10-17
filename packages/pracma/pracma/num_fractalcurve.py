"""Deterministic fractal polylines."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import match_arg


def _real_imag(z):
    values = np.asarray(z, dtype=np.complex128).reshape(-1)
    return {"x": np.real(values).astype(float), "y": np.imag(values).astype(float)}


def fractalcurve(n, which=("hilbert", "sierpinski", "snowflake", "dragon", "triangle", "arrowhead", "flowsnake", "molecule")):
    curve = match_arg(which, ("hilbert", "sierpinski", "snowflake", "dragon", "triangle", "arrowhead", "flowsnake", "molecule"))
    steps = int(n)
    if curve == "hilbert":
        a = 1 + 1j
        b = 1 - 1j
        z = np.array([0j])
        for _ in range(steps):
            w = 1j * np.conj(z)
            z = np.concatenate([w - a, z - b, z + a, b - w]) / 2.0
    elif curve == "sierpinski":
        a = 1 + 1j
        b = 1 - 1j
        c = 2 - np.sqrt(2)
        z = np.array([c])
        for _ in range(steps):
            w = 1j * z
            z = np.concatenate([z + b, w + b, a - w, z + a]) / 2.0
        z = np.concatenate([z, 1j * z, -z, -1j * z, z[:1]])
    elif curve == "snowflake":
        a = 0.5 + np.sqrt(-3 + 0j) / 6
        b = 1 - a
        c = 0.5 + np.sqrt(-3 + 0j) / 2
        d = 1 - c
        z = np.array([1 + 0j])
        for _ in range(steps):
            z = np.conj(z)
            z = np.concatenate([a * z, b * z + a])
        z = np.concatenate([np.array([0j]), z, 1 - c * z, 1 - c - d * z])
    elif curve == "dragon":
        a = (1 + 1j) / 2
        b = (1 - 1j) / 2
        c = np.sqrt(0.5 + 0j)
        z = np.array([1 - c, c])
        for _ in range(steps):
            w = z[::-1]
            z = np.concatenate([a * z, 1 - b * w])
    elif curve == "triangle":
        a = (1 + np.sqrt(-3 + 0j)) / 2
        z = np.array([0j, 1 + 0j])
        for _ in range(steps):
            z = np.concatenate([z, z + a, z + 1]) / 2
        z = np.concatenate([z, np.array([a, 0j])])
    elif curve == "arrowhead":
        a = (1 + np.sqrt(-3 + 0j)) / 2
        b = (1 - np.sqrt(-3 + 0j)) / 2
        z = np.array([0j])
        for _ in range(steps):
            w = np.conj(z)
            z = np.concatenate([a * w, z + a, b * w + a + 1]) / 2
        z = np.concatenate([z, np.array([1 + 0j])])
    elif curve == "flowsnake":
        a = (1 + np.sqrt(-3 + 0j)) / 2
        b = (1 - np.sqrt(-3 + 0j)) / 2
        c = np.array([1, a, -b, -1, -a, b])
        u = np.array([0.0])
        for _ in range(steps):
            v = u[::-1]
            u = np.concatenate([u, v + 1, v + 3, u + 2, u, u, v - 1])
        u = np.mod(u, 6)
        z = np.cumsum(c[u.astype(int)])
        z = np.concatenate([np.array([0j]), z / 7 ** (steps / 2)])
    elif curve == "molecule":
        a = (1 + np.sqrt(-3 + 0j)) / 2
        b = (1 - np.sqrt(-3 + 0j)) / 2
        c = np.array([1, a, -b, -1, -a, b])
        u = np.array([0.0])
        for _ in range(steps):
            u = np.concatenate([u + 1, -u, u - 1])
        u = np.concatenate([u, 1 - u, 2 + u, 3 - u, 4 + u, 5 - u])
        u = np.mod(u, 6)
        z = np.cumsum(c[u.astype(int)])
        z = np.concatenate([np.array([0j]), z / 2 ** steps])
    else:
        raise PracmaError("Unknown fractal curve name ...")
    return _real_imag(z)
