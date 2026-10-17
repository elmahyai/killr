script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
here <- dirname(normalizePath(sub("^--file=", "", script_arg)))
out <- file.path(here, "..", "docs", "output")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
lib <- Sys.getenv("LMOM_R_LIB", unset = file.path(Sys.getenv("HOME"), ".cache", "killr", "Rlib-lmom-3.3"))
suppressPackageStartupMessages(library(lmom, lib.loc = lib))
cases <- read.csv(file.path(here, "pel_cases.csv"), stringsAsFactors = FALSE,
                  check.names = FALSE)
times <- numeric(nrow(cases))
value_rows <- list()
for (i in seq_len(nrow(cases))) {
  f <- get(cases[["function"]][i], asNamespace("lmom"))
  x <- as.numeric(strsplit(cases$args[i], " ", fixed = TRUE)[[1]])
  value <- as.numeric(f(x))
  value_rows[[i]] <- data.frame(fn = cases[["function"]][i], index = seq_along(value),
                                 value = sprintf("%.17g", value))
  f(x)
  tt <- numeric(20)
  for (k in seq_len(20)) {
    t0 <- Sys.time()
    f(x)
    tt[k] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
  }
  times[i] <- median(tt)
}
write.table(do.call(rbind, value_rows), file.path(out, "pel_r_values.txt"),
            row.names = FALSE, quote = FALSE)
write.table(data.frame(fn = cases[["function"]], r_seconds = times),
            file.path(out, "pel_r_timings.txt"), row.names = FALSE, quote = FALSE)
