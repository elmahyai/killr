.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(readxl))
one <- function() {
  paste(capture.output(print(anchored("C4", dim = c(3, 2)))), collapse = "\n")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE\n")
cat(value, "\n", sep = "")
cat("<<<END>>>\n")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
