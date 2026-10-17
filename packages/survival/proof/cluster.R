suppressPackageStartupMessages(library(survival))

one <- function() {
  n <- cluster(c(1, 1, 2, 2, 3, 3))
  ch <- cluster(c("a", "a", "b", "b"))
  f <- cluster(factor(c("x", "y", "x")))
  c(sprintf("%.17g", n), ch, as.character(f))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
