suppressPackageStartupMessages(library(quantreg))
one <- function() {z <- sfn.control(); c(z$cachsz, z$small, z$maxiter, z$tiny, z$Large)}
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
