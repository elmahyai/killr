# Fixed parameters for the sim proofs (mclust 6.1.3). The same literal numbers are
# in sim_fixtures.py. A matrix's columns are the components.
sim_mu <- matrix(c(0, 2, -1, 1, 0.5, 1.5, -1, -0.5, 0.25), 3, 3)
sim_pro <- c(0.2, 0.3, 0.5)
sim_O1 <- matrix(c(0.6, 0.8, 0, -0.64, 0.48, -0.6, -0.48, 0.36, 0.8), 3, 3)
sim_O2 <- matrix(c(0, 1, 0, 0, 0, 1, 1, 0, 0), 3, 3)
sim_O3 <- matrix(c(1, 0, 0, 0, 0.6, -0.8, 0, 0.8, 0.6), 3, 3)
sim_Oarr <- array(c(sim_O1, sim_O2, sim_O3), c(3, 3, 3))
sim_shape_d <- c(1.0, 2.0, 0.5)
sim_scale_g <- c(0.5, 1.5, 0.8)
sim_shape_dg <- matrix(c(1, 2, 0.5, 1.5, 1, 2, 0.8, 0.6, 1.2), 3, 3)
sim_scale_1 <- 1.4
sim_sigma <- array(c(2, 0.3, 0.1, 0.3, 1.5, -0.2, 0.1, -0.2, 1,
                     1, 0, 0, 0, 2, 0.5, 0, 0.5, 1.2,
                     0.7, -0.1, 0.05, -0.1, 0.9, 0.2, 0.05, 0.2, 1.5), c(3, 3, 3))
sim_sigmasq <- c(0.5, 1.5, 0.8)

# The parameter list for one model. use_chol = TRUE gives VVV its cholsigma path.
sim_params <- function(model, use_chol = FALSE) {
  var <- switch(model,
    VEV = list(shape = sim_shape_d, scale = sim_scale_g, orientation = sim_Oarr),
    VII = list(sigmasq = sim_sigmasq),
    VVI = list(shape = sim_shape_dg, scale = sim_scale_g),
    VVV = if (use_chol) {
            list(cholsigma = array(apply(sim_sigma, 3, chol), c(3, 3, 3)))
          } else {
            list(sigma = sim_sigma)
          },
    EVV = list(shape = sim_shape_dg, scale = sim_scale_1, orientation = sim_Oarr),
    VEE = list(shape = sim_shape_d, scale = sim_scale_g, orientation = sim_O1),
    EVE = list(shape = sim_shape_dg, scale = sim_scale_1, orientation = sim_O1),
    VVE = list(shape = sim_shape_dg, scale = sim_scale_g, orientation = sim_O1))
  list(pro = sim_pro, mean = sim_mu, variance = var)
}

# The same parameters with the mean missing (the R missing-parameter branch).
sim_params_missing <- function(model) {
  p <- sim_params(model)
  p$mean <- NA
  p
}
