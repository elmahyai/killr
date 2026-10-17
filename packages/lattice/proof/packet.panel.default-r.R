.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(lattice))
if (packageDescription("lattice")$Version != "0.23-1") stop("expected lattice 0.23-1")
options(warn = -1)
one <- function() {
  layout <- c(2L, 2L, 1L)
  condlevels <- list(c(1L, 2L), c(1L, 2L, 3L))
  p1 <- packet.panel.default(layout, condlevels, 1L, 1L, 1L, c(FALSE, TRUE, FALSE, FALSE))
  p2 <- packet.panel.default(layout, condlevels, 1L, 2L, 1L, c(FALSE, TRUE, FALSE, FALSE))
  p3 <- packet.panel.default(c(2L, 2L, 2L), condlevels, 2L, 1L, 1L, FALSE, all.pages.skip = FALSE)
  c(p1, p2, p3)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = as.numeric(value), median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
