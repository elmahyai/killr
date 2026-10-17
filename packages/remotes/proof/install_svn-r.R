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
expected <- paste0(
  "Failed to install 'unknown package' from SVN:\n",
  "  SVN does not seem to be installed on your system."
)

one <- function() {
  tryCatch(
    install_svn(
      "https://example.invalid/repo",
      dependencies = FALSE, upgrade = "never", quiet = TRUE, lib = lib
    ),
    error = function(e) conditionMessage(e)
  )
}
value <- one()
stopifnot(identical(value, expected))
stopifnot(identical(list.files(lib), character()))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, expected))
}

sentence <- "install_svn() fails with: SVN does not seem to be installed on your system."
writeLines(sentence, file.path(out_dir, "install_svn-r.txt"))
cat(sprintf("{\"message\":\"svn-missing\",\"median_ms\":%.17g}\n", median(elapsed) * 1000))
