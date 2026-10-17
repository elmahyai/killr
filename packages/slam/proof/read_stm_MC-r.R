.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slam))

one <- function() {
  f <- tempfile()
  writeLines("2 2 3", paste0(f, "_dim"))
  writeLines(c("0", "1", "0"), paste0(f, "_row_ccs"))
  writeLines(c("0", "2", "3"), paste0(f, "_col_ccs"))
  writeLines(c("1.5", "3", "2"), paste0(f, "_tfn_nz"))
  as.numeric(as.matrix(read_stm_MC(f)))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
