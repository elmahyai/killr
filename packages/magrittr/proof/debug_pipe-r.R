.libPaths(c(path.expand("~/R/library"), .libPaths()))
cmd <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", cmd[grepl("^--file=", cmd)])
root <- dirname(dirname(normalizePath(file_arg)))
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

{
  suppressPackageStartupMessages(library(magrittr))
  one <- function() debug_pipe(5)
  value <- one()
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    one()
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  cat(sprintf('{"value":%.17g,"median_ms":%.17g}\n', value, median(elapsed) * 1000))
  writeLines(
    c(
      "Called from: debug_pipe(5)",
      "debug: x",
      "debug_pipe(5) returns 5."
    ),
    file.path(out_dir, "debug_pipe-r.txt")
  )
}
