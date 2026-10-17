# Wrapper-level proof, R side: the public gower_dist() and gower_topn() of
# gower 1.0.2 on the fixed inputs written by make_inputs.py.
#
# Run from the repository root:
#   GOWER_R_LIB=/tmp/gower_rlib Rscript packages/gower/proof/wrapper_proof_r.R
# where /tmp/gower_rlib holds gower 1.0.2
# (R CMD INSTALL -l /tmp/gower_rlib cran/contrib/gower_1.0.2.tar.gz).
#
# Writes the values to packages/gower/proof/data/wrapper_r_*.txt. The Python
# side (wrapper_proof_py.py) reads them and compares.
#
# Timing: Sys.time(), one untimed call, then the median of 20 timed calls.
# gower_topn overwrites the character column of the argument it is given
# (gower 1.0.2), so every topn call gets its own pre-built copy of x, made
# outside the timer.

lib_loc <- Sys.getenv("GOWER_R_LIB", unset = "")
if (nzchar(lib_loc)) {
  suppressPackageStartupMessages(library(gower, lib.loc = lib_loc))
} else {
  suppressPackageStartupMessages(library(gower))
}
stopifnot(as.character(packageVersion("gower")) == "1.0.2")

data_dir <- "packages/gower/proof/data"

x_classes <- c("numeric", "integer", "logical", "character",
               "character", "numeric", "integer", "numeric")
y_classes <- c("numeric", "integer", "logical", "character",
               "character", "numeric", "integer")
levels_4 <- c("a", "b", "c", "d")

read_frame <- function(path, classes) {
  read.csv(path, colClasses = classes, na.strings = "NA",
           stringsAsFactors = FALSE)
}
x0 <- read_frame(file.path(data_dir, "x.csv"), x_classes)
y0 <- read_frame(file.path(data_dir, "y.csv"), y_classes)
x0$x4 <- factor(x0$x4, levels = levels_4)
y0$y4 <- factor(y0$y4, levels = levels_4)

# Same pairing as the Python side: pair_x 1:8, pair_y 2 1 3 4 5 6 7 0
# (a 0 skips the column), explicit weights, eps 1e-8, n = 5.
pair_x <- 1:8
pair_y <- c(2, 1, 3, 4, 5, 6, 7, 0)
weights <- c(1, 2, 0.5, 1.5, 1, 3, 0.25, 1)
eps <- 1e-8
n_top <- 5L
n_reps <- 20L

run_dist <- function(x) {
  gower_dist(x, y0, pair_x = pair_x, pair_y = pair_y, eps = eps,
             weights = weights, nthread = 1L)
}
run_topn <- function(x) {
  gower_topn(x, y0, pair_x = pair_x, pair_y = pair_y, n = n_top, eps = eps,
             weights = weights, nthread = 1L)
}

# args: n_reps + 1 pre-built arguments. The first is the untimed call.
time_median <- function(fun, args) {
  fun(args[[1]])
  secs <- numeric(n_reps)
  for (k in seq_len(n_reps)) {
    arg <- args[[k + 1]]
    t0 <- Sys.time()
    fun(arg)
    t1 <- Sys.time()
    secs[k] <- as.numeric(difftime(t1, t0, units = "secs"))
  }
  list(median = median(secs), all = secs)
}

x_copy <- function() {
  z <- x0
  z$x5 <- x0$x5[seq_along(x0$x5)]
  z
}

# Copies: [1] value call, [2] untimed call, [3..22] the 20 timed calls.
topn_copies <- lapply(seq_len(n_reps + 2), function(k) x_copy())
x5_before <- x0$x5

dist_val <- run_dist(x0)
topn_val <- run_topn(topn_copies[[1]])
stopifnot(identical(x0$x5, x5_before))  # the caller's data is not touched

t_dist <- time_median(run_dist, rep(list(x0), n_reps + 1))
t_topn <- time_median(run_topn, topn_copies[-1])

fmt <- function(v) sprintf("%.17g", v)
writeLines(fmt(as.vector(dist_val)), file.path(data_dir, "wrapper_r_dist.txt"))
writeLines(apply(topn_val$index, 1, function(r) paste(r, collapse = " ")),
           file.path(data_dir, "wrapper_r_topn_index.txt"))
writeLines(apply(topn_val$distance, 1, function(r) paste(fmt(r), collapse = " ")),
           file.path(data_dir, "wrapper_r_topn_distance.txt"))
writeLines(c(sprintf("gower_dist %.17g", t_dist$median),
             sprintf("gower_topn %.17g", t_topn$median)),
           file.path(data_dir, "wrapper_r_timings.txt"))

cat("gower version:", as.character(packageVersion("gower")), "\n")
cat("R version:", R.version.string, "\n")
cat(sprintf("R gower_dist: %d values, median of %d timed calls = %.6f s\n",
            length(dist_val), n_reps, t_dist$median))
cat(sprintf("R gower_topn: %d x %d, median of %d timed calls = %.6f s\n",
            nrow(topn_val$index), ncol(topn_val$index), n_reps, t_topn$median))
cat("topn overwrote x5 in its argument (copy 1):",
    !identical(topn_copies[[1]]$x5, x5_before), "\n")
