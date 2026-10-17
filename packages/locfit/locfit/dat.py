"""The locfit ``dat`` evaluation specification."""

def dat(cv: bool = False) -> dict:
    return {
        "type": "crossval" if cv else "data",
        "xev": 0.0,
        "mg": 0,
        "cut": 0.0,
        "ll": 0.0,
        "ur": 0.0,
        "class": "lf_evs",
    }

