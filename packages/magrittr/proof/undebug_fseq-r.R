.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(magrittr))
cmd <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", cmd[grepl("^--file=", cmd)])
root <- dirname(dirname(normalizePath(file_arg)))
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

f <- . %>% sqrt %>% log
debug_fseq(f, 1)
one <- function() undebug_fseq(f)
value <- one()
if (!is.null(value)) stop("expected NULL")
if (any(vapply(functions(f), isdebugged, logical(1)))) stop("still marked")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":null,"median_ms":%.17g}\n', median(elapsed) * 1000))
writeLines("undebug_fseq(fseq) returns NULL.", file.path(out_dir, "undebug_fseq-r.txt"))
