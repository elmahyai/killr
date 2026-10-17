suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(is.number(1), is.number(-1), is.number(1.5), is.number(1:5), is.number('a'), is.number(TRUE), is.number(NULL), is.number(NA), is.number(NA_real_), is.number(Inf), is.number(-Inf))
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
