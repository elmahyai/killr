from XML import xmlParse, xmlRoot, xmlElementsByTagName, xmlValue
txt = '<doc id="1"><item class="a">hello</item><item class="b">world<note>!</note></item></doc>'
ns = '<doc xmlns:a="urn:ex"><a:item>z</a:item></doc>'
html = '<html><head><title>Hi</title></head><body><a href="x">go</a></body></html>'

def one():
    r = xmlRoot(xmlParse(txt, as_text=True))
    items = [xmlValue(n) for n in xmlElementsByTagName(r, "item")]
    note = [xmlValue(n) for n in xmlElementsByTagName(r, "note", recursive=True)]
    return ",".join(items + note)

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
