.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(magrittr))
cmd <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", cmd[grepl("^--file=", cmd)])
root <- dirname(dirname(normalizePath(file_arg)))
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

f <- . %>% sqrt %>% log %>% exp
one <- function() debug_fseq(f, 2)
invisible(one())
value <- as.numeric(
  isdebugged(functions(f)[[2]]) &&
    !isdebugged(functions(f)[[1]]) &&
    !isdebugged(functions(f)[[3]])
)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%.17g,"median_ms":%.17g}\n', value, median(elapsed) * 1000))
writeLines("debug_fseq(fseq, 2) returns NULL.", file.path(out_dir, "debug_fseq-r.txt"))
