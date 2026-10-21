"""The `*_dfr()` and `*_dfc()` wrappers.

Each one is the ordinary windowed call followed by a bind. The result is a
Polars `DataFrame`, which is what a data frame is here.
"""

from __future__ import annotations

from slider.bind import ZAP, vec_cbind, vec_rbind


def _dfr(out, names_to, name_repair):
    return vec_rbind(out, names_to=ZAP if names_to is None else names_to, name_repair=name_repair)


def slide_dfr(x, f, *args, before=0, after=0, step=1, complete=False,
              names_to=ZAP, name_repair="unique"):
    from slider import slide

    out = slide(x, f, *args, before=before, after=after, step=step, complete=complete)
    return _dfr(out, names_to, name_repair)


def slide_dfc(x, f, *args, before=0, after=0, step=1, complete=False,
              size=None, name_repair="unique"):
    from slider import slide

    out = slide(x, f, *args, before=before, after=after, step=step, complete=complete)
    return vec_cbind(out, size=size, name_repair=name_repair)


def slide2_dfr(x, y, f, *args, before=0, after=0, step=1, complete=False,
               names_to=ZAP, name_repair="unique"):
    from slider import slide2

    out = slide2(x, y, f, *args, before=before, after=after, step=step, complete=complete)
    return _dfr(out, names_to, name_repair)


def slide2_dfc(x, y, f, *args, before=0, after=0, step=1, complete=False,
               size=None, name_repair="unique"):
    from slider import slide2

    out = slide2(x, y, f, *args, before=before, after=after, step=step, complete=complete)
    return vec_cbind(out, size=size, name_repair=name_repair)


def pslide_dfr(items, f, *args, before=0, after=0, step=1, complete=False,
               names_to=ZAP, name_repair="unique"):
    from slider import pslide

    out = pslide(items, f, *args, before=before, after=after, step=step, complete=complete)
    return _dfr(out, names_to, name_repair)


def pslide_dfc(items, f, *args, before=0, after=0, step=1, complete=False,
               size=None, name_repair="unique"):
    from slider import pslide

    out = pslide(items, f, *args, before=before, after=after, step=step, complete=complete)
    return vec_cbind(out, size=size, name_repair=name_repair)


def slide_index_dfr(x, i, f, *args, before=0, after=0, complete=False,
                    names_to=ZAP, name_repair="unique"):
    from slider import slide_index

    out = slide_index(x, i, f, *args, before=before, after=after, complete=complete)
    return _dfr(out, names_to, name_repair)


def slide_index_dfc(x, i, f, *args, before=0, after=0, complete=False,
                    size=None, name_repair="unique"):
    from slider import slide_index

    out = slide_index(x, i, f, *args, before=before, after=after, complete=complete)
    return vec_cbind(out, size=size, name_repair=name_repair)


def slide_index2_dfr(x, y, i, f, *args, before=0, after=0, complete=False,
                     names_to=ZAP, name_repair="unique"):
    from slider import slide_index2

    out = slide_index2(x, y, i, f, *args, before=before, after=after, complete=complete)
    return _dfr(out, names_to, name_repair)


def slide_index2_dfc(x, y, i, f, *args, before=0, after=0, complete=False,
                     size=None, name_repair="unique"):
    from slider import slide_index2

    out = slide_index2(x, y, i, f, *args, before=before, after=after, complete=complete)
    return vec_cbind(out, size=size, name_repair=name_repair)


def pslide_index_dfr(items, i, f, *args, before=0, after=0, complete=False,
                     names_to=ZAP, name_repair="unique"):
    from slider import pslide_index

    out = pslide_index(items, i, f, *args, before=before, after=after, complete=complete)
    return _dfr(out, names_to, name_repair)


def pslide_index_dfc(items, i, f, *args, before=0, after=0, complete=False,
                     size=None, name_repair="unique"):
    from slider import pslide_index

    out = pslide_index(items, i, f, *args, before=before, after=after, complete=complete)
    return vec_cbind(out, size=size, name_repair=name_repair)


def slide_period_dfr(x, i, period, f, *args, every=1, origin=None, before=0, after=0,
                     complete=False, names_to=ZAP, name_repair="unique"):
    from slider.slide_period import slide_period

    out = slide_period(x, i, period, f, *args, every=every, origin=origin,
                       before=before, after=after, complete=complete)
    return _dfr(out, names_to, name_repair)


def slide_period_dfc(x, i, period, f, *args, every=1, origin=None, before=0, after=0,
                     complete=False, size=None, name_repair="unique"):
    from slider.slide_period import slide_period

    out = slide_period(x, i, period, f, *args, every=every, origin=origin,
                       before=before, after=after, complete=complete)
    return vec_cbind(out, size=size, name_repair=name_repair)


def slide_period2_dfr(x, y, i, period, f, *args, every=1, origin=None, before=0, after=0,
                      complete=False, names_to=ZAP, name_repair="unique"):
    from slider.slide_period2 import slide_period2

    out = slide_period2(x, y, i, period, f, *args, every=every, origin=origin,
                        before=before, after=after, complete=complete)
    return _dfr(out, names_to, name_repair)


def slide_period2_dfc(x, y, i, period, f, *args, every=1, origin=None, before=0, after=0,
                      complete=False, size=None, name_repair="unique"):
    from slider.slide_period2 import slide_period2

    out = slide_period2(x, y, i, period, f, *args, every=every, origin=origin,
                        before=before, after=after, complete=complete)
    return vec_cbind(out, size=size, name_repair=name_repair)


def pslide_period_dfr(items, i, period, f, *args, every=1, origin=None, before=0, after=0,
                      complete=False, names_to=ZAP, name_repair="unique"):
    from slider.pslide_period import pslide_period

    out = pslide_period(items, i, period, f, *args, every=every, origin=origin,
                        before=before, after=after, complete=complete)
    return _dfr(out, names_to, name_repair)


def pslide_period_dfc(items, i, period, f, *args, every=1, origin=None, before=0, after=0,
                      complete=False, size=None, name_repair="unique"):
    from slider.pslide_period import pslide_period

    out = pslide_period(items, i, period, f, *args, every=every, origin=origin,
                        before=before, after=after, complete=complete)
    return vec_cbind(out, size=size, name_repair=name_repair)
