.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(magrittr))

root <- "/home/ahmed/killr_projects/killr/packages/magrittr"
dir.create(file.path(root, "docs", "output"), recursive = TRUE, showWarnings = FALSE)
writeLines(
  "data.frame(z = 1:3) %$% sum(z) returns 6.",
  file.path(root, "docs", "output", "%$%-r.txt")
)

one <- function() data.frame(z = 1:3) %$% sum(z)

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%.17g],\"median_ms\":%.17g}\n",
  as.numeric(value),
  median(elapsed) * 1000
))
