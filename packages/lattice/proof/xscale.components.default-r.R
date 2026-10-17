.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(lattice))
if (packageDescription("lattice")$Version != "0.23-1") stop("expected lattice 0.23-1")
options(warn = -1)

encode <- function(comp) {
  b <- comp$bottom
  nums <- c(
    as.numeric(comp$num.limit),
    as.numeric(b$ticks$at),
    as.numeric(b$ticks$tck),
    as.numeric(b$labels$at),
    as.numeric(b$labels$check.overlap),
    as.numeric(comp$top)
  )
  list(nums = nums, labels = as.character(b$labels$labels))
}

one <- function() {
  encode(xscale.components.default(c(0, 1)))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(
  list(value = value$nums, labels = value$labels, median_ms = median(elapsed) * 1000),
  auto_unbox = FALSE,
  digits = 17,
  na = "null"
))
