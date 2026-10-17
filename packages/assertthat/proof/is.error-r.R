suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(is.error(try(stop("!!"), silent = TRUE)), is.error(1), is.error(NA), is.error(NULL))
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
