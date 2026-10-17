suppressPackageStartupMessages(library(utils))
one <- function() {
  f <- tempfile()
  con <- file(f, open = "wb")
  pb <- txtProgressBar(min = 0, max = 10, style = 1, file = con)
  setTxtProgressBar(pb, 4)
  value <- getTxtProgressBar(pb)
  close(pb)
  close(con)
  value
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%s\n%.17g\n", value, median(elapsed) * 1000))
