.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

one <- function() {
  tryCatch(
    github_remote("r-lib/remotes#7", auth_token = NULL),
    error = function(e) e
  )
}

value <- one()

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

tagged <- github_remote("igraph=igraph/rigraph@v1.0.0", auth_token = NULL)
stopifnot(
  identical(tagged$package, "igraph"),
  identical(tagged$repo, "rigraph"),
  identical(tagged$ref, "v1.0.0")
)
branch <- github_remote("user/repo", ref = "branch", auth_token = NULL)
stopifnot(identical(branch$ref, "branch"))
kept <- github_remote("user/repo/pkg@tag", ref = "branch", auth_token = NULL)
stopifnot(identical(kept$ref, "tag"))
missing_ref <- github_remote("user/repo", ref = NULL, auth_token = NULL)
stopifnot(identical(missing_ref$ref, "HEAD"))

tag_line <- paste0(
  "github_remote(\"igraph=igraph/rigraph@v1.0.0\", auth_token = NULL) returns package ",
  tagged$package, ", repo ", tagged$repo, ", ref ", tagged$ref, "."
)

if (inherits(value, "error")) {
  username <- NULL
  repo <- NULL
  ref <- NULL
  err <- conditionMessage(value)
  pull_text <- paste0(
    "github_remote(\"r-lib/remotes#7\", auth_token = NULL) stops with:\n",
    err
  )
} else {
  username <- value$username
  repo <- value$repo
  ref <- value$ref
  err <- NULL
  pull_text <- paste0(
    "github_remote(\"r-lib/remotes#7\", auth_token = NULL) returns username ",
    username, ", repo ", repo, ", ref ", ref, "."
  )
}

cat(tag_line, "\n", pull_text, "\n", sep = "", file = file.path(out_dir, "github_remote-r.txt"))

json_str <- function(s) {
  if (is.null(s)) return("null")
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  paste0("\"", s, "\"")
}

cat(sprintf(
  "{\"username\":%s,\"repo\":%s,\"ref\":%s,\"error\":%s,\"median_ms\":%.17g}\n",
  json_str(username),
  json_str(repo),
  json_str(ref),
  json_str(err),
  median(elapsed) * 1000
))
