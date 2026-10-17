.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(pracma))
flat <- function(x) {
  if (is.null(x)) return("null")
  fmt <- function(v) if (is.na(v)) "NA" else sprintf("%.16g", as.numeric(v))
  if (is.matrix(x)) return(paste(c(nrow(x), ncol(x), vapply(as.numeric(x), fmt, "")), collapse = "|"))
  if (length(x) == 0) return("")
  paste(vapply(as.numeric(x), fmt, ""), collapse = "|")
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}
one <- function() {
  finds(c(0, 3, 0, -1))
}
value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
