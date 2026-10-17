.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

options(remotes.git_credentials = NULL)
stopifnot(is.null(git_credentials()))

options(remotes.git_credentials = "plain-token")

one <- function() git_credentials()
value <- one()
stopifnot(identical(value, "plain-token"))
writeLines(
  paste0(
    "options(remotes.git_credentials = \"plain-token\"); git_credentials() returns ",
    value,
    "."
  ),
  file.path(out_dir, "git_credentials-r.txt")
)

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":\"%s\",\"median_ms\":%.17g}\n",
  value,
  median(elapsed) * 1000
))
