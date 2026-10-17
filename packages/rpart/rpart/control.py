"""Control list for an rpart tree."""

from __future__ import annotations


def rpart_control(
    minsplit=None,
    minbucket=None,
    cp=0.01,
    maxcompete=4,
    maxsurrogate=5,
    usesurrogate=2,
    xval=10,
    surrogatestyle=0,
    maxdepth=30,
):
    """The nine control numbers, with xval last, as rpart.control stores them."""
    maxcompete = int(maxcompete)
    maxsurrogate = int(maxsurrogate)
    usesurrogate = int(usesurrogate)
    surrogatestyle = int(surrogatestyle)
    maxdepth = int(maxdepth)
    xval = int(xval)
    if maxcompete < 0:
        maxcompete = 0
    if xval < 0:
        xval = 0
    if maxdepth > 30:
        raise ValueError("Maximum depth is 30")
    if maxdepth < 1:
        raise ValueError("Maximum depth must be at least 1")
    if minsplit is None and minbucket is not None:
        minsplit = int(round(minbucket)) * 3
    if minsplit is None:
        minsplit = 20
    minsplit = int(minsplit)
    if minbucket is None:
        minbucket = int(round(minsplit / 3))
    else:
        minbucket = int(round(minbucket))
    if usesurrogate < 0 or usesurrogate > 2:
        usesurrogate = 2
    if surrogatestyle < 0 or surrogatestyle > 1:
        surrogatestyle = 0
    return {
        "minsplit": minsplit,
        "minbucket": minbucket,
        "cp": float(cp),
        "maxcompete": maxcompete,
        "maxsurrogate": maxsurrogate,
        "usesurrogate": usesurrogate,
        "surrogatestyle": surrogatestyle,
        "maxdepth": maxdepth,
        "xval": xval,
    }
