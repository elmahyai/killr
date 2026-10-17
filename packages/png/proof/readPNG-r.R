.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(png))
p <- system.file("img", "Rlogo.png", package = "png")
one <- function() {
  img <- readPNG(p)
  c(dim(img), as.numeric(img))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat('{"value":[')
cat(sprintf("%.17g", value), sep = ",")
cat(sprintf('],"median_ms":%.17g}\n', median(elapsed) * 1000))
