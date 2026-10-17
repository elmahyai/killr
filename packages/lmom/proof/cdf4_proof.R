args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", grep("^--file=", args, value = TRUE))
here <- dirname(normalizePath(script))
out <- file.path(here, "..", "docs", "output")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
lib <- Sys.getenv("LMOM_R_LIB", unset = file.path(Sys.getenv("HOME"), ".cache", "killr", "Rlib-lmom-3.3"))
suppressPackageStartupMessages(library(lmom, lib.loc = lib))
stopifnot(as.character(packageVersion("lmom", lib.loc = lib)) == "3.3")

xs <- c(-2, -0.5, 0, 0.5, 1, 2, 5, 10)
cases <- list(
  cdfkap = list(c(0, 1, 0.2, 0.1), c(1.2, 2.3, -0.25, 0.15), c(0, 1, 0, 0), c(0, 1, 0.3, -0.2)),
  cdfln3 = list(c(0.5, 1, 0.2), c(-1, 0, 1), c(0, 0.3, 0.8), c(-0.5, -0.2, 0.6)),
  cdfpe3 = list(c(0, 1, 0.5), c(1.2, 2.3, -0.8), c(0, 1, 0), c(0, 1, 1e-7), c(-1, 2, -0.3)),
  cdfwak = list(c(0, 1, 0.5, 0.2, 0.1), c(1.2, 2.3, 0.25, 0.8, -0.15), c(0, 1, 0, 0, 0),
                c(0, 1, 0.5, 0, 0), c(0, 0, 0, 0.5, 0.2), c(0, 1, 0, 0.3, 0.2), c(0, 1, -0.3, 0.2, 0.5))
)

lines <- character(); timing <- character()
for (nm in names(cases)) {
  f <- get(nm, asNamespace("lmom"))
  for (i in seq_along(cases[[nm]])) {
    p <- cases[[nm]][[i]]
    val <- f(xs, p)
    lines <- c(lines, paste(nm, i, paste(sprintf("%.17g", val), collapse = " ")))
  }
  p1 <- cases[[nm]][[1]]
  f0 <- function() f(xs, p1)
  f0()
  z <- numeric(20)
  for (i in 1:20) {
    t <- Sys.time(); f0()
    z[i] <- as.numeric(difftime(Sys.time(), t, units = "secs"))
  }
  timing <- c(timing, paste(nm, sprintf("%.12g", median(z))))
}
writeLines(lines, file.path(out, "cdf4_r_values.txt"))
writeLines(timing, file.path(out, "cdf4_r_timings.txt"))
