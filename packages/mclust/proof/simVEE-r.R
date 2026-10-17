# Proof: R mclust::simVEE (mclust 6.1.3), model VEE, against the Python port.
# Run from packages/mclust:  Rscript proof/simVEE-r.R
suppressMessages(library(mclust))
stopifnot(as.character(packageVersion("mclust")) == "6.1.3")
source("proof/sim_fixtures.R")
source("proof/sim_proof_common.R")
p <- sim_params("VEE")
pm <- sim_params_missing("VEE")
sim_proof("simVEE", list(
  list(id = "main", run = function() simVEE(p, 500, seed = 20260917)),
  list(id = "small", run = function() simVEE(p, 5, seed = 7)),
  list(id = "odd", run = function() simVEE(p, 37, seed = 123)),
  list(id = "missing", run = function() simVEE(pm, 20, seed = 5))
))
