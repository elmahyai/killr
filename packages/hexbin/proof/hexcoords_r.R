# R reference for hexcoords(). Run from the repository root:
#   Rscript packages/hexbin/proof/hexcoords_r.R
source("packages/hexbin/proof/_proof_common.R")

a <- hexcoords(dx = 0.5, n = 3)
put_num("case1.x", a$x)
put_num("case1.y", a$y)
put_num("case1.no_sep", as.numeric(a$no.sep))

b <- hexcoords(dx = 0.3, dy = 0.2, n = 2, sep = NA)
put_num("case2.x", b$x)
put_num("case2.y", b$y)
put_num("case2.no_sep", as.numeric(b$no.sep))

c2 <- hexcoords(dx = 1, n = 1, sep = 0)
put_num("case3.x", c2$x)
put_num("case3.y", c2$y)
put_num("case3.no_sep", as.numeric(c2$no.sep))

d <- hexcoords(dx = 2.5)   # dy defaults to dx / sqrt(3), n = 1
put_num("case4.x", d$x)
put_num("case4.y", d$y)

record_timing(function() hexcoords(dx = 0.5, dy = 0.3, n = 20000))
write_ref("hexcoords")
