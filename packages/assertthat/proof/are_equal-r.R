suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(are_equal(2, 1.9), are_equal(2, 1.999, tol = 0.01), are_equal(2, 2), are_equal("a", "a"), are_equal("a", "b"), are_equal(NA, NA), are_equal(NULL, NULL))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(as.integer(value), collapse = " "), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
