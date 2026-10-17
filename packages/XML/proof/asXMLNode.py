from XML.asXMLNode import asXMLNode, xmlNode, _xml_name

txt = '<doc id="1"><item class="a">hello</item><item class="b">world<note>!</note></item></doc>'
ns = '<doc xmlns:a="urn:ex"><a:item>z</a:item></doc>'
html = '<html><head><title>Hi</title></head><body><a href="x">go</a></body></html>'


def one():
    text = asXMLNode("a text node")
    element = xmlNode("p")
    return ",".join(
        [
            text.classes[0],
            text.value,
            _xml_name(asXMLNode(element)),
            "TRUE" if asXMLNode(element) is element else "FALSE",
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
