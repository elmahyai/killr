.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({ library(raster); library(sf); library(exactextractr) })
one <- function() {
  g <- sf::st_sf(geometry=sf::st_sfc(
    sf::st_polygon(list(matrix(c(0,0, 2,0, 2,2, 0,2, 0,0), ncol=2, byrow=TRUE))),
    sf::st_polygon(list(matrix(c(1,1, 3,1, 3,3, 1,3, 1,1), ncol=2, byrow=TRUE)))
  ))
  y <- raster::raster(xmn=0, xmx=3, ymn=0, ymx=3, nrows=3, ncols=3)
  as.matrix(rasterize_polygons(g, y))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- apply(value, 1, function(row) paste(ifelse(is.na(row), "NA", as.character(row)), collapse=" "))
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', paste0("[", paste(sprintf('"%s"', shown), collapse=","), "]"), median(elapsed)*1000))
