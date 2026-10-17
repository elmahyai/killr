# R reference for locfit::lfeval (locfit 1.5-9.12). Run from the repository root.
source("packages/locfit/proof/locfit_proof_common.R")

fits <- fixed_fits()
write_fixture(list(cases = lapply(fits, fit_fixture)), "lfeval")
out <- lapply(fits, function(f) to_plain(lfeval(f)))
write_r_output(list(cases = out), "lfeval")

ms <- time_r_ms(function() lfeval(fits$tree))
write_r_timing("lfeval", ms)
cat("lfeval R reference written; r_ms =", ms, "\n")
