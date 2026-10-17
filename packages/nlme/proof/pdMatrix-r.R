.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
stopifnot(isTRUE(packageVersion("nlme") == "3.1-171"))

script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", file_arg[[1]])))
}

build <- function() {
  list(
    diag = pdDiag(c(0.1, -0.2, 0.3), nam = c("a", "b", "c")),
    ident = pdIdent(0.3, nam = c("a", "b", "c")),
    compsymm = pdCompSymm(c(log(1.5), 0.4), nam = c("a", "b", "c")),
    logchol = pdLogChol(c(0.1, -0.2, 0.3, 0.4, 0.5, -0.1), nam = c("a", "b", "c")),
    blocked = pdBlocked(c(0.1, -0.2, 0.3, 0.4), nam = list(c("a", "b"), c("c", "d")),
                        pdClass = c("pdDiag", "pdCompSymm"))
  )
}

one <- function() {
  o <- build()
  c(
    as.numeric(pdMatrix(o$diag)), as.numeric(pdMatrix(o$diag, factor = TRUE)),
    as.numeric(pdMatrix(o$ident)), as.numeric(pdMatrix(o$ident, factor = TRUE)),
    as.numeric(pdMatrix(o$compsymm)), as.numeric(pdMatrix(o$compsymm, factor = TRUE)),
    as.numeric(pdMatrix(o$logchol)), as.numeric(pdMatrix(o$logchol, factor = TRUE)),
    as.numeric(pdMatrix(o$blocked)), as.numeric(pdMatrix(o$blocked, factor = TRUE))
  )
}

example <- function() {
  o <- build()
  lines <- character(0)
  for (nm in names(o)) {
    m <- pdMatrix(o[[nm]])
    f <- pdMatrix(o[[nm]], factor = TRUE)
    lines <- c(
      lines,
      sprintf("%s matrix (column-major): %s", nm,
              paste(sprintf("%.10g", as.numeric(m)), collapse = " ")),
      sprintf("%s factor (column-major): %s", nm,
              paste(sprintf("%.10g", as.numeric(f)), collapse = " "))
    )
  }
  lines
}

out_dir <- file.path(script_dir(), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(example(), file.path(out_dir, "pdMatrix-r.txt"))

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
