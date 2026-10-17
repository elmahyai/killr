args <- commandArgs(trailingOnly = FALSE)
script <- sub("^--file=", "", grep("^--file=", args, value = TRUE))
here <- dirname(normalizePath(script))
out <- file.path(here, "..", "docs", "output")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
lib <- Sys.getenv("LMOM_R_LIB", unset = file.path(Sys.getenv("HOME"), ".cache", "killr", "Rlib-lmom-3.3"))
suppressPackageStartupMessages(library(lmom, lib.loc = lib))
cases <- list(
  cdfexp=c(0,2), cdfgam=c(2,1.5), cdfgev=c(0,1,0.2),
  cdfglo=c(0,1,-0.3), cdfgno=c(0,1,0.2), cdfgpa=c(0,1,0.3),
  cdfgum=c(0,1), cdfkap=c(0,1,0.2,0.1), cdfln3=c(0.5,1,0.2),
  cdfnor=c(0,1), cdfpe3=c(0,1,0.5), cdfwak=c(0,1,0.5,0.2,0.1),
  cdfwei=c(0,1.5,2))
xs <- c(-2,-0.5,0,0.5,1,2,5,10)
lines <- character(); timing <- character()
for (nm in names(cases)) {
  f <- get(nm, asNamespace("lmom")); p <- cases[[nm]]
  val <- f(xs, p)
  lines <- c(lines, paste(nm, paste(sprintf("%.17g", val), collapse=" ")))
  f0 <- function() f(xs, p); f0(); z <- numeric(20)
  for (i in 1:20) { t <- Sys.time(); f0(); z[i] <- as.numeric(difftime(Sys.time(), t, units="secs")) }
  timing <- c(timing, paste(nm, sprintf("%.12g", median(z))))
}
writeLines(lines, file.path(out, "cdf_r_values.txt"))
writeLines(timing, file.path(out, "cdf_r_timings.txt"))
