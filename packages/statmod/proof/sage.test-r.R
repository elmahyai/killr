suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

one <- function() {
  c(
    sage.test(c(0, 5, 10), c(0, 30, 50), n1 = 10000, n2 = 15000),
    sage.test(c(1, 5, 10), c(2, 4, 10), n1 = 100, n2 = 100),
    sage.test(5000, 6000, n1 = 10000, n2 = 15000),
    sage.test(c(3, 7), c(4, 3), n1 = 20, n2 = 20),
    sage.test(c(0.4, 2.6), c(1.4, 3.6)),
    sage.test(c(2, 8, 15), c(1, 12, 5), n1 = 50, n2 = 60)
  )
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
