suppressPackageStartupMessages(library(survival))

one <- function() {
  w <- coxph.wtest(matrix(c(2, 0.5, 0.5, 1), 2, 2), c(1, -1))
  w1 <- coxph.wtest(2, 3)
  c(sprintf("%.17g", w$test), sprintf("%d", w$df),
    sprintf("%.17g", w$solve),
    sprintf("%.17g", w1$test), sprintf("%d", w1$df), sprintf("%.17g", w1$solve))
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
