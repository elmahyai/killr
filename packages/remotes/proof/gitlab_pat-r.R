.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))

json_escape <- function(x) {
  if (is.null(x)) return("null")
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  x <- gsub("\r", "\\r", x, fixed = TRUE)
  x <- gsub("\n", "\\n", x, fixed = TRUE)
  x <- gsub("\t", "\\t", x, fixed = TRUE)
  paste0("\"", x, "\"")
}

Sys.setenv(GITLAB_PAT = "glpat-example")

one <- function() {
  gitlab_pat()
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

Sys.setenv(GITLAB_PAT = "")
stopifnot(is.null(gitlab_pat()))
Sys.unsetenv("GITLAB_PAT")
stopifnot(is.null(gitlab_pat()))

cat(sprintf(
  "{\"value\":%s,\"median_ms\":%.17g}\n",
  json_escape(value),
  median(elapsed) * 1000
))
