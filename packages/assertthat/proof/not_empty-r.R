suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(not_empty(1), not_empty(numeric()), not_empty(mtcars[0, ]), not_empty(mtcars[, 0]), not_empty(NA), not_empty(NULL))
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
