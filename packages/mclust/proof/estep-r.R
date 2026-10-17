.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
X <- matrix(c(0.1, 1.2, -0.4, 2.9, 3.3, 2.2, 0.7, 4.1, 1.5, 3.8, -1.0, 2.0, 0.3, 2.7, 1.9, 3.1), nrow = 8)
X1 <- X[, 1]
MU <- matrix(c(0.5, 0.2, 3.0, 2.5), nrow = 2)
MU1 <- c(0.5, 3.0)
S <- matrix(c(1.2, 0.3, 0.3, 0.9), nrow = 2)
ROT <- function(th) matrix(c(cos(th), sin(th), -sin(th), cos(th)), nrow = 2)
O2 <- array(0, c(2, 2, 2))
O2[, , 1] <- ROT(0.3)
O2[, , 2] <- ROT(-0.5)
U <- array(0, c(2, 2, 2))
for (g in 1:2) {
  M <- diag(c(1.0, 0.8) + 0.1 * g)
  M[1, 2] <- 0.3 * g
  U[, , g] <- M
}
SH <- matrix(c(1.0, 1.5, 2.0, 0.8), nrow = 2)
SH2 <- matrix(c(1.5, 0.6, 0.8, 1.4), nrow = 2)

pars_for <- function(model, pro) {
  mean <- if (model %in% c("E", "V")) MU1 else MU
  variance <- switch(model,
    E = list(modelName = "E", sigmasq = 1.5),
    V = list(modelName = "V", sigmasq = c(1.5, 0.8)),
    EII = list(modelName = "EII", sigmasq = 1.1),
    VII = list(modelName = "VII", sigmasq = c(1.1, 0.7)),
    EEI = list(modelName = "EEI", scale = 0.8, shape = c(1.0, 2.0)),
    VEI = list(modelName = "VEI", scale = c(0.6, 1.4), shape = c(1.5, 0.7)),
    EVI = list(modelName = "EVI", scale = 0.9, shape = SH),
    VVI = list(modelName = "VVI", scale = c(0.6, 1.4), shape = SH),
    EEE = list(modelName = "EEE", cholSigma = chol(S)),
    EVE = list(modelName = "EVE", scale = 0.9, shape = SH2, orientation = ROT(0.3)),
    VEE = list(modelName = "VEE", scale = c(1.3, 0.7), shape = c(1.5, 0.6), orientation = ROT(0.3)),
    VVE = list(modelName = "VVE", scale = c(1.3, 0.7), shape = SH2, orientation = ROT(0.3)),
    EEV = list(modelName = "EEV", scale = 0.9, shape = c(1.0, 1.7), orientation = O2),
    VEV = list(modelName = "VEV", scale = c(0.6, 1.4), shape = c(1.5, 0.7), orientation = O2),
    EVV = list(modelName = "EVV", scale = 0.9, shape = SH2, orientation = O2),
    VVV = list(modelName = "VVV", cholsigma = U))
  list(pro = pro, mean = mean, variance = variance)
}

run <- function(model, dat, pro) mclust:::estep(dat, model, pars_for(model, pro))
emit <- function(res) c(res$loglik, attr(res, "returnCode"), as.vector(res$z))
models <- c("E", "V", "EII", "VII", "EEI", "VEI", "EVI", "VVI",
            "EEE", "EVE", "VEE", "VVE", "EEV", "VEV", "EVV", "VVV")
pros <- list(c(0.4, 0.6), c(0.3, 0.5, 0.2))
one <- function() {
  out <- list()
  for (m in models) {
    dat <- if (m %in% c("E", "V")) X1 else X
    for (pro in pros) out[[length(out) + 1]] <- run(m, dat, pro)
  }
  out
}
value <- one()
cat(sprintf("%.17g\n", unlist(lapply(value, emit))), sep = "")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", median(elapsed) * 1000))
