suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")
one <- function() {
  x <- c(
    NA,
    0,
    -1,
    exp(seq(log(1e-3), log(4.999), length.out = 40)),
    5,
    5.001,
    10,
    100,
    1e6,
    1e15
  )
  logmdigamma(x)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
