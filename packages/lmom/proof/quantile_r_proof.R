args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
here <- dirname(normalizePath(sub("^--file=", "", file_arg)))
out <- file.path(here, "..", "docs", "output")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
lib <- Sys.getenv("LMOM_R_LIB", unset = file.path(Sys.getenv("HOME"), ".cache", "killr", "Rlib-lmom-3.3"))
suppressPackageStartupMessages(library(lmom, lib.loc = lib))
stopifnot(as.character(packageVersion("lmom", lib.loc = lib)) == "3.3")

f <- c(0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99)
cases <- list(
  quaexp = list(para = c(1.2, 2.3)),
  quagam = list(para = c(2.4, 1.7)),
  quagev = list(para = c(1.2, 2.3, 0.25)),
  quaglo = list(para = c(1.2, 2.3, -0.25)),
  quagno = list(para = c(1.2, 2.3, 0.25)),
  quagpa = list(para = c(1.2, 2.3, -0.25)),
  quagum = list(para = c(1.2, 2.3)),
  quakap = list(para = c(1.2, 2.3, 0.25, -0.15)),
  qualn3 = list(para = c(1.2, 0.3, 0.8)),
  quanor = list(para = c(1.2, 2.3)),
  quape3 = list(para = c(1.2, 2.3, -0.8)),
  quawak = list(para = c(1.2, 2.3, 0.25, 0.8, -0.15)),
  quawei = list(para = c(1.2, 2.3, 1.7))
)
timed <- function(fun, para) {
  fun(f, para)
  z <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time(); fun(f, para); z[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
  }
  median(z)
}
values <- file(file.path(out, "quantile_r_values.txt"), "w")
timings <- file(file.path(out, "quantile_r_timings.txt"), "w")
for (name in names(cases)) {
  fun <- get(name, asNamespace("lmom"))
  para <- cases[[name]]$para
  writeLines(paste(c(name, sprintf("%.17g", fun(f, para))), collapse = " "), values)
  writeLines(sprintf("%s %.17g", name, timed(fun, para)), timings)
}
close(values); close(timings)
