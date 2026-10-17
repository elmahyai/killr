# Proof: R mclust::simVEV (mclust 6.1.3), model VEV, against the Python port.
# Run from packages/mclust:  Rscript proof/simVEV-r.R
suppressMessages(library(mclust))
stopifnot(as.character(packageVersion("mclust")) == "6.1.3")
source("proof/sim_fixtures.R")
source("proof/sim_proof_common.R")
p <- sim_params("VEV")
pm <- sim_params_missing("VEV")
sim_proof("simVEV", list(
  list(id = "main", run = function() simVEV(p, 500, seed = 20260917)),
  list(id = "small", run = function() simVEV(p, 5, seed = 7)),
  list(id = "odd", run = function() simVEV(p, 37, seed = 123)),
  list(id = "missing", run = function() simVEV(pm, 20, seed = 5))
))
