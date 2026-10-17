from XML.comment_SAX import SAXState
from XML.endElement_SAX import endElement_SAX, setMethod_endElement_SAX

txt = '<doc id="1"><item class="a">hello</item><item class="b">world<note>!</note></item></doc>'
ns = '<doc xmlns:a="urn:ex"><a:item>z</a:item></doc>'
html = '<html><head><title>Hi</title></head><body><a href="x">go</a></body></html>'


class T2(SAXState):
    pass


class MySAXState(SAXState):
    __slots__ = ("closed",)

    def __init__(self) -> None:
        super().__init__()
        self.closed: list[str] = []


def _my_end_element(name: str, _state: MySAXState) -> MySAXState:
    updated = MySAXState()
    updated.closed = _state.closed + [name]
    return updated


setMethod_endElement_SAX(MySAXState, _my_end_element)


def one():
    st = T2()
    my = MySAXState()
    return ",".join(
        [
            "TRUE" if endElement_SAX("item", st) is st else "FALSE",
            type(endElement_SAX("item", st)).__name__,
            ":".join(endElement_SAX("item", my).closed),
            ":".join(endElement_SAX("doc", endElement_SAX("item", my)).closed),
        ]
    )


import statistics
import time

value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("VALUE " + str(value).replace("\n", " / "))
print(f"MS {statistics.median(elapsed):.17g}")
