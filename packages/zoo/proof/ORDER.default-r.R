.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
flat <- function(x) {
  if (is.null(x)) return("null")
  if (is.character(x)) return(paste(x, collapse = "|"))
  if (length(x) == 0) return("")
  x <- as.numeric(x)
  paste(vapply(x, function(v) if (is.na(v)) "NA" else sprintf("%.16g", v), ""), collapse = "|")
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s
}
one <- function() {
  c(
    ORDER.default(c(2, NA, 1), na.last = NA),
    ORDER.default(c(1, 1, 2), c(2, 1, 0), decreasing = TRUE),
    ORDER.default(c(-1, -3, 2, 0)),
    ORDER.default(c(0, -0, 1)),
    ORDER.default(c(1, NaN, NA, 0, -0, -1))
  )
}

value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
