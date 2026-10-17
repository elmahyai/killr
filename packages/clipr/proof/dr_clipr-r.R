suppressPackageStartupMessages(library(clipr))
system2("xclip", c("-selection", "clipboard"), input = "seed")

json_escape <- function(x) {
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  paste0("\"", x, "\"")
}

one <- function() dr_clipr()
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":%s,\"median_ms\":%.17g}\n",
  json_escape(value),
  median(elapsed) * 1000
))
