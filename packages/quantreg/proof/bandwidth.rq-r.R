suppressPackageStartupMessages(library(quantreg))
one <- function() {c(bandwidth.rq(0.5, 100), bandwidth.rq(0.9, 50, hs=FALSE, alpha=0.1))}
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
