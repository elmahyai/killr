
suppressPackageStartupMessages(library(filelock))
one <- function() {
  path <- tempfile("filelock")
  lck <- lock(path)
  txt <- paste(capture.output(print(lck)), collapse = "\n")
  txt <- sub(path, "PATH", txt, fixed = TRUE)
  unlock(lck)
  txt
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":\"%s\",\"median_ms\":%.17g}\n", gsub("\"", "\\\"", value), median(elapsed) * 1000))
