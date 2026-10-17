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
installed <- tryCatch(
  install_bitbucket("djnavarro/lsr", dependencies = FALSE, upgrade = "never", quiet = TRUE, build = FALSE, lib = lib),
  error = function(e) "error"
)

one <- function() {
  remote <- remotes:::bitbucket_remote("djnavarro/lsr")
  c(remote$username, remote$repo, remote$ref)
}
value <- one()
stopifnot(identical(value, c("djnavarro", "lsr", "HEAD")))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, value))
}

sentence <- "install_bitbucket(\"djnavarro/lsr\") would install lsr from djnavarro/lsr at HEAD."
writeLines(sentence, file.path(out_dir, "install_bitbucket-r.txt"))
installed_json <- if (identical(installed, "lsr")) "\"lsr\"" else "\"error\""
cat(sprintf("{\"username\":\"djnavarro\",\"repo\":\"lsr\",\"ref\":\"HEAD\",\"installed\":%s,\"median_ms\":%.17g}\n", installed_json, median(elapsed) * 1000))
