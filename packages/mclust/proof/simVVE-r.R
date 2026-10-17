# Proof: R mclust::simVVE (mclust 6.1.3), model VVE, against the Python port.
# Run from packages/mclust:  Rscript proof/simVVE-r.R
suppressMessages(library(mclust))
stopifnot(as.character(packageVersion("mclust")) == "6.1.3")
source("proof/sim_fixtures.R")
source("proof/sim_proof_common.R")
p <- sim_params("VVE")
pm <- sim_params_missing("VVE")
sim_proof("simVVE", list(
  list(id = "main", run = function() simVVE(p, 500, seed = 20260917)),
  list(id = "small", run = function() simVVE(p, 5, seed = 7)),
  list(id = "odd", run = function() simVVE(p, 37, seed = 123)),
  list(id = "missing", run = function() simVVE(pm, 20, seed = 5))
))
