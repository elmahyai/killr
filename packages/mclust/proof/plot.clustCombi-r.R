suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof_dir, "plot_trace.R"))

write_mat <- function(m, path) {
  m <- as.matrix(m)
  lines <- apply(m, 1, function(r) paste(sprintf("%.17g", r), collapse = "\t"))
  writeLines(lines, path)
}

# Fixtures. The G = 6, two-column pair is the existing clustCombi fixture.
X6 <- as.matrix(read.table(file.path(proof_dir, "clustCombi_data.csv")))
Z6 <- as.matrix(read.table(file.path(proof_dir, "clustCombi_z.csv")))
G6 <- 6

softz <- function(X, centres) {
  d2 <- sapply(seq_len(nrow(centres)), function(k)
    rowSums((X - matrix(centres[k, ], nrow(X), ncol(X), byrow = TRUE))^2))
  e <- exp(-0.5 * (d2 - apply(d2, 1, min)))
  e / rowSums(e)
}
set.seed(31)
X1 <- matrix(c(rnorm(40, -3), rnorm(40, 0), rnorm(40, 3)), 120, 1)
Z1 <- softz(X1, matrix(c(-4, -1, 2, 5), 4, 1))
set.seed(32)
X3 <- matrix(rnorm(150 * 3), 150, 3) + rep(c(0, 2, 4), each = 50)
Z3 <- softz(X3, matrix(c(0, 0, 0, 2, 2, 2, 4, 4, 4, -2, 3, 1), 4, 3, byrow = TRUE))
set.seed(33)
X2 <- matrix(rnorm(80 * 2), 80, 2) + rep(c(-2, 2), each = 40)
Z2 <- softz(X2, matrix(c(-2, -2, 2, 2), 2, 2, byrow = TRUE))
write_mat(X1, file.path(proof_dir, "plot.clustCombi_d1_data.csv"))
write_mat(Z1, file.path(proof_dir, "plot.clustCombi_d1_z.csv"))
write_mat(X3, file.path(proof_dir, "plot.clustCombi_d3_data.csv"))
write_mat(Z3, file.path(proof_dir, "plot.clustCombi_d3_z.csv"))
write_mat(X2, file.path(proof_dir, "plot.clustCombi_d2g2_data.csv"))
write_mat(Z2, file.path(proof_dir, "plot.clustCombi_d2g2_z.csv"))

mk <- function(X, Z, G) { m <- list(data = X, z = Z, G = G); class(m) <- "Mclust"; m }
cc6 <- clustCombi(mk(X6, Z6, G6))
cc1 <- clustCombi(mk(X1, Z1, 4))
cc3 <- clustCombi(mk(X3, Z3, 4))
cc2 <- clustCombi(mk(X2, Z2, 2))

# ---- plot.clustCombi (all three plots) --------------------------------------
pc_cases <- list(
  G6_p2 = cc6,
  G4_p1 = cc1,
  G4_p3 = cc3,
  G2_p2 = cc2
)
pc_out <- character(0)
pdf(NULL)
for (nm in names(pc_cases)) {
  trace_start()
  plot.clustCombi(pc_cases[[nm]])
  trace_stop()
  pc_out <- c(pc_out, paste0("#CASE\t", nm), .LOG$out)
}
writeLines(pc_out, file.path(proof_dir, "plot.clustCombi-r-log.txt"))

# ---- entPlot ----------------------------------------------------------------
ent_cases <- list(
  G6_default = list(z = Z6, combiM = cc6$combiM),
  G6_reg3 = list(z = Z6, combiM = cc6$combiM, reg = 3)
)
ent_out <- character(0)
for (nm in names(ent_cases)) {
  a <- ent_cases[[nm]]
  trace_start()
  if (is.null(a$reg)) entPlot(z = a$z, combiM = a$combiM) else entPlot(z = a$z, combiM = a$combiM, reg = a$reg)
  trace_stop()
  ent_out <- c(ent_out, paste0("#CASE\t", nm), .LOG$out)
}
writeLines(ent_out, file.path(proof_dir, "entPlot-r-log.txt"))

# ---- combiPlot --------------------------------------------------------------
cp_cases <- list(
  G6_p2_merge24 = list(X = X6, z = Z6, combiM = combMat(6, 2, 4)),
  G4_p3_identity = list(X = X3, z = Z3, combiM = diag(4)),
  G4_p1_merge13 = list(X = X1, z = Z1, combiM = combMat(4, 1, 3))
)
cp_out <- character(0)
for (nm in names(cp_cases)) {
  a <- cp_cases[[nm]]
  trace_start()
  combiPlot(data = a$X, z = a$z, combiM = a$combiM)
  trace_stop()
  cp_out <- c(cp_out, paste0("#CASE\t", nm), .LOG$out)
}
dev.off()
writeLines(cp_out, file.path(proof_dir, "combiPlot-r-log.txt"))

# ---- timing: the data computation only (no device) --------------------------
# plot.clustCombi: the classification sequence (permutation, then each
# K-cluster map), the entropy and merge counts with the segmented fits for both
# entPlot panels, and the combiTree data (merge, heights, as.dendrogram).
clust_combi_data <- function(object) {
  G <- object$MclustOutput$G
  z <- object$MclustOutput$z
  combiM <- object$combiM
  curr <- 1:G
  i <- numeric()
  j <- numeric()
  for (K in G:2) {
    l1 <- which(!combiM[[K - 1]] %*% rep(1, K) == 1)
    l2 <- (combiM[[K - 1]] %*% curr)[l1] - curr[l1]
    i <- c(curr[l1], i)
    j <- c(l2, j)
    curr <- combiM[[K - 1]] %*% curr - l2 * c(rep(0, (l1 - 1)), 1, rep(0, (K - 1 - l1)))
  }
  permutz <- z[, c(1, j)]
  cm <- diag(G)
  i <- c(0, i)
  j <- c(1, j)
  cls <- vector("list", G)
  for (K in G:1) {
    cls[[K]] <- map(t(cm %*% t(permutz)))
    cm <- combMat(K, which(j == i[K]), K) %*% cm
  }
  ent_data_out <- ent_data(z, combiM, reg = 2)
  # combiTree data
  curr <- 1:G
  merged <- -(1:G)
  merge <- matrix(NA, G - 1, 2)
  for (k in 1:(G - 1)) {
    Kp <- G - k + 1
    l1 <- which(!combiM[[Kp - 1]] %*% rep(1, Kp) == 1)
    l2 <- (combiM[[Kp - 1]] %*% curr)[l1] - curr[l1]
    curr <- setdiff(curr, max(l1, l2))
    merge[k, ] <- merged[c(l1, l2)]
    merged[merged == merged[l1] | merged == merged[l2]] <- k
  }
  entropy <- sapply(rev(object$combiz), function(z) -sum(mclust:::xlog(z)))
  h <- entropy
  h <- 1 - (h - min(h)) / (max(h) - min(h))
  h <- h[-1]
  hc <- list(merge = merge, height = h, order = NULL, labels = 1:G)
  class(hc) <- "hclust"
  dendro <- as.dendrogram(hc, check = FALSE)
  list(cls = cls, ent = ent_data_out, dendro = dendro)
}

ent_data <- function(z, combiM, reg = 2) {
  Kmax <- ncol(z)
  ent <- numeric()
  z0 <- z
  for (K in Kmax:1) {
    z0 <- t(combiM[[K]] %*% t(z0))
    ent[K] <- -sum(mclust:::xlog(z0))
  }
  mergedn <- numeric()
  z0 <- z
  for (K in (Kmax - 1):1) {
    z0 <- t(combiM[[K + 1]] %*% t(z0))
    mergedn[K] <- sum(sapply(map(z0), function(x)
      any(which(as.logical(combiM[[K]][rowSums(combiM[[K]]) == 2, ])) == x)))
  }
  if (Kmax == 2) reg <- NULL
  fits <- list()
  if (any(reg == 2)) fits$s2 <- mclust:::pcws2_reg(1:Kmax, ent)
  if (any(reg == 3)) fits$s3 <- mclust:::pcws3_reg(1:Kmax, ent)
  X <- cumsum(c(0, mergedn))
  if (any(reg == 2)) fits$n2 <- mclust:::pcws2_reg(X, ent)
  if (any(reg == 3)) fits$n3 <- mclust:::pcws3_reg(X, ent)
  list(ent = ent, mergedn = mergedn, fits = fits)
}

time_median <- function(fn) {
  invisible(fn())
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    fn()
    elapsed[i] <- as.numeric(Sys.time()) - t0
  }
  median(elapsed) * 1000
}

writeLines(sprintf("%.17g", time_median(function() clust_combi_data(cc6))),
           file.path(proof_dir, "plot.clustCombi-r-ms.txt"))
writeLines(sprintf("%.17g", time_median(function() ent_data(Z6, cc6$combiM, reg = 2))),
           file.path(proof_dir, "entPlot-r-ms.txt"))
writeLines(sprintf("%.17g", time_median(function() map(t(combMat(6, 2, 4) %*% t(Z6))))),
           file.path(proof_dir, "combiPlot-r-ms.txt"))
cat("ok\n")
