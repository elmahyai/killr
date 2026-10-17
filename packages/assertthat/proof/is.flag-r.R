suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(is.flag(1), is.flag("a"), is.flag(TRUE), is.flag(FALSE), is.flag(c(TRUE, FALSE)), is.flag(NULL), is.flag(NA), is.flag(Inf))
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
