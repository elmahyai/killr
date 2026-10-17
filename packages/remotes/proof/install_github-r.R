.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

spec <- "praise=gaborcsardi/praise"
lib <- tempfile("lib")
dir.create(lib)
installed <- tryCatch(
  install_github(spec, auth_token = NULL, dependencies = FALSE, upgrade = "never", quiet = TRUE, build = FALSE, lib = lib),
  error = function(e) conditionMessage(e)
)

one <- function() {
  remote <- github_remote(spec, auth_token = NULL)
  c(remote$package, remote$username, remote$repo, remote$ref)
}
value <- one()
stopifnot(identical(value, c("praise", "gaborcsardi", "praise", "HEAD")))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, value))
}

sentence <- "install_github(\"praise=gaborcsardi/praise\") would install praise from gaborcsardi/praise at HEAD."
writeLines(sentence, file.path(out_dir, "install_github-r.txt"))
installed_json <- if (is.null(installed)) "null" else if (is.character(installed) && length(installed) == 1 && !grepl("\n", installed)) paste0("\"", installed, "\"") else "\"error\""
cat(sprintf("{\"package\":\"praise\",\"username\":\"gaborcsardi\",\"repo\":\"praise\",\"ref\":\"HEAD\",\"installed\":%s,\"median_ms\":%.17g}\n", installed_json, median(elapsed) * 1000))
