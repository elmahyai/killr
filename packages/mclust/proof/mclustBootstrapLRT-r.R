.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

# The same data as the Python proof: set.seed(42), then two clusters of 15 points.
make_data <- function() {
  set.seed(42)
  rbind(
    cbind(rnorm(15, 0, 1), rnorm(15, 0, 1)),
    cbind(rnorm(15, 3, 1), rnorm(15, 3, 1))
  )
}

record <- function(out) {
  c(as.numeric(out$G), out$obs, out$p.value, as.numeric(out$boot))
}

# The default call: only modelName is given; nboot = 999, level = 0.05, maxG = NULL.
one <- function() {
  record(mclustBootstrapLRT(make_data(), modelName = "EEE"))
}

# A second call with fewer replications and maxG = 2, compared but not timed.
small <- function() {
  record(mclustBootstrapLRT(make_data(), modelName = "EEE",
                            nboot = 15, maxG = 2, verbose = FALSE))
}

# First value is the length of the default-call record, so the two cases can be split.
default_part <- one()
value <- c(length(default_part), default_part, small())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
