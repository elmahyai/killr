suppressPackageStartupMessages(library(quantreg))
z <- list(structure(list(tau=.5, coefficients=matrix(c(1.2,2.3,.1,.2,.03,.04),2,3,
  dimnames=list(c("a","b"), c("v","s","p")))), class="summary.rq"))
one <- function() {
  latex.summary.rqs(z, caption="Demo", file="/tmp/summary")
  paste(readLines("/tmp/summary.tex"), collapse="\n")
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time()); one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(one(), "\n", sep="")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
