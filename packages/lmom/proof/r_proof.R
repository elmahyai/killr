# Proof, R side: reference L-moment values and timings from lmom 3.3.
#
# Reads fixed_samples.csv and cases.csv (shared with python_proof.py) and
# writes docs/output/r_values.csv and docs/output/r_timings.csv.
#
# Run: Rscript packages/lmom/proof/r_proof.R
# The lmom 3.3 install is taken from LMOM_R_LIB (default ~/.cache/killr/Rlib-lmom-3.3).

script_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
here <- dirname(normalizePath(sub("^--file=", "", script_arg)))
out_dir <- normalizePath(file.path(here, "..", "docs", "output"), mustWork = FALSE)
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

lib <- Sys.getenv("LMOM_R_LIB",
  unset = file.path(Sys.getenv("HOME"), ".cache", "killr", "Rlib-lmom-3.3"))
suppressPackageStartupMessages(library(lmom, lib.loc = lib))
stopifnot(as.character(packageVersion("lmom", lib.loc = lib)) == "3.3")

samples <- read.csv(file.path(here, "fixed_samples.csv"), stringsAsFactors = FALSE)
sample_list <- split(samples$x, samples$sample)
cases <- read.csv(file.path(here, "cases.csv"), stringsAsFactors = FALSE)

parse_numbers <- function(s) as.numeric(strsplit(trimws(s), "\\s+")[[1]])

# Calls the lmom 3.3 kernel wrappers (the same .Fortran entry points that
# the exported R functions use). Returns the values and the IFAIL code.
run_case <- function(routine, args, nmom) {
  if (routine == "samlm" || routine == "samlm_ratio") {
    ratios <- routine == "samlm_ratio"
    x <- sample_list[[args]]
    vals <- samlmu(x, nmom = nmom, sort.data = TRUE, ratios = ratios)
    return(list(values = as.numeric(vals), ifail = 0L))
  }
  key <- sub("^(lmr|pel)_", "", routine)
  if (startsWith(routine, "lmr_")) {
    res <- suppressWarnings(lmom:::lmrxxx(key, parse_numbers(args), as.integer(nmom)))
    return(list(values = as.numeric(res$lmom), ifail = as.integer(res$ifail)))
  }
  if (startsWith(routine, "pel_")) {
    res <- suppressWarnings(lmom:::pelxxx(key, parse_numbers(args)))
    return(list(values = as.numeric(res$para), ifail = as.integer(res$ifail)))
  }
  stop("unknown routine: ", routine)
}

median_seconds <- function(fn, reps = 20L) {
  fn()  # one untimed call
  t <- numeric(reps)
  for (k in seq_len(reps)) {
    t0 <- Sys.time()
    fn()
    t[k] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
  }
  median(t)
}

value_rows <- list()
timing_rows <- list()
for (i in seq_len(nrow(cases))) {
  cs <- cases[i, ]
  res <- run_case(cs$routine, cs$args, cs$nmom)
  value_rows[[length(value_rows) + 1]] <- data.frame(
    id = cs$id, index = seq_along(res$values),
    value = sprintf("%.17g", res$values), ifail = res$ifail,
    stringsAsFactors = FALSE)
  med <- median_seconds(function() run_case(cs$routine, cs$args, cs$nmom))
  timing_rows[[length(timing_rows) + 1]] <- data.frame(
    id = cs$id, routine = cs$routine, r_median_seconds = sprintf("%.9e", med),
    stringsAsFactors = FALSE)
}

write.csv(do.call(rbind, value_rows), file.path(out_dir, "r_values.csv"), row.names = FALSE)
write.csv(do.call(rbind, timing_rows), file.path(out_dir, "r_timings.csv"), row.names = FALSE)
cat("R proof: wrote", length(value_rows), "cases to", out_dir, "\n")
