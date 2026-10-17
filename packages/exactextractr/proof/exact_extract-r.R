.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({ library(raster); library(sf); library(exactextractr) })
one <- function() {
  rast <- raster::raster(matrix(1:100, ncol=10), xmn=0, ymn=0, xmx=10, ymx=10)
  poly <- sf::st_as_sfc("POLYGON ((2 2, 7 6, 4 9, 2 2))")
  exact_extract(rast, poly, "mean", progress=FALSE)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%.17g,"median_ms":%.17g}\n', value, median(elapsed)*1000))
