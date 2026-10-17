.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(diffobj))
a <- letters[1:6]
b <- c("b", "CC", "DD", "d", "f")
one <- function() ses(a, b)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "|"), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
