# Proof: R simulate.Mclust (mclust 6.1.3) for all 16 models, against the Python port.
# Run from packages/mclust:  Rscript proof/simulate.Mclust-r.R
# The timed unit is one sweep: the 18 cases below, each one simulate.Mclust call.
suppressMessages(library(mclust))
stopifnot(as.character(packageVersion("mclust")) == "6.1.3")
source("proof/sim_fixtures.R")      # group B parameters (VEV, VII, VVI, VVV, EVV, VEE, EVE, VVE)
source("proof/sim-core-fixtures.R") # group A parameters (E, V, EII, EEI, VEI, EVI, EEE, EEV)
source("proof/sim_proof_common.R")

group_a <- c("E", "V", "EII", "EEI", "VEI", "EVI", "EEE", "EEV")
pars_for <- function(model) {
  if (model %in% group_a) get(paste0("pars_", model)) else sim_params(model)
}
mk <- function(model) structure(list(modelName = model, parameters = pars_for(model)), class = "Mclust")

models16 <- c("E", "V", "EII", "VII", "EEI", "VEI", "EVI", "VVI",
              "EEE", "VEE", "EVE", "VVE", "EEV", "VEV", "EVV", "VVV")
model_cases <- lapply(models16, function(m) {
  force(m)
  list(id = m, run = function() simulate(mk(m), nsim = 37, seed = 123))
})

cases <- c(
  list(list(id = "VEV-main", run = function() simulate(mk("VEV"), nsim = 500, seed = 20260917)),
       list(id = "VEV-small", run = function() simulate(mk("VEV"), nsim = 5, seed = 7))),
  model_cases
)

sweep <- function() for (cs in cases) cs$run()

sim_proof("simulate.Mclust", cases, timed = sweep)
