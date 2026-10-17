suppressPackageStartupMessages(library(extraDistr))
one <- function() {
  phnorm(c(0, 0.5, 1, 2, 4), 2)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
