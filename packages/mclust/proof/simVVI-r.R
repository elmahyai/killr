# Proof: R mclust::simVVI (mclust 6.1.3), model VVI, against the Python port.
# Run from packages/mclust:  Rscript proof/simVVI-r.R
suppressMessages(library(mclust))
stopifnot(as.character(packageVersion("mclust")) == "6.1.3")
source("proof/sim_fixtures.R")
source("proof/sim_proof_common.R")
p <- sim_params("VVI")
pm <- sim_params_missing("VVI")
sim_proof("simVVI", list(
  list(id = "main", run = function() simVVI(p, 500, seed = 20260917)),
  list(id = "small", run = function() simVVI(p, 5, seed = 7)),
  list(id = "odd", run = function() simVVI(p, 37, seed = 123)),
  list(id = "missing", run = function() simVVI(pm, 20, seed = 5))
))
