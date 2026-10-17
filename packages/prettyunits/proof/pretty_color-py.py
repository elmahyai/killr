"""Proof: prettyunits.color.pretty_color against the R prettyunits 1.2.0 result.

The R case passes factor("red"). Python has no factor, so the same color name
"red" is passed. Both sides return the same name.
"""

from harness import run_proof, try_val

from prettyunits.color import pretty_color

COLORS = [
    "red", "#FF0000", "navy", "gray50", "grey50", "transparent", "#12345678",
    "blue", "darkolivegreen", "chartreuse3", "#ABCDEF", "white", "black",
    "steelblue", "#0000FF80", "NA", "", "nonsense", None,
    "red", 5,
]


def one():
    out = []
    for col in COLORS:
        result = try_val(pretty_color, col)
        if result == "__error__":
            out.append("__error__")
        else:
            out.append({"value": result.name, "alt": result.alt})
    return out


run_proof("pretty_color", one)
