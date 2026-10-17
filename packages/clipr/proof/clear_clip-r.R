suppressPackageStartupMessages(library(clipr))
system2("xclip", c("-selection", "clipboard"), input = "seed")
write_clip("to-clear")

one <- function() clear_clip()
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
emptied <- read_clip()
cat(sprintf(
  "{\"value\":\"\",\"empty\":%s,\"median_ms\":%.17g}\n",
  if (is.null(emptied)) "true" else "false",
  median(elapsed) * 1000
))
