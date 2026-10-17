.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(MASS))

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
this_dir <- if (length(file_arg)) {
  dirname(normalizePath(sub("^--file=", "", file_arg)))
} else {
  "."
}
x <- as.numeric(readLines(file.path(this_dir, "fitdistr-x.txt")))

one <- function() {
  fit <- fitdistr(x, "normal")
  c(
    fit$estimate["mean"],
    fit$estimate["sd"],
    fit$sd["mean"],
    fit$sd["sd"],
    fit$loglik,
    fit$vcov[1, 1],
    fit$vcov[2, 1],
    fit$vcov[1, 2],
    fit$vcov[2, 2],
    fit$n
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = "\n"), "\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
