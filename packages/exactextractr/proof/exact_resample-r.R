.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({ library(raster); library(sf); library(exactextractr) })
one <- function() {
  src <- raster::raster(matrix(1:16, ncol=4), xmn=0, xmx=4, ymn=0, ymx=4)
  dst <- raster::raster(xmn=0, xmx=4, ymn=0, ymx=4, nrows=2, ncols=2)
  suppressWarnings(as.matrix(exact_resample(src, dst, "mean")))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
rows <- apply(value, 1, function(row) paste(sprintf("%.17g", row), collapse=" "))
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', paste0("[", paste(sprintf('"%s"', rows), collapse=","), "]"), median(elapsed)*1000))
