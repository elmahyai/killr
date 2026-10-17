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
  list(
    b1 = pdBlocked(c(0.1, -0.2, 0.3, 0.4), nam = list(c("a", "b"), c("c", "d")),
                   pdClass = c("pdDiag", "pdCompSymm")),
    b2 = pdBlocked(nam = list(c("a", "b"), c("c", "d")),
                   pdClass = c("pdDiag", "pdCompSymm")),
    b3 = pdBlocked(c(0.1, 0.2, 0.3, 0.4, 0.5, -0.1, 0.7, 0.2),
                   nam = list(c("a", "b", "c"), c("d", "e")),
                   pdClass = c("pdLogChol", "pdDiag")),
    b4 = pdBlocked(c(0.5, 0.1), nam = list(c("a", "b"), c("c")),
                   pdClass = c("pdIdent", "pdDiag"))
  )
}

one <- function() {
  o <- build()
  unlist(lapply(o, function(p) {
    c(as.numeric(isInitialized(p)), as.numeric(coef(p)), names_fp(Names(p)),
      as.numeric(lengths(Names(p, TRUE))))
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
      sprintf("%s coef: %s", nm, paste(sprintf("%.10g", as.numeric(coef(p))), collapse = " ")),
      sprintf("%s names: %s", nm, paste(Names(p), collapse = " ")),
      sprintf("%s block sizes: %s", nm, paste(lengths(Names(p, TRUE)), collapse = " "))
    )
  }
  lines
}

out_dir <- file.path(script_dir(), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(example(), file.path(out_dir, "pdBlocked-r.txt"))

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
