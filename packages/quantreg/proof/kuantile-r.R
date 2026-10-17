suppressPackageStartupMessages(library(quantreg))
# Dense probs use base R quantile(type = 7), the reference for kuantile. quantreg's own
# kuantile in R pairs order statistics wrongly for many probs, so it is not the reference there.
xd <- sin(1:92) * 10 + (1:92) / 7
one <- function() {
  x <- c(3,1,4,1,5,9,2,6)
  a <- c(as.numeric(kuantile(x, c(.25,.5,.75))), as.numeric(kuantile(x, c(.2,.8), type=5)))
  b <- as.numeric(quantile(xd, 1:99/100, type=7, names=FALSE))
  c2 <- as.numeric(quantile(xd, 5:96/100, type=7, names=FALSE))
  c3 <- as.numeric(quantile(xd, 1:92/93, type=7, names=FALSE))
  c(a, b, c2, c3)
}
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
value <- one()
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
