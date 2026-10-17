suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(is.string(1), is.string("a"), is.string(c("a", "b")), is.string(TRUE), is.string(NULL), is.string(NA), is.string(Inf))
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
