# Fixed inputs shared by the cdens proof scripts. The Python twin is cdens_fixtures.py.
# Every value is a closed-form expression, so R and Python build the same numbers.
n <- 60L
p <- 3L
G <- 3L
i1 <- seq_len(n)
x1 <- sin(0.7 * i1) + 0.5 * cos(0.31 * i1 * i1)
X <- outer(seq_len(n), seq_len(p), function(i, j) sin(0.7 * i + 1.3 * j) + 0.5 * cos(0.31 * i * j))
MU <- outer(seq_len(p), seq_len(G), function(j, k) 0.4 * k - 0.25 * j + 0.1 * j * k)
MU1 <- c(-0.5, 0.2, 1.1)
PRO <- c(0.2, 0.3, 0.5)
SHAPE_V <- c(1.0, 1.4, 0.6)
SHAPE_M <- outer(seq_len(p), seq_len(G), function(j, k) 0.5 + 0.3 * j + 0.2 * k)
CHOL <- matrix(c(1.2, 0, 0, 0.3, 0.8, 0, -0.2, 0.4, 1.5), p, p)
Rz <- function(a) matrix(c(cos(a), sin(a), 0, -sin(a), cos(a), 0, 0, 0, 1), 3)
Rx <- function(a) matrix(c(1, 0, 0, 0, cos(a), sin(a), 0, -sin(a), cos(a)), 3)
ORI <- array(0, c(p, p, G))
for (k in seq_len(G)) ORI[, , k] <- Rz(0.2 * k) %*% Rx(0.14 * k)

pars_E <- list(pro = PRO, mean = MU1, variance = list(modelName = "E", sigmasq = 0.8))
pars_E_missing <- pars_E
pars_E_missing$mean[2] <- NA
pars_E_vanish <- list(pro = PRO, mean = MU1, variance = list(modelName = "E", sigmasq = 0))

pars_EII <- list(pro = PRO, mean = MU, variance = list(modelName = "EII", sigmasq = 0.9))
pars_EII_missing <- pars_EII
pars_EII_missing$mean[1, 1] <- NA
pars_EII_vanish <- list(pro = PRO, mean = MU, variance = list(modelName = "EII", sigmasq = 0))

pars_EEI <- list(pro = PRO, mean = MU, variance = list(modelName = "EEI", scale = 0.9, shape = SHAPE_V))
pars_EEI_missing <- pars_EEI
pars_EEI_missing$mean[1, 1] <- NA

pars_EVI <- list(pro = PRO, mean = MU, variance = list(modelName = "EVI", scale = 0.9, shape = SHAPE_M))
pars_EVI_missing <- pars_EVI
pars_EVI_missing$mean[1, 1] <- NA

pars_EEV <- list(pro = PRO, mean = MU, variance = list(modelName = "EEV", scale = 0.9, shape = SHAPE_V, orientation = ORI))
pars_EEV_missing <- pars_EEV
pars_EEV_missing$mean[1, 1] <- NA

pars_EEE <- list(pro = PRO, mean = MU, variance = list(modelName = "EEE", cholSigma = CHOL))
pars_EEE_missing <- pars_EEE
pars_EEE_missing$mean[1, 1] <- NA

# Encode NA as -1e300 so both sides print a number. The return code is printed first.
emit <- function(res) {
  z <- as.vector(res)
  z[is.na(z)] <- -1e300
  c(as.numeric(attr(res, "returnCode")), z)
}

print_values <- function(values) cat(sprintf("%.17g\n", values), sep = "")
