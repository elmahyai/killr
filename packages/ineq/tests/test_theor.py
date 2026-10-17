"""Checks for the theoretical Lorenz curves, including a comparison with R."""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
import textwrap
import warnings
from pathlib import Path

import numpy as np
import pytest

from ineq.theor import (
    _pbeta_scalar,
    _pnorm_scalar,
    _qnorm_scalar,
    lc_dagum,
    lc_exp,
    lc_lognorm,
    lc_pareto,
    lc_singh,
    theorLc,
)

TOLERANCE = 1e-8


def test_exp_keeps_the_r_endpoint_and_the_input_shape():
    assert lc_exp(0.0).shape == ()
    assert lc_exp(0.0) == pytest.approx(0.0)
    assert math.isnan(float(lc_exp(1.0)))

    grid = np.array([[0.0, 0.25], [0.75, 1.0]])
    ordinate = lc_exp(grid)
    assert ordinate.shape == grid.shape
    assert ordinate[0, 0] == pytest.approx(0.0)
    assert math.isnan(float(ordinate[1, 1]))
    assert isinstance(lc_exp([0.2, 0.4]), np.ndarray)


def test_lognorm_keeps_endpoints_and_shifts_the_interior():
    grid = np.array([[0.0, 0.25], [0.5, 1.0]])
    ordinate = lc_lognorm(grid, parameter=0.78)
    assert ordinate.shape == grid.shape
    assert ordinate[0, 0] == 0.0
    assert ordinate[1, 1] == 1.0
    interior = _pnorm_scalar(_qnorm_scalar(0.25) - 0.78)
    assert ordinate[0, 1] == pytest.approx(interior, abs=TOLERANCE)


def test_pbeta_matches_closed_forms():
    share = np.linspace(0.0, 1.0, 21)
    uniform = np.array([_pbeta_scalar(float(x), 1.0, 1.0) for x in share])
    assert uniform == pytest.approx(share, abs=TOLERANCE)
    pareto_like = np.array([_pbeta_scalar(float(x), 1.0, 0.5) for x in share])
    assert pareto_like == pytest.approx(1.0 - np.sqrt(1.0 - share), abs=TOLERANCE)
    root = np.array([_pbeta_scalar(float(x), 0.5, 1.0) for x in share])
    assert root == pytest.approx(np.sqrt(share), abs=TOLERANCE)


def test_inadmissible_parameters_warn_and_use_the_r_defaults():
    share = np.linspace(0.0, 1.0, 21)
    with pytest.warns(UserWarning, match=r"default parameter=1"):
        lognorm = lc_lognorm(share, parameter=0)
    assert lognorm == pytest.approx(lc_lognorm(share, parameter=1), abs=TOLERANCE)

    with pytest.warns(UserWarning, match=r"default parameter=1"):
        negative = lc_lognorm(share, parameter=-2)
    assert negative == pytest.approx(lognorm, abs=TOLERANCE)

    with pytest.warns(UserWarning, match=r"default parameter=2 is used"):
        pareto = lc_pareto(share, parameter=1)
    assert pareto == pytest.approx(lc_pareto(share, parameter=2), abs=TOLERANCE)

    with pytest.warns(UserWarning, match=r"default parameter=c\(2,2\)"):
        singh = lc_singh(share, parameter=0)
    assert singh == pytest.approx(lc_singh(share), abs=TOLERANCE)

    with pytest.warns(UserWarning, match=r"default parameter=c\(2,2\)"):
        on_the_boundary = lc_singh(share, parameter=(4, 2))
    assert on_the_boundary == pytest.approx(lc_singh(share), abs=TOLERANCE)

    with pytest.warns(UserWarning, match=r"default parameter=c\(2,2\)"):
        dagum = lc_dagum(share, parameter=1)
    assert dagum == pytest.approx(lc_dagum(share), abs=TOLERANCE)


def test_theorlc_prefixes_and_the_exponential_branch():
    share = np.linspace(0.0, 1.0, 11)
    dagum = theorLc("D", parameter=(3.4, 2.6))
    assert dagum(share) == pytest.approx(lc_dagum(share, parameter=(3.4, 2.6)), abs=TOLERANCE)
    assert theorLc("log", parameter=0.78)(share) == pytest.approx(
        lc_lognorm(share, parameter=0.78), abs=TOLERANCE
    )
    assert theorLc("Pa", parameter=1.5)(share) == pytest.approx(
        lc_pareto(share, parameter=1.5), abs=TOLERANCE
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        assert theorLc("Singh", parameter=0)(share) == pytest.approx(lc_singh(share), abs=TOLERANCE)

    exponential = theorLc("e", parameter=99)
    assert np.allclose(exponential(share), lc_exp(share), equal_nan=True)

    with pytest.warns(UserWarning, match=r"default parameter=c\(2,2\)"):
        fallback = theorLc()(share)
    assert fallback == pytest.approx(lc_singh(share), abs=TOLERANCE)

    for bad in ("dagum", "singh", "", "E", "p", "Log"):
        with pytest.raises(ValueError):
            theorLc(bad)
    with pytest.raises(ValueError):
        theorLc(1)


def test_curves_and_specials_match_installed_ineq():
    reference = _r_reference()
    if reference is None:
        pytest.skip("Rscript or ineq is unavailable")

    share = reference["p"]
    assert lc_exp(share) == pytest.approx(reference["exp"], abs=TOLERANCE, nan_ok=True)
    assert lc_lognorm(share) == pytest.approx(reference["lognorm"], abs=TOLERANCE)
    assert lc_lognorm(share, parameter=0.78) == pytest.approx(reference["lognorm078"], abs=TOLERANCE)
    assert lc_pareto(share) == pytest.approx(reference["pareto"], abs=TOLERANCE)
    assert lc_singh(share) == pytest.approx(reference["singh"], abs=TOLERANCE)
    assert lc_dagum(share) == pytest.approx(reference["dagum"], abs=TOLERANCE)
    assert lc_dagum(share, parameter=(3.4, 2.6)) == pytest.approx(
        reference["dagum_manual"], abs=TOLERANCE
    )
    assert lc_singh(share, parameter=(3, 2)) == pytest.approx(reference["singh32"], abs=TOLERANCE)

    curve = theorLc(type="Dagum", parameter=(3.4, 2.6))
    assert curve(share) == pytest.approx(reference["theor_dagum"], abs=TOLERANCE)
    assert np.allclose(theorLc("exp")(share), reference["theor_exp"], equal_nan=True)

    python_pnorm = np.array([_pnorm_scalar(float(z)) for z in reference["z"]])
    assert python_pnorm == pytest.approx(reference["pnorm"], abs=TOLERANCE)
    python_qnorm = np.array([_qnorm_scalar(float(p)) for p in reference["probs"]])
    assert python_qnorm == pytest.approx(reference["qnorm"], abs=TOLERANCE)

    beta_x = reference["beta_x"]
    beta_cases = {
        "singh_beta": (beta_x, 4.0 / 3.0, 2.0 / 3.0),
        "dagum_beta": (np.power(beta_x, 2.0), 1.0, 0.5),
        "manual_beta": (np.power(beta_x, 2.6), 1.0 / 3.4 + 1.0 / 2.6, 1.0 - 1.0 / 3.4),
    }
    for name, (abscissa, a, b) in beta_cases.items():
        python_beta = np.array([_pbeta_scalar(float(x), a, b) for x in abscissa])
        assert python_beta == pytest.approx(reference[name], abs=TOLERANCE)


def _r_reference():
    if shutil.which("Rscript") is None:
        return None
    share = np.linspace(0.0, 1.0, 21)
    normal = np.linspace(-8.0, 8.0, 33)
    probs = np.array(
        [1e-10, 1e-6, 1e-3, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1 - 1e-6, 1 - 1e-10],
        dtype=np.float64,
    )
    beta_x = np.linspace(0.0, 1.0, 21)
    script = textwrap.dedent(
        """
        args <- commandArgs(trailingOnly=TRUE)
        if (!requireNamespace("ineq", quietly=TRUE)) quit(status=2)
        p <- scan(file.path(args[[1]], "p.txt"), quiet=TRUE)
        z <- scan(file.path(args[[1]], "z.txt"), quiet=TRUE)
        probs <- scan(file.path(args[[1]], "probs.txt"), quiet=TRUE)
        beta_x <- scan(file.path(args[[1]], "beta.txt"), quiet=TRUE)
        emit <- function(name, v) {
          cat("## ", name, "\\n", sep="")
          cat(sprintf("%.17g\\n", v), sep="")
        }
        emit("exp", ineq::Lc.exp(p))
        emit("lognorm", ineq::Lc.lognorm(p))
        emit("lognorm078", ineq::Lc.lognorm(p, parameter=0.78))
        emit("pareto", ineq::Lc.pareto(p))
        emit("singh", ineq::Lc.singh(p))
        emit("singh32", ineq::Lc.singh(p, parameter=c(3, 2)))
        emit("dagum", ineq::Lc.dagum(p))
        emit("dagum_manual", ineq::Lc.dagum(p, parameter=c(3.4, 2.6)))
        emit("theor_dagum", ineq::theorLc("Dagum", parameter=c(3.4, 2.6))(p))
        emit("theor_exp", ineq::theorLc("exp")(p))
        emit("pnorm", pnorm(z))
        emit("qnorm", qnorm(probs))
        emit("singh_beta", pbeta(beta_x, 4/3, 2/3))
        emit("dagum_beta", pbeta(beta_x^2, 1, 0.5))
        a <- 1/3.4
        b <- 2.6
        emit("manual_beta", pbeta(beta_x^b, a + 1/b, 1 - a))
        """
    )
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        np.savetxt(root / "p.txt", share, fmt="%.17g")
        np.savetxt(root / "z.txt", normal, fmt="%.17g")
        np.savetxt(root / "probs.txt", probs, fmt="%.17g")
        np.savetxt(root / "beta.txt", beta_x, fmt="%.17g")
        program = root / "check.R"
        program.write_text(script)
        result = subprocess.run(
            ["Rscript", str(program), str(root)],
            check=False,
            capture_output=True,
            text=True,
        )
    if result.returncode == 2:
        return None
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    parsed = _parse_blocks(result.stdout)
    parsed["p"] = share
    parsed["z"] = normal
    parsed["probs"] = probs
    parsed["beta_x"] = beta_x
    return parsed


def _parse_blocks(text):
    blocks = {}
    name = None
    rows = []
    for line in text.splitlines():
        if line.startswith("## "):
            if name is not None:
                blocks[name] = _floats(rows)
            name = line[3:]
            rows = []
        elif line.strip():
            rows.append(line.strip())
    if name is not None:
        blocks[name] = _floats(rows)
    return blocks


def _floats(rows):
    values = []
    for token in rows:
        if token in {"NaN", "NA", "nan"}:
            values.append(np.nan)
        else:
            values.append(float(token))
    return np.asarray(values, dtype=np.float64)
