.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

lib <- tempfile("lib")
dir.create(lib)
stopifnot(is.null(update_packages(character(), lib = lib, quiet = TRUE, upgrade = "never")))
stopifnot(identical(list.files(lib), character()))

one <- function() {
  update_packages("remotes", lib = lib, quiet = TRUE, upgrade = "never")
}
value <- one()
stopifnot(is.null(value))
stopifnot(identical(list.files(lib), character()))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(is.null(got))
}
stopifnot(identical(list.files(lib), character()))

sentence <- "update_packages(\"remotes\", upgrade = \"never\") returns NULL."
writeLines(sentence, file.path(out_dir, "update_packages-r.txt"))
cat(sprintf("{\"value\":null,\"median_ms\":%.17g}\n", median(elapsed) * 1000))
