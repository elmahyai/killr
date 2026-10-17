suppressPackageStartupMessages(library(clipr))
system2("xclip", c("-selection", "clipboard"), input = "seed")

one <- function() clipr_available()
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":%s,\"median_ms\":%.17g}\n",
  if (isTRUE(value)) "true" else "false",
  median(elapsed) * 1000
))
