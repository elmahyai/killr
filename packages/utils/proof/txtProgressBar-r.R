suppressPackageStartupMessages(library(utils))
one <- function() {
  f <- tempfile()
  con <- file(f, open = "wb")
  pb <- txtProgressBar(min = 0, max = 10, style = 3, file = con)
  setTxtProgressBar(pb, 5)
  close(pb)
  close(con)
  readChar(f, 1e6)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value)
cat(sprintf("%.17g\n", median(elapsed) * 1000))
