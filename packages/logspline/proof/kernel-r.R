# Proof for crates/logspline: the R .C entry points of logspline 2.1.22 on a
# fixed sample. Run from the repository root:
#   Rscript packages/logspline/proof/kernel-r.R
# It writes docs/output/kernel-r.csv (outputs of one untimed pass) and
# docs/output/kernel-r-timing.csv (20 timed passes, Sys.time()).
# kernel-py.py reads both files and writes the comparison.

library(logspline)

out_dir <- "packages/logspline/docs/output"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# Fixed sample: integer arithmetic, then one division, so R and Python agree bit for bit.
n <- 200L
i <- seq_len(n)
x <- ((i * i * 37) %% 997) / 100 + i / 50   # unsorted, as oldlogspline sees it
xs <- sort(x)                              # sorted, as logspline() passes it
nu <- length(unique(x))

# Grids for rpqlsd (fixed).
q <- (0:99) * 0.14                         # density evaluation points
p <- (1:99) / 100                          # quantile levels

lc_names <- c("delete", "iautoknot", "sample", "nsample", "bd", "SorC", "nk",
              "kt", "cf", "penalty", "wk", "wk2", "logl")

# nlogcensor fit, with the padding and intpars logspline() uses.
nlfit <- function(maxp, ilow, low, iupp, upp) {
  .C("nlogcensor",
     ip = as.integer(c(n, 0, 0, 0, 1 - ilow, 1 - iupp, -1)),
     coef = as.double(c(xs, rep(0, maxp))),
     dp = as.double(c(-1, low, upp)),
     logl = as.double(rep(0, maxp)),
     ad = as.integer(rep(0, maxp)),
     kts = as.double(rep(0, maxp)),
     PACKAGE = "logspline")
}

# rpqlsd on the fit, with the arguments logspline() builds.
rpq <- function(z, ilow, low, iupp, upp) {
  nk <- z$ip[2]
  coef <- z$coef[1:(nk + 2)]               # c(coef.pol, coef.kts)
  knots <- z$kts[1:nk]
  bnd <- c(ilow, low, iupp, upp)
  dens <- .C("rpqlsd", as.double(coef), as.double(knots), as.double(bnd),
             as.integer(1), pp = as.double(q),
             as.integer(length(knots)), as.integer(length(q)),
             PACKAGE = "logspline")
  quant <- .C("rpqlsd", as.double(coef), as.double(knots), as.double(bnd),
              as.integer(0), pp = as.double(p),
              as.integer(length(knots)), as.integer(length(p)),
              PACKAGE = "logspline")
  list(density = list(pq = dens$pp), quantile = list(pq = quant$pp))
}

pipeline <- function() {
  # oldlogspline: uncensored sample only, delete = TRUE, automatic knots
  nsample <- c(n, n, 0, 0, 0, nu - 1)
  n1 <- 4 * n^0.2 + 1
  knots <- rep(0, 50)
  sorc <- rep(0L, 35)
  sorc[1] <- 1L
  sorc[17] <- 0L
  lc <- .C("logcensor",
           as.integer(c(1, 0, 0, 0, 0)),
           as.integer(c(1, 0, 0, 0, 0)),
           as.double(c(x, 0, 0, 0, 0)),
           as.integer(c(nsample, 0, 0, 0, 0)),
           bd = as.double(c(1, 0, 0, 0, 0)),
           SorC = as.integer(c(sorc, 0, 0, 0, 0)),
           nk = as.integer(0),
           kt = as.double(c(knots, 0, 0, 0, 0)),
           cf = as.double(c(knots, 0, 0, 0, 0)),
           as.double(c(log(n), 0, 0, 0, 0)),
           as.double(c(x, 0, 0, 0, 0)),
           as.double(c(x, 0, 0, 0, 0)),
           logl = as.double(rep(0, n1 + 1 + 10)),
           PACKAGE = "logspline")
  names(lc) <- lc_names

  # new logspline: maximal dimension, then the fit, unbounded and bounded
  nx <- .C("nlogcensorx", z = as.integer(c(-100, rep(0, 9))), PACKAGE = "logspline")
  maxp <- nx$z[1]
  fitA <- nlfit(maxp, 0, 0, 0, 0)
  rA <- rpq(fitA, 0, 0, 0, 0)
  fitB <- nlfit(maxp, 1, -0.5, 1, 15)
  rB <- rpq(fitB, 1, -0.5, 1, 15)

  list(logcensor = lc,
       nlogcensorx = nx,
       nlogcensor_unbounded = fitA,
       rpqlsd_unbounded_density = rA$density,
       rpqlsd_unbounded_quantile = rA$quantile,
       nlogcensor_bounded = fitB,
       rpqlsd_bounded_density = rB$density,
       rpqlsd_bounded_quantile = rB$quantile)
}

# One untimed pass gives the outputs.
res <- pipeline()

rows <- character(0)
for (label in names(res)) {
  z <- res[[label]]
  nm <- names(z)
  for (k in seq_along(z)) {
    v <- as.double(unlist(z[[k]]))
    rows <- c(rows, sprintf("%s,%s,%d,%.17g", label, nm[k], seq_along(v) - 1L, v))
  }
}
writeLines(c("label,name,index,value", rows), file.path(out_dir, "kernel-r.csv"))

# Twenty timed passes with Sys.time().
ms <- numeric(20)
for (r in 1:20) {
  t0 <- Sys.time()
  invisible(pipeline())
  t1 <- Sys.time()
  ms[r] <- as.numeric(difftime(t1, t0, units = "secs")) * 1000
}
writeLines(c("run,ms", sprintf("%d,%.6f", 1:20, ms)),
           file.path(out_dir, "kernel-r-timing.csv"))
cat("R pipeline median ms:", median(ms), "\n")
cat("rows written:", length(rows), "\n")
