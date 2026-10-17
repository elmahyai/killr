.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(pracma))
flat <- function(x) {
  if (is.null(x) || length(x) == 0) return("")
  x <- as.numeric(x)
  paste(vapply(x, function(v) if (is.na(v)) "NA" else sprintf("%.16g", v), ""), collapse = "|")
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s
}
one <- function() {
  c(shooting(function(t, y1, y2) -y1, 0, 0.5, 1, function(u, v) u - cos(0.5), 0, -1, tol=1e-6, hmax=0.1)$y)
}
value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
