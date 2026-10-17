suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(is.date(Sys.time()), is.date(Sys.Date()), is.date(1), is.date(NA), is.date(NULL))
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
