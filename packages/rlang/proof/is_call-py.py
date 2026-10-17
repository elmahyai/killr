import statistics
import time

from rlang.as_label import Call, Symbol
from rlang.is_call import is_call

_colon2 = Symbol("::")
_at = Symbol("@")
_colon3 = Symbol(":::")


def _q(*parts):
    return Call(*parts)


def one():
    foo_bar = _q(Symbol("foo"), Symbol("bar"))
    plus3 = _q(Symbol("+"), 3)
    three_plus = _q(Symbol("+"), 3, 3)
    foo_ns_bar_call = _q(_q(_colon2, Symbol("foo"), Symbol("bar")))
    foo_ns_quux_call = _q(_q(_colon2, Symbol("foo"), Symbol("quux")))
    bar_ns_quux_call = _q(_q(_colon2, Symbol("bar"), Symbol("quux")))
    baz_ns_quux_call = _q(_q(_colon2, Symbol("baz"), Symbol("quux")))
    foo_call = _q(Symbol("foo"))
    foo_ns_bar_sym = _q(_colon2, Symbol("foo"), Symbol("bar"))
    quux_call = _q(Symbol("quux"))
    base_ns_list = _q(_q(_colon2, Symbol("base"), Symbol("list")))
    list_call = _q(Symbol("list"))

    return ",".join(
        "TRUE" if item else "FALSE"
        for item in (
            is_call(foo_bar, "foo"),
            is_call(foo_bar, "bar"),
            is_call(foo_bar, Symbol("foo")),
            is_call(foo_bar, "foo", n=1),
            is_call(foo_bar, "foo", n=2),
            is_call(plus3, n=1),
            is_call(three_plus, n=2),
            is_call(1),
            is_call(None),
            is_call(foo_call, Symbol("foo")),
            is_call(foo_call, Symbol("bar")),
            is_call(foo_ns_bar_sym, ("fn", "fn2")),
            is_call(foo_ns_bar_sym, ("fn", "::")),
            is_call(foo_ns_bar_sym, _colon2),
            is_call(foo_ns_bar_sym, (_at, _colon2)),
            is_call(foo_ns_bar_sym, (_at, _colon3)),
            is_call(foo_ns_bar_call, ns=None),
            is_call(foo_ns_bar_call, ns=""),
            is_call(foo_ns_bar_call, ns="baz"),
            is_call(foo_ns_bar_call, ns="foo"),
            is_call(foo_ns_bar_call, name="bar", ns="foo"),
            is_call(foo_ns_bar_call, name="baz", ns="foo"),
            is_call(foo_ns_quux_call, ns=("foo", "bar")),
            is_call(bar_ns_quux_call, ns=("foo", "bar")),
            is_call(baz_ns_quux_call, ns=("foo", "bar")),
            is_call(quux_call, ns=("foo", "bar")),
            is_call(baz_ns_quux_call, ns=("foo", "bar", "")),
            is_call(quux_call, ns=("foo", "bar", "")),
            is_call(base_ns_list, "list"),
            is_call(base_ns_list, "list", ns=""),
            is_call(base_ns_list, "list", ns="utils"),
            is_call(base_ns_list, "list", ns="base"),
            is_call(base_ns_list, "list", ns=("utils", "base")),
            is_call(list_call, "list", ns="base"),
            is_call(list_call, "list", ns=("base", "")),
            is_call(base_ns_list, "list", ns=("base", "")),
        )
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
shown = str(value).replace("\n", " / ")
print("VALUE " + shown)
print(f"MS {statistics.median(elapsed):.17g}")
