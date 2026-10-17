library(mime)
x <- list(
  basic=guess_type(c('a/b/c.html','d.pdf','e.odt','foo.docx','tex')),
  extra=guess_type(c('a.md','b.R')),
  override=guess_type('tex', mime_extra=c(tex='text/plain')),
  unknown=guess_type('foo.zzz'),
  empty=guess_type('Makefile'),
  subtype=guess_type(c('abc.html','def.htm'), subtype=c('charset=UTF-8',''))
)
print(x)
