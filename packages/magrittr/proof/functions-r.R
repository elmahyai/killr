.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(magrittr))
cmd <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", cmd[grepl("^--file=", cmd)])
root <- dirname(dirname(normalizePath(file_arg)))
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

f <- . %>% sqrt %>% log
one <- function() functions(f)
fns <- one()
value <- fns[[2]](fns[[1]](16))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%.17g,"median_ms":%.17g}\n', value, median(elapsed) * 1000))
writeLines("functions(fseq) returns 2 functions.", file.path(out_dir, "functions-r.txt"))
