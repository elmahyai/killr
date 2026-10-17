# Proof: R mclust::simEVE (mclust 6.1.3), model EVE, against the Python port.
# Run from packages/mclust:  Rscript proof/simEVE-r.R
suppressMessages(library(mclust))
stopifnot(as.character(packageVersion("mclust")) == "6.1.3")
source("proof/sim_fixtures.R")
source("proof/sim_proof_common.R")
p <- sim_params("EVE")
pm <- sim_params_missing("EVE")
sim_proof("simEVE", list(
  list(id = "main", run = function() simEVE(p, 500, seed = 20260917)),
  list(id = "small", run = function() simEVE(p, 5, seed = 7)),
  list(id = "odd", run = function() simEVE(p, 37, seed = 123)),
  list(id = "missing", run = function() simEVE(pm, 20, seed = 5))
))
