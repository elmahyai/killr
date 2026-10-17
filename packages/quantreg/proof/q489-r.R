suppressPackageStartupMessages(library(quantreg))
one <- function() {x <- c(3,1,4,1,5,9,2,6); c(q489(x, 0.5), q489(x, 0.25))}
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
