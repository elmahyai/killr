from XML.Doctype import Doctype, as_character

txt = '<doc id="1"><item class="a">hello</item><item class="b">world<note>!</note></item></doc>'
ns = '<doc xmlns:a="urn:ex"><a:item>z</a:item></doc>'
html = '<html><head><title>Hi</title></head><body><a href="x">go</a></body></html>'


def one():
    d1 = Doctype(
        name="section",
        public=[
            "-//OASIS//DTD DocBook XML V4.2//EN",
            "http://oasis-open.org/docbook/xml/4.2/docbookx.dtd",
        ],
    )
    d2 = Doctype(
        name="section",
        public=["-//OASIS//DTD DocBook XML V4.2//EN"],
        system="http://oasis-open.org/docbook/xml/4.2/docbookx.dtd",
    )
    return "|".join(as_character(d) for d in (d1, d2))


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
