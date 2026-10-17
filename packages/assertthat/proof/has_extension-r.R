suppressPackageStartupMessages(library(assertthat))

one <- function() {
  c(has_extension("a/b.txt", "txt"), has_extension("/tmp/foo", ""), has_extension("file.", ""), has_extension("file.c++", "c++"), has_extension(".hidden", "hidden"), has_extension("a.tar.gz", "gz"), has_extension("a.é", "é"), has_extension("x.Y_z", "Y_z"))
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
