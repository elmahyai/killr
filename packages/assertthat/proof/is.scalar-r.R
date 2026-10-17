suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(is.scalar(1), is.scalar(1:5), is.scalar("a"), is.scalar(c("a", "b")), is.scalar(TRUE), is.scalar(c(TRUE, FALSE)), is.scalar(NULL), is.scalar(NA), is.scalar(Inf))
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
