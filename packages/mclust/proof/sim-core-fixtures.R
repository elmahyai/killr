# Fixed parameters shared by the sim proof scripts. The Python twin is sim_fixtures.py.
# Every value is a closed-form expression, so R and Python build the same numbers.
p <- 3L
G <- 3L
PRO <- c(0.2, 0.3, 0.5)
MU1 <- c(-0.5, 0.2, 1.1)
MU <- outer(seq_len(p), seq_len(G), function(j, k) 0.4 * k - 0.25 * j + 0.1 * j * k)
SHAPE_V <- c(1.0, 1.4, 0.6)
SHAPE_M <- outer(seq_len(p), seq_len(G), function(j, k) 0.5 + 0.3 * j + 0.2 * k)
CHOL <- matrix(c(1.2, 0, 0, 0.3, 0.8, 0, -0.2, 0.4, 1.5), p, p)
Rz <- function(a) matrix(c(cos(a), sin(a), 0, -sin(a), cos(a), 0, 0, 0, 1), 3)
Rx <- function(a) matrix(c(1, 0, 0, 0, cos(a), sin(a), 0, -sin(a), cos(a)), 3)
ORI <- array(0, c(p, p, G))
for (k in seq_len(G)) ORI[, , k] <- Rz(0.2 * k) %*% Rx(0.14 * k)

pars_E <- list(pro = PRO, mean = MU1, variance = list(sigmasq = 0.8))
pars_E_nopro <- list(mean = MU1, variance = list(sigmasq = 0.8))
pars_E_zero <- list(pro = PRO, mean = MU1, variance = list(sigmasq = 0))
pars_E_missing <- pars_E
pars_E_missing$mean <- NA_real_

pars_V <- list(pro = PRO, mean = MU1, variance = list(sigmasq = c(0.5, 1.4, 0.9)))
pars_V_nopro <- list(mean = MU1, variance = list(sigmasq = c(0.5, 1.4, 0.9)))
pars_V_zero <- list(pro = PRO, mean = MU1, variance = list(sigmasq = c(0.5, 0, 0.9)))
pars_V_missing <- pars_V
pars_V_missing$mean <- NA_real_

pars_EII <- list(pro = PRO, mean = MU, variance = list(sigmasq = 0.9))
pars_EII_nopro <- list(mean = MU, variance = list(sigmasq = 0.9))
pars_EII_missing <- pars_EII
pars_EII_missing$mean <- NA_real_

pars_EEI <- list(pro = PRO, mean = MU, variance = list(scale = 0.9, shape = SHAPE_V))
pars_EEI_nopro <- list(mean = MU, variance = list(scale = 0.9, shape = SHAPE_V))
pars_EEI_missing <- pars_EEI
pars_EEI_missing$mean <- NA_real_

pars_EEV <- list(pro = PRO, mean = MU, variance = list(scale = 0.9, shape = SHAPE_V, orientation = ORI))
pars_EEV_nopro <- list(mean = MU, variance = list(scale = 0.9, shape = SHAPE_V, orientation = ORI))
pars_EEV_missing <- pars_EEV
pars_EEV_missing$mean <- NA_real_

pars_EEE <- list(pro = PRO, mean = MU, variance = list(cholSigma = CHOL))
pars_EEE_nopro <- list(mean = MU, variance = list(cholSigma = CHOL))
pars_EEE_sigma <- list(pro = PRO, mean = MU, variance = list(Sigma = crossprod(CHOL)))
pars_EEE_missing <- pars_EEE
pars_EEE_missing$mean <- NA_real_

# scale has one entry per component, which R recycles along the column-major order of shape.
pars_EVI <- list(pro = PRO, mean = MU, variance = list(scale = c(0.9, 1.1, 0.7), shape = SHAPE_M))
pars_EVI_nopro <- list(mean = MU, variance = list(scale = c(0.9, 1.1, 0.7), shape = SHAPE_M))
pars_EVI_missing <- pars_EVI
pars_EVI_missing$mean <- NA_real_

pars_VEI <- list(pro = PRO, mean = MU, variance = list(scale = c(0.9, 1.3, 0.6), shape = SHAPE_V))
pars_VEI_nopro <- list(mean = MU, variance = list(scale = c(0.9, 1.3, 0.6), shape = SHAPE_V))
pars_VEI_missing <- pars_VEI
pars_VEI_missing$mean <- NA_real_

# Encode NA as -1e300 so both sides print a number. The dimensions come first, then the values.
emit <- function(res) {
  z <- as.vector(res)
  z[is.na(z)] <- -1e300
  c(dim(res), z)
}

print_values <- function(values) cat(sprintf("%.17g\n", values), sep = "")
