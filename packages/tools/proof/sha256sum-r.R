suppressPackageStartupMessages(library(tools))

one <- function() {
  f <- tempfile()
  writeBin(charToRaw("z\n"), f)
  paste0(sha256sum(bytes=charToRaw("abc")), "\n", unname(sha256sum(f)), "\n")
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
