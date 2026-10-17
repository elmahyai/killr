suppressPackageStartupMessages(library(digest))
one <- function() sha1_digest(NULL)
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%s\n%.17g\n", value, median(elapsed) * 1000))
