# R reference for locfit::rv (locfit 1.5-9.12). Run from the repository root.
source("packages/locfit/proof/locfit_proof_common.R")

fits <- fixed_fits()
write_fixture(list(cases = lapply(fits, fit_fixture)), "rv")
out <- lapply(fits, function(f) as.numeric(rv(f)))
write_r_output(list(cases = out), "rv")

ms <- time_r_ms(function() rv(fits$tree))
write_r_timing("rv", ms)
cat("rv R reference written; r_ms =", ms, "\n")
