.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
stopifnot(isTRUE(packageVersion("nlme") == "3.1-171"))

script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", file_arg[[1]])))
}

names_fp <- function(x) {
  x <- as.character(x)
  out <- length(x)
  for (s in x) {
    codes <- utf8ToInt(s)
    out <- c(out, nchar(s), sum(codes * seq_along(codes)))
  }
  as.numeric(out)
}

build <- function() {
  M <- matrix(c(4, 1, 0, 1, 3, 0.5, 0, 0.5, 2), 3, 3)
  list(
    p1 = pdDiag(c(0.1, -0.2, 0.3), nam = c("a", "b", "c")),
    p2 = pdDiag(M),
    p3 = pdDiag(nam = c("x", "y")),
    p4 = pdDiag(c(0.4, 0.6), form = ~ u + v - 1, data = list(u = 1:3, v = c(2, 5, 1)))
  )
}

one <- function() {
  o <- build()
  unlist(lapply(o, function(p) {
    c(as.numeric(isInitialized(p)), as.numeric(p), names_fp(Names(p)))
  }))
}

example <- function() {
  o <- build()
  lines <- character(0)
  for (nm in names(o)) {
    p <- o[[nm]]
    lines <- c(
      lines,
      sprintf("%s initialized: %d", nm, as.integer(isInitialized(p))),
      sprintf("%s values: %s", nm, paste(sprintf("%.10g", as.numeric(p)), collapse = " ")),
      sprintf("%s names: %s", nm, paste(Names(p), collapse = " "))
    )
  }
  lines
}

out_dir <- file.path(script_dir(), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(example(), file.path(out_dir, "pdDiag-r.txt"))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
