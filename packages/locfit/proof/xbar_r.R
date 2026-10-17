# R reference for locfit::xbar (locfit 1.5-9.12). Run from the repository root.
source("packages/locfit/proof/locfit_proof_common.R")

write_fixture(list(cases = list(default = list())), "xbar")
out <- to_plain(xbar())
write_r_output(list(cases = list(default = out)), "xbar")

ms <- time_r_ms(function() xbar())
write_r_timing("xbar", ms)
cat("xbar R reference written; r_ms =", ms, "\n")
