.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(BB))
A <- rbind(c(1, 1), c(1, 0))
b <- c(3, 0)
one <- function() projectLinear(c(0.2, 0.2), A, b, meq=0)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse=","), "
", sep="")
cat("MS
")
cat(sprintf("%.17g
", median(elapsed) * 1000))
