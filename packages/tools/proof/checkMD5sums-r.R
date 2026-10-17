suppressPackageStartupMessages(library(tools))

one <- function() {
  dir <- tempfile()
  dir.create(dir)
  writeBin(charToRaw("hello\n"), file.path(dir, "a.txt"))
  hash <- unname(md5sum(file.path(dir, "a.txt")))
  writeLines(c(paste0(hash, "  a.txt"), "abc  missing.txt"), file.path(dir, "MD5"))
  msg <- capture.output(res <- checkMD5sums(dir=dir))
  paste0(res, " || ", paste(msg, collapse="|"), "\n")
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
