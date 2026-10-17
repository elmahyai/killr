suppressPackageStartupMessages(library(digest))
sha1 <- getVDigest(algo = "sha1")
one <- function() sha1(letters)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
cat(paste(value, collapse = "\n"), "\n", sep = "")
