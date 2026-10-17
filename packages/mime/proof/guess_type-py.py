import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from mime.api import guess_type
x = dict(basic=guess_type(['a/b/c.html','d.pdf','e.odt','foo.docx','tex']),
         extra=guess_type(['a.md','b.R']),
         override=guess_type('tex', mime_extra={'tex':'text/plain'}),
         unknown=guess_type('foo.zzz'), empty=guess_type('Makefile'),
         subtype=guess_type(['abc.html','def.htm'], subtype=['charset=UTF-8','']))
print(x)
