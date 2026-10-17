.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({ library(raster); library(sf); library(exactextractr) })
one <- function() {
  rast <- raster::raster(xmn=0, xmx=3, ymn=0, ymx=3, nrows=3, ncols=3, crs=NA)
  square <- sf::st_sfc(sf::st_polygon(list(matrix(c(0.5,0.5, 2.5,0.5, 2.5,2.5, 0.5,2.5, 0.5,0.5), ncol=2, byrow=TRUE))))
  as.matrix(coverage_fraction(rast, square)[[1]])
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
