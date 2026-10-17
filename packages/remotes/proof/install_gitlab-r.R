.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

spec <- "jimhester/covr"
lib <- tempfile("lib")
dir.create(lib)
installed <- tryCatch(
  install_gitlab(spec, auth_token = NULL, dependencies = FALSE, upgrade = "never", quiet = TRUE, build = FALSE, lib = lib),
  error = function(e) "error"
)

one <- function() {
  remote <- remotes:::gitlab_remote(spec)
  c(remote$username, remote$repo, remote$ref)
}
value <- one()
stopifnot(identical(value, c("jimhester", "covr", "HEAD")))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, value))
}

sentence <- "install_gitlab(\"jimhester/covr\") would install covr from jimhester/covr at HEAD."
writeLines(sentence, file.path(out_dir, "install_gitlab-r.txt"))
installed_json <- if (is.null(installed)) "null" else if (identical(installed, "covr")) "\"covr\"" else "\"error\""
cat(sprintf("{\"username\":\"jimhester\",\"repo\":\"covr\",\"ref\":\"HEAD\",\"installed\":%s,\"median_ms\":%.17g}\n", installed_json, median(elapsed) * 1000))
