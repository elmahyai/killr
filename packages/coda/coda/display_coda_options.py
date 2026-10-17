"""Print current coda menu option settings."""

from __future__ import annotations

import inspect
import sys

from coda.coda_options import coda_options


def display_coda_options(stats=False, plots=False, diags=False):
    """Mirror ``display.coda.options`` from coda 0.19-4.1."""
    out = sys.stdout
    out.write("\nCurrent option settings:")
    out.write("\n=======================\n\n")
    if stats:
        out.write("SUMMARY STATISTICS OPTIONS\n")
        out.write("==========================\n\n")
        out.write(f"Combine chains     : {_r_bool(coda_options('combine.stats'))}\n")
        quantiles = coda_options("quantiles")
        qtext = ", ".join(_format_quantile(q) for q in quantiles)
        out.write(f"Quantiles          : {qtext}\n")
        out.write(f"Significant digits : {coda_options('digits')}\n\n")
    if plots:
        out.write("PLOTTING OPTIONS\n")
        out.write("================\n\n")
        out.write(f"Trace               : {_r_bool(coda_options('trace'))}\n")
        out.write(f"Density             : {_r_bool(coda_options('densplot'))}\n")
        out.write(f"Smooth lines        : {_r_bool(coda_options('lowess'))}\n")
        out.write(f"Combine chains      : {_r_bool(coda_options('combine.plots'))}\n")
        out.write(f"User-defined layout : {_r_bool(coda_options('user.layout'))}\n")
        if coda_options("user.layout"):
            # R would print par("mfrow"); non-interactive proof keeps user.layout FALSE.
            out.write("                    : 1 X 1\n")
        out.write("Bandwidth function  :\n")
        bandwidth = coda_options("bandwidth")
        if callable(bandwidth):
            out.write(_format_bandwidth(bandwidth))
        else:
            out.write(f"{bandwidth}\n")
        out.write("\n")
    if diags:
        out.write("DIAGNOSTICS OPTIONS\n")
        out.write("===================\n\n")
        out.write("Geweke\n")
        out.write("------\n")
        out.write(f"Window 1 fraction  : {coda_options('frac1')}\n")
        out.write(f"Window 2 fraction  : {coda_options('frac2')}\n")
        out.write(f"Number of bins     : {coda_options('geweke.nbin')}\n\n")
        out.write("Gelman & Rubin\n")
        out.write("--------------\n")
        out.write(f"Bin width          : {coda_options('gr.bin')}\n")
        out.write(f"Max number of bins : {coda_options('gr.max')}\n\n")
        out.write("Raftery & Lewis\n")
        out.write("---------------\n")
        out.write(f"Quantile (q)       : {coda_options('q')}\n")
        out.write(f"Precision (+/- r)  : {coda_options('r')}\n")
        out.write(f"Probability (s)    : {coda_options('s')}\n\n")
        out.write("Cross-correlations\n")
        out.write("------------------\n")
        out.write(f"Combine chains     : {_r_bool(coda_options('combine.corr'))}\n\n")
    return None


def _r_bool(value):
    return "TRUE" if bool(value) else "FALSE"


def _format_quantile(q):
    pct = 100 * float(q)
    if abs(pct - round(pct)) < 1e-12:
        return f"{int(round(pct))}%"
    return f"{pct}%"


def _format_bandwidth(func):
    """Approximate R ``print(function)`` for the default bandwidth closure."""
    try:
        source = inspect.getsource(func).strip()
    except (OSError, TypeError):
        source = repr(func)
    lines = source.splitlines()
    if lines and lines[0].startswith("def "):
        lines[0] = "function (x) "
    return "\n".join(lines) + "\n"
