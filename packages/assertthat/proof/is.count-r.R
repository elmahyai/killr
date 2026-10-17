suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(is.count(1), is.count(-1), is.count(1.5), is.count(1:5), is.count("a"), is.count(TRUE), is.count(NULL), is.count(NA), is.count(NA_real_), is.count(NA_integer_), is.count(NaN), is.count(Inf), is.count(-Inf), is.count(1e10 + 0.0001), is.count(1e10 - 0.1))
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
