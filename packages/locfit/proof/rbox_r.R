# R reference for locfit::rbox (locfit 1.5-9.12). Run from the repository root.
source("packages/locfit/proof/locfit_proof_common.R")

cases <- list(
  default = list(),
  kdtree = list(cut = 0.5, type = "kdtree", ll = c(0, 1, 2), ur = c(3, 4, 5)),
  phull = list(type = "phull", cut = 1.25, ll = c(-1, -2), ur = c(1, 2)),
  kdcenter = list(type = "kdcenter", cut = 0.3),
  bad_type = list(type = "foo")
)
write_fixture(list(cases = cases), "rbox")

run_case <- function(args) {
  tryCatch(to_plain(do.call(rbox, args)),
           error = function(e) list(error = TRUE, message = conditionMessage(e)))
}
out <- lapply(cases, run_case)
write_r_output(list(cases = out), "rbox")

timed_args <- cases$kdtree
ms <- time_r_ms(function() do.call(rbox, timed_args))
write_r_timing("rbox", ms)
cat("rbox R reference written; r_ms =", ms, "\n")
