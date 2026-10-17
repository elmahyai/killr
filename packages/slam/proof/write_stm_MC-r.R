.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(slam))

one <- function() {
  f <- tempfile()
  m <- simple_triplet_matrix(i=c(1,2,1), j=c(1,1,2), v=c(1.5,2,3), nrow=2, ncol=2)
  write_stm_MC(m, f)
  parts <- c(
    paste(readLines(paste0(f, "_dim")), collapse = "\n"),
    paste(readLines(paste0(f, "_row_ccs")), collapse = "\n"),
    paste(readLines(paste0(f, "_col_ccs")), collapse = "\n"),
    paste(readLines(paste0(f, "_tfn_nz")), collapse = "\n")
  )
  utf8ToInt(paste(parts, collapse = "\n"))
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
