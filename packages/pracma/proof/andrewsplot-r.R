.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(pracma))
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
  { A <- matrix(c(1,2,3,4), 2, 2); npts <- 5; xpts <- seq(0, 2*pi, length.out=npts); Y <- matrix(NA, 2, npts); for (i in 1:2) { xs <- A[i,]; ypts <- c(); for (p in xpts) { y <- xs[1]; for (j in 2:2) { if (j %% 2 == 1) y <- y + xs[j]*sin((j %/% 2)*p) else y <- y + xs[j]*cos((j %/% 2)*p) }; ypts <- c(ypts, y) }; Y[i,] <- ypts }; pdf(file.path(tempdir(),"p.pdf")); andrewsplot(A, c(1L,2L), style="cart", npts=5); dev.off(); as.numeric(Y) }
}
value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
