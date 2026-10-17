suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

sym <- get("Csurvdiff2", envir = asNamespace("survival"))

call_one <- function(rho, time, status, group, strata, ngroup, nstrat) {
  n <- length(time)
  xx <- .C(
    sym,
    as.integer(n),
    as.integer(ngroup),
    as.integer(nstrat),
    as.double(rho),
    as.double(time),
    as.integer(status),
    as.integer(group),
    as.integer(strata),
    observed = double(ngroup * nstrat),
    expected = double(ngroup * nstrat),
    var = double(ngroup * ngroup),
    double(ngroup),
    double(n)
  )
  c(xx$observed, xx$expected, xx$var)
}

tiny_time <- c(1, 2, 3, 4)
tiny_status <- c(1L, 1L, 0L, 1L)
tiny_group <- c(1L, 2L, 1L, 2L)
tiny_strata <- c(0L, 0L, 0L, 1L)

n1 <- 90L
i1 <- seq_len(n1)
n2 <- 60L
i2 <- seq_len(n2)
large_time <- c(((i1 - 1L) %/% 3L) + 1, ((i2 - 1L) %/% 2L) + 1)
large_status <- c(ifelse(i1 %% 5L == 0L, 0L, 1L), ifelse(i2 %% 4L == 0L, 0L, 1L))
large_group <- c(((i1 - 1L) %% 3L) + 1L, ((i2 - 1L) %% 3L) + 1L)
large_strata <- c(rep(0L, n1 - 1L), 1L, rep(0L, n2 - 1L), 1L)

one <- function() {
  c(
    call_one(0, tiny_time, tiny_status, tiny_group, tiny_strata, 2L, 1L),
    call_one(1, tiny_time, tiny_status, tiny_group, tiny_strata, 2L, 1L),
    call_one(0, large_time, large_status, large_group, large_strata, 3L, 2L),
    call_one(1, large_time, large_status, large_group, large_strata, 3L, 2L),
    call_one(0.5, large_time, large_status, large_group, large_strata, 3L, 2L)
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", value), collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
