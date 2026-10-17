suppressPackageStartupMessages(library(tools))

one <- function() {
  capture.output(.print.via.format(c("a", "b")))
  paste0(paste(capture.output(.print.via.format(c("a", "b"))), collapse="\n"), "\n")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
