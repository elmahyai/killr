suppressPackageStartupMessages(library(assertthat))

file <- tempfile()
cat("x", file = file)
miss <- tryCatch(is.readable("asdf-missing"), error = function(e) conditionMessage(e))
one <- function() c(is.readable(tempdir()), is.readable(file))
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(as.integer(value), collapse = " "), "\n", sep = "")
cat(miss, "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
