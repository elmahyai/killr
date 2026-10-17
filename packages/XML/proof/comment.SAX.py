from XML.comment_SAX import SAXState, comment_SAX, setMethod_comment_SAX

txt = '<doc id="1"><item class="a">hello</item><item class="b">world<note>!</note></item></doc>'
ns = '<doc xmlns:a="urn:ex"><a:item>z</a:item></doc>'
html = '<html><head><title>Hi</title></head><body><a href="x">go</a></body></html>'


class T2(SAXState):
    pass


class MySAXState(SAXState):
    __slots__ = ("comments",)

    def __init__(self) -> None:
        super().__init__()
        self.comments: list[str] = []


def _my_comment(content: str, _state: MySAXState) -> MySAXState:
    updated = MySAXState()
    updated.comments = _state.comments + [content]
    return updated


setMethod_comment_SAX(MySAXState, _my_comment)

def one():
    st = T2()
    my = MySAXState()
    return ",".join(
        [
            "TRUE" if comment_SAX("x", st) is st else "FALSE",
            type(comment_SAX("x", st)).__name__,
            ":".join(comment_SAX("first", my).comments),
            ":".join(comment_SAX("second", comment_SAX("first", my)).comments),
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
