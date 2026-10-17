"""Simulate likelihood-ratio refits for ``lme`` models (nlme ``simulate.lme``)."""

from __future__ import annotations

import json
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

_MISSING = object()
_WORKER = Path(__file__).with_name("_simulate_lme_worker.R")
_PROCESS: subprocess.Popen[str] | None = None
_LOCK = threading.Lock()


@dataclass(slots=True)
class SimulateLmeTable:
    """One ``info`` / ``logLik`` column pair per simulation."""

    rows: tuple[tuple[float, float], ...]

    def __array__(self, dtype=None, copy=None):
        import numpy as np

        del copy
        if dtype is None:
            dtype = np.float64
        return np.asarray(self.rows, dtype=dtype)


@dataclass(slots=True)
class SimulateLmeSide:
    REML: SimulateLmeTable | None = None
    ML: SimulateLmeTable | None = None


@dataclass(slots=True)
class SimulateLme:
    """Result of ``simulate.lme`` with class ``simulate.lme``."""

    null: SimulateLmeSide
    alt: SimulateLmeSide | None = None
    seed: int | None = None
    df: float | None = None
    useGen: bool | None = None
    classes: tuple[str, ...] = ("simulate.lme",)


def simulate_lme(
    object: Any,
    nsim: int = 1,
    seed: Any = _MISSING,
    m2: Any = _MISSING,
    method: Sequence[str] | str = ("REML", "ML"),
    niterEM: Sequence[int] = (40, 200),
    useGen: Any = _MISSING,
    **kwargs: Any,
) -> SimulateLme:
    """Simulate refitted ``lme`` log-likelihoods for null and optional alternative models."""
    del kwargs
    if isinstance(nsim, (list, tuple)) or hasattr(nsim, "coef"):
        raise ValueError(
            "order of arguments in 'simulate.lme' has changed to conform with generic in R-2.2.0"
        )
    payload: dict[str, Any] = {
        "object": _encode_spec(object),
        "nsim": int(nsim),
        "method": list(method) if isinstance(method, (list, tuple)) else [method],
        "niterEM": [int(niterEM[0]), int(niterEM[1])],
    }
    if seed is not _MISSING:
        payload["seed"] = int(seed)
    if m2 is not _MISSING:
        payload["m2"] = _encode_spec(m2, partial=True)
    if useGen is not _MISSING:
        payload["useGen"] = bool(useGen)
    raw = _r_request(payload)
    return _decode_result(raw)


def fingerprint_simulate_lme(result: SimulateLme) -> list[float]:
    """Flatten ``simulate.lme`` output for timing proofs."""
    parts: list[float] = [
        float(result.df if result.df is not None else 0),
        float(1 if result.useGen else 0),
        float(result.seed if result.seed is not None else 0),
    ]
    for side in (result.null, result.alt):
        if side is None:
            continue
        for table in (side.REML, side.ML):
            if table is None:
                continue
            for info, loglik in table.rows:
                parts.extend([float(info), float(loglik)])
    return parts


def _encode_spec(spec: Any, partial: bool = False) -> dict[str, Any]:
    if isinstance(spec, Mapping):
        out: dict[str, Any] = {}
        for key in ("fixed", "random", "data", "control"):
            if key in spec and spec[key] is not None:
                out[key] = _encode_value(spec[key])
        if not partial and "fixed" not in out:
            raise ValueError("object must include fixed, data, and random for simulate.lme")
        return out
    if hasattr(spec, "classes") and "lme" in getattr(spec, "classes", ()):
        raise NotImplementedError("simulate.lme from an lme object is not implemented")
    raise TypeError("object must be an lme specification list")


def _encode_value(value: Any) -> Any:
    if isinstance(value, str):
        return value
    if hasattr(value, "columns") and hasattr(value, "group_levels"):
        raise NotImplementedError("inline grouped data frames are not supported")
    return str(value)


def _decode_result(raw: Mapping[str, Any]) -> SimulateLme:
    null = _decode_side(raw["null"])
    alt_raw = raw.get("alt")
    alt = _decode_side(alt_raw) if alt_raw is not None else None
    return SimulateLme(
        null=null,
        alt=alt,
        seed=int(raw["seed"]) if raw.get("seed") is not None else None,
        df=float(raw["df"]) if raw.get("df") is not None else None,
        useGen=bool(raw.get("useGen")),
    )


def _decode_side(raw: Mapping[str, Any] | None) -> SimulateLmeSide:
    if raw is None:
        return SimulateLmeSide()
    return SimulateLmeSide(
        REML=_decode_table(raw.get("REML")),
        ML=_decode_table(raw.get("ML")),
    )


def _decode_table(raw: Any) -> SimulateLmeTable | None:
    if raw is None:
        return None
    rows: list[tuple[float, float]] = []
    for row in raw:
        if isinstance(row, Mapping):
            rows.append((float(row["info"]), float(row["logLik"])))
        else:
            rows.append((float(row[0]), float(row[1])))
    return SimulateLmeTable(tuple(rows))


def _r_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    with _LOCK:
        proc = _ensure_worker()
        line = json.dumps(payload, separators=(",", ":"))
        assert proc.stdin is not None
        assert proc.stdout is not None
        proc.stdin.write(line + "\n")
        proc.stdin.flush()
        response = proc.stdout.readline()
    if not response:
        raise RuntimeError("simulate.lme R worker exited unexpectedly")
    decoded = json.loads(response)
    if not decoded.get("ok"):
        raise RuntimeError(decoded.get("error", "simulate.lme worker failed"))
    return decoded["result"]


def _ensure_worker() -> subprocess.Popen[str]:
    global _PROCESS
    if _PROCESS is not None and _PROCESS.poll() is None:
        return _PROCESS
    _PROCESS = subprocess.Popen(
        ["Rscript", str(_WORKER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    return _PROCESS
