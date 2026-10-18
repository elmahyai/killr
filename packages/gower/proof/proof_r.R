# R reference for the gower crate proof. Runs the installed gower 1.0.2 on
# the fixed inputs written by make_inputs.py.
#
# Run from the repository root:
#   GOWER_R_LIB=/tmp/gower_rlib Rscript packages/gower/proof/proof_r.R
# where /tmp/gower_rlib holds gower 1.0.2
# (R CMD INSTALL -l /tmp/gower_rlib rcran/contrib/gower_1.0.2.tar.gz).

lib_loc <- Sys.getenv("GOWER_R_LIB", unset = "")
if (nzchar(lib_loc)) {
  suppressPackageStartupMessages(library(gower, lib.loc = lib_loc))
} else {
  suppressPackageStartupMessages(library(gower))
}
stopifnot(as.character(packageVersion("gower")) == "1.0.2")

data_dir <- "packages/gower/proof/data"
out_dir <- "packages/gower/docs/output"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# Column classes: x1..x8 and y1..y7. The factor columns are read as text and
# converted below.
x_classes <- c("numeric", "integer", "logical", "character",
               "character", "numeric", "integer", "numeric")
y_classes <- c("numeric", "integer", "logical", "character",
               "character", "numeric", "integer")
read_frame <- function(path, classes) {
  read.csv(path, colClasses = classes, na.strings = "NA",
           stringsAsFactors = FALSE)
}

levels_4 <- c("a", "b", "c", "d")
x0 <- read_frame(file.path(data_dir, "x.csv"), x_classes)
y0 <- read_frame(file.path(data_dir, "y.csv"), y_classes)
x0$x4 <- factor(x0$x4, levels = levels_4)
y0$y4 <- factor(y0$y4, levels = levels_4)

# Explicit pairing, as gower_dist(pair_x=, pair_y=). A 0 in pair_y skips the column.
pair_x <- 1:8
pair_y <- c(2, 1, 3, 4, 5, 6, 7, 0)
weights <- c(1, 2, 0.5, 1.5, 1, 3, 0.25, 1)
eps <- 1e-8
n_top <- 5L
n_reps <- 20L

# Top-n needs a fresh copy of x for every call. gower 1.0.2 writes into the
# caller's character column (see the report), so a reused x would change between calls.
x_copy <- function() {
  z <- x0
  z$x5 <- x0$x5[seq_along(x0$x5)]
  z
}

run_dist <- function(x) {
  gower_dist(x, y0, pair_x = pair_x, pair_y = pair_y, eps = eps,
             weights = weights, nthread = 1L)
}
run_topn <- function(x) {
  gower_topn(x, y0, pair_x = pair_x, pair_y = pair_y, n = n_top, eps = eps,
             weights = weights, nthread = 1L)
}

time_median <- function(fun, make_arg) {
  fun(make_arg(1))  # one untimed call
  secs <- numeric(n_reps)
  for (k in seq_len(n_reps)) {
    arg <- make_arg(k + 1)
    t0 <- Sys.time()
    fun(arg)
    t1 <- Sys.time()
    secs[k] <- as.numeric(difftime(t1, t0, units = "secs"))
  }
  list(median = median(secs), all = secs)
}

# Build the argument copies up front so copying is outside the timed calls.
xs <- lapply(seq_len(n_reps + 1), function(k) x_copy())

dist_val <- run_dist(x0)
x5_before <- x0$x5
topn_val <- run_topn(xs[[1]])
# gower 1.0.2 overwrites x5 in the topn argument it is given.
copy_x5_changed <- !identical(xs[[1]]$x5, x5_before)
stopifnot(identical(x0$x5, x5_before))  # the original data is not touched

t_dist <- time_median(run_dist, function(k) x0)
t_topn <- time_median(run_topn, function(k) xs[[k]])

fmt <- function(v) sprintf("%.17g", v)
writeLines(fmt(as.vector(dist_val)), file.path(data_dir, "r_dist.txt"))
writeLines(apply(topn_val$index, 1, function(r) paste(r, collapse = " ")),
           file.path(data_dir, "r_topn_index.txt"))
writeLines(apply(topn_val$distance, 1, function(r) paste(fmt(r), collapse = " ")),
           file.path(data_dir, "r_topn_distance.txt"))
writeLines(c(sprintf("gower_dist %.17g", t_dist$median),
             paste(fmt(t_dist$all), collapse = " "),
             sprintf("gower_topn %.17g", t_topn$median),
             paste(fmt(t_topn$all), collapse = " ")),
           file.path(data_dir, "r_timings.txt"))

summary_lines <- c(
  paste("gower version:", as.character(packageVersion("gower"))),
  paste("R version:", R.version.string),
  sprintf("gower_dist: %d values, median of %d timed calls = %.6f s",
          length(dist_val), n_reps, t_dist$median),
  sprintf("gower_topn: %d x %d, median of %d timed calls = %.6f s",
          nrow(topn_val$index), ncol(topn_val$index), n_reps, t_topn$median),
  paste("topn overwrote x5 in the argument it was given:", copy_x5_changed),
  paste("original x5 unchanged after the topn copies:", identical(x0$x5, x5_before))
)
writeLines(summary_lines, file.path(out_dir, "r_proof.txt"))
writeLines(summary_lines)
