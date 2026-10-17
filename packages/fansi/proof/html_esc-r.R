.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fansi))
hex_one <- function(s) {
  if (length(s) == 0 || is.na(s)) return("null")
  paste(sprintf("%02x", as.integer(charToRaw(enc2utf8(s)))), collapse = "")
}
hex_val <- function(x) {
  if (is.list(x) && !is.null(names(x))) x <- unlist(x, use.names = FALSE)
  x <- as.character(x)
  parts <- vapply(seq_along(x), function(i) hex_one(x[[i]]), "")
  paste0("[", paste(sprintf('"%s"', parts), collapse = ","), "]")
}
one <- function() {
  html_esc("<tag attr='x' & \"y\">")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', hex_val(value), median(elapsed) * 1000))
