# Proof: R mclust::simVVV (mclust 6.1.3), model VVV, against the Python port.
# Run from packages/mclust:  Rscript proof/simVVV-r.R
suppressMessages(library(mclust))
stopifnot(as.character(packageVersion("mclust")) == "6.1.3")
source("proof/sim_fixtures.R")
source("proof/sim_proof_common.R")
p <- sim_params("VVV")
pm <- sim_params_missing("VVV")
sim_proof("simVVV", list(
  list(id = "main", run = function() simVVV(p, 500, seed = 20260917)),
  list(id = "small", run = function() simVVV(p, 5, seed = 7)),
  list(id = "odd", run = function() simVVV(p, 37, seed = 123)),
  list(id = "missing", run = function() simVVV(pm, 20, seed = 5)),
  list(id = "chol", run = function() simVVV(sim_params("VVV", use_chol = TRUE), 500, seed = 20260917))
))
