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

ncol_fp <- function(x) if (is.null(x)) -1 else as.numeric(x)

M3 <- matrix(c(4, 1, 0.5, 1, 3, 0.2, 0.5, 0.2, 2), 3)

build <- function() {
  o1 <- pdDiag(nam = c("a", "b", "c"))
  o2 <- pdCompSymm(nam = c("a", "b", "c"))
  o3 <- pdLogChol(nam = c("x", "y", "z"))
  o4 <- pdIdent(nam = c("a", "b"))
  list(
    r1 = pdConstruct(o1, c(0.1, 0.2, 0.3)),
    r2 = pdConstruct(o2, c(0.2, 0.5)),
    r3 = pdConstruct(o3, M3),
    r4 = pdConstruct(o4, 0.25)
  )
}

one <- function() {
  o <- build()
  unlist(lapply(o, function(p) {
    c(as.numeric(isInitialized(p)), as.numeric(p), ncol_fp(attr(p, "ncol")),
      names_fp(Names(p)))
  }))
}

example <- function() {
  o <- build()
  lines <- character(0)
  for (nm in names(o)) {
    p <- o[[nm]]
    lines <- c(
      lines,
      sprintf("%s class: %s", nm, class(p)[1]),
      sprintf("%s values: %s", nm, paste(sprintf("%.10g", as.numeric(p)), collapse = " ")),
      sprintf("%s ncol: %s", nm, paste(ncol_fp(attr(p, "ncol")), collapse = " ")),
      sprintf("%s names: %s", nm, paste(Names(p), collapse = " "))
    )
  }
  lines
}

out_dir <- file.path(script_dir(), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(example(), file.path(out_dir, "pdConstruct-r.txt"))

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
