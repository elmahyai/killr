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
    index2char(c(2000, 2000.25, 2000.5)),
    index2char(seq(2000, 2000.75, by = 0.25), frequency = 4),
    index2char(c(1999.75, 2000), frequency = 4),
    index2char(c(-1.5, -1.25, -1), frequency = 4),
    index2char(c(1/3, 1e-4, 1e5), digits = 4),
    index2char(c(2000, 2000.3, 2000.5), frequency = 4)
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
