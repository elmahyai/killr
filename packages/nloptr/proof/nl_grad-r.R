.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nloptr))

one <- function() nl.grad(seq(0, 1, by = 0.2), function(x) sum(x^2))
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
if (is.character(value) && length(value) == 1) {
  esc <- gsub("\\", "\\\\", value, fixed = TRUE)
  esc <- gsub("\"", "\\\"", esc, fixed = TRUE)
  esc <- gsub("\n", "\\n", esc, fixed = TRUE)
  esc <- gsub("\t", "\\t", esc, fixed = TRUE)
  encoded <- paste0("\"", esc, "\"")
} else if (is.logical(value) && length(value) == 1) {
  encoded <- if (isTRUE(value)) "true" else "false"
} else {
  encoded <- json_num(value)
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", encoded, median(elapsed) * 1000))
