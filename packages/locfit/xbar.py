"""Mean/centroid evaluation specification."""


def xbar():
    """Return the locfit ``xbar`` evaluation specification."""
    return {"type": "xbar", "xev": 0, "mg": 0, "cut": 0, "ll": 0, "ur": 0}
