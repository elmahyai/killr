# Proof: R mclust::simEVV (mclust 6.1.3), model EVV, against the Python port.
# Run from packages/mclust:  Rscript proof/simEVV-r.R
suppressMessages(library(mclust))
stopifnot(as.character(packageVersion("mclust")) == "6.1.3")
source("proof/sim_fixtures.R")
source("proof/sim_proof_common.R")
p <- sim_params("EVV")
pm <- sim_params_missing("EVV")
sim_proof("simEVV", list(
  list(id = "main", run = function() simEVV(p, 500, seed = 20260917)),
  list(id = "small", run = function() simEVV(p, 5, seed = 7)),
  list(id = "odd", run = function() simEVV(p, 37, seed = 123)),
  list(id = "missing", run = function() simEVV(pm, 20, seed = 5))
))
