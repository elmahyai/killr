# Proof: R mclust::simVII (mclust 6.1.3), model VII, against the Python port.
# Run from packages/mclust:  Rscript proof/simVII-r.R
suppressMessages(library(mclust))
stopifnot(as.character(packageVersion("mclust")) == "6.1.3")
source("proof/sim_fixtures.R")
source("proof/sim_proof_common.R")
p <- sim_params("VII")
pm <- sim_params_missing("VII")
sim_proof("simVII", list(
  list(id = "main", run = function() simVII(p, 500, seed = 20260917)),
  list(id = "small", run = function() simVII(p, 5, seed = 7)),
  list(id = "odd", run = function() simVII(p, 37, seed = 123)),
  list(id = "missing", run = function() simVII(pm, 20, seed = 5))
))
