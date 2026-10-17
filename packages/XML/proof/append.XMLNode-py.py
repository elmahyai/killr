from XML import newXMLDoc, newXMLNode, saveXML
from XML.append_XMLNode import append_XMLNode

txt = '<doc id="1"><item class="a">hello</item><item class="b">world<note>!</note></item></doc>'
ns = '<doc xmlns:a="urn:ex"><a:item>z</a:item></doc>'
html = '<html><head><title>Hi</title></head><body><a href="x">go</a></body></html>'


def one():
    doc = newXMLDoc()
    n = newXMLNode("data", attrs={"numVars": "2", "numRecords": "3"}, doc=doc)
    append_XMLNode(
        n,
        newXMLNode(
            "varNames",
            newXMLNode("string", "A", doc=doc),
            newXMLNode("string", "B", doc=doc),
            doc=doc,
        ),
    )
    append_XMLNode(n, newXMLNode("record", "1.2 3.5", doc=doc))
    return saveXML(doc)


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
