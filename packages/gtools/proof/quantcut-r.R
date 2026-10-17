.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  if (length(x) == 0) return(character(0))
  vapply(x, function(v) if (is.na(v)) "NA" else as.character(v), "")
}

one <- function() {
  set.seed(1234)
  x <- rnorm(1000)
  quartiles <- as.character(quantcut(x))
  deciles1 <- as.character(quantcut(x, 10))
  deciles2 <- as.character(quantcut(x, seq(0, 1, by = 0.1)))
  stopifnot(identical(deciles1, deciles2))
  x2 <- round(x)
  tied <- as.character(quantcut(x2, 10))
  x3 <- c(1, 2, 3, NA, 5)
  small <- as.character(quantcut(x3, 2))
  c(flat(quartiles), flat(deciles1), flat(tied), flat(small))
}

invisible(one())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', paste0('"', paste(value, collapse = "|"), '"'), median(elapsed) * 1000))
