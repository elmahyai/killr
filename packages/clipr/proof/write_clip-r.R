suppressPackageStartupMessages(library(clipr))
system2("xclip", c("-selection", "clipboard"), input = "seed")

json_escape <- function(x) {
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  x <- gsub("\r", "\\r", x, fixed = TRUE)
  x <- gsub("\n", "\\n", x, fixed = TRUE)
  x <- gsub("\t", "\\t", x, fixed = TRUE)
  paste0("\"", x, "\"")
}

one <- function() {
  write_clip(data.frame(a = c(1, 2, 3), b = c(4, 5, 6)), return_new = TRUE)
}
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
