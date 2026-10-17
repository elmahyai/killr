suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "plot_trace.R"))
source(file.path(proof_dir, "MclustDR-export.R"))
dr <- MclustDR(mod, lambda = 0.7)

cases <- list(
  scatterplot    = list(what = "scatterplot"),
  pairs          = list(what = "pairs"),
  contour        = list(what = "contour"),
  classification = list(what = "classification"),
  boundaries     = list(what = "boundaries"),
  density_dim1   = list(what = "density", dimens = 1),
  evalues        = list(what = "evalues"),
  scatter_dims23 = list(what = "scatterplot", dimens = c(2, 3)),
  default_all    = list()
)

out <- character(0)
pdf(NULL)
for (nm in names(cases)) {
  args <- c(list(x = dr), cases[[nm]])
  trace_start()
  do.call(plot.MclustDR, args)
  trace_stop()
  out <- c(out, paste0("#CASE\t", nm), .LOG$out)
}
dev.off()
writeLines(out, file.path(proof_dir, "plot.MclustDR-r-log.txt"))
cat("cases", length(cases), "\n")

# Timing: the data computation of the default plot, with no drawing. It repeats
# the grids plot.MclustDR fills: predict2D for the classification and boundary
# grids, the per-class contour densities through surfacePlot's own internals
# (cdensVVV, logsumexp, grid1, grid2), the density curves, and plotEvalues.
compute_default <- function(dr) {
  ngrid <- 200
  dir2 <- dr$dir[, 1:2, drop = FALSE]
  xl <- extendrange(dir2[, 1], f = 0.05)
  yl <- extendrange(dir2[, 2], f = 0.05)
  p1 <- predict2D.MclustDR(dr, dim = 1:2, ngrid = ngrid, xlim = xl, ylim = yl)
  p2 <- predict2D.MclustDR(dr, dim = 1:2, ngrid = ngrid, xlim = xl, ylim = yl)
  p2$uncertainty[c(1, ngrid), ] <- NA
  p2$uncertainty[, c(1, ngrid)] <- NA
  dx <- range(dir2[, 1]); dy <- range(dir2[, 2])
  usr_x <- dx + c(-1, 1) * 0.04 * diff(dx)
  usr_y <- dy + c(-1, 1) * 0.04 * diff(dy)
  par2 <- projpar.MclustDR(dr, 1:2)
  nclass <- length(table(as.numeric(as.factor(dr$mixcomp))))
  for (k in 1:nclass) {
    i <- which(dr$class2mixcomp == k)
    parameters <- list(pro = dr$pro[i] / sum(dr$pro[i]),
                       mean = t(par2$mean[i, , drop = FALSE]),
                       variance = list(G = length(i), d = 2,
                                       sigma = par2$variance[, , i, drop = FALSE]))
    parameters$variance$cholsigma <- parameters$variance$sigma
    for (g in seq_along(i)) parameters$variance$cholsigma[, , g] <- chol(parameters$variance$sigma[, , g])
    x <- mclust:::grid1(n = ngrid, range = usr_x, edge = TRUE)
    y <- mclust:::grid1(n = ngrid, range = usr_y, edge = TRUE)
    xy <- mclust:::grid2(x, y)
    cden <- mclust:::cdensVVV(data = xy, parameters = parameters, logarithm = TRUE)
    logden <- mclust:::logsumexp(cden, log(parameters$pro))
    zz <- matrix(exp(logden), ngrid, ngrid)
    lv <- pretty(zz, 5)
  }
  dd <- extendrange(dir2[, 1], f = 0.1)
  xgrid <- seq(min(dd), max(dd), length = 2 * ngrid)
  parD <- projpar.MclustDR(dr, 1)
  dens <- matrix(0, length(xgrid), dr$G)
  for (j in 1:dr$G) dens[, j] <- dnorm(xgrid, parD$mean[j, ], sqrt(parD$variance[, , j]))
  ev <- plotEvalues.MclustDR(dr, plot = FALSE)
  invisible(NULL)
}
one_default <- function() compute_default(dr)
elapsed_default <- numeric(20)
one_default()
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one_default()
  elapsed_default[i] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed_default) * 1000),
           file.path(proof_dir, "plot.MclustDR-r-ms.txt"))
