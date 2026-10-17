suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(has_args(mean, "x"), has_args(mean, "x", exact = TRUE), has_args(mean, "y"), has_args(rnorm, "n"), has_args(rnorm, c("n", "mean")), has_args(rnorm, c("mean", "sd", "n")), has_args(rnorm, "n", exact = TRUE), has_args(rnorm, c("n", "mean"), exact = TRUE), has_args(rnorm, c("mean", "sd", "n"), exact = TRUE))
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
