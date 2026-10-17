# R reference for locfit::lfknots (locfit 1.5-9.12). Run from the repository root.
source("packages/locfit/proof/locfit_proof_common.R")

fits <- fixed_fits()
tree_s <- fits$tree
tree_s$cell$s[c(2, 5)] <- 1L          # exercises the delete.pv row removal
tree_na <- fits$tree
tree_na$eva$coef[2, 1] <- 0.1278433   # locfit's missing-value marker
fit_set <- list(tree = fits$tree, tree_s = tree_s, tree_na = tree_na,
                dat = fits$dat, grid = fits$grid)

cases <- list(
  tree_default = list(fit = "tree", what = c("x", "coef", "h", "nlx"), delete_pv = TRUE, tr = "identity"),
  tree_all = list(fit = "tree", what = c("x", "coef", "f1", "nlx", "nlx1", "se", "infl",
                                         "infla", "lik", "h", "deg"), delete_pv = TRUE, tr = "identity"),
  tree_exp = list(fit = "tree", what = c("coef", "h"), delete_pv = TRUE, tr = "exp"),
  tree_s_delete = list(fit = "tree_s", what = c("x", "coef", "h", "nlx"), delete_pv = TRUE, tr = "identity"),
  tree_s_keep = list(fit = "tree_s", what = c("x", "coef", "h", "nlx"), delete_pv = FALSE, tr = "identity"),
  tree_na = list(fit = "tree_na", what = c("coef", "h"), delete_pv = TRUE, tr = "identity"),
  dat = list(fit = "dat", what = c("x", "coef", "nlx"), delete_pv = TRUE, tr = "identity"),
  grid = list(fit = "grid", what = c("x", "coef", "h"), delete_pv = TRUE, tr = "identity")
)

fixture_cases <- lapply(cases, function(cs) {
  list(fit = fit_fixture(fit_set[[cs$fit]]), what = cs$what,
       delete_pv = cs$delete_pv, tr = cs$tr)
})
write_fixture(list(cases = fixture_cases), "lfknots")

run_case <- function(cs) {
  f <- fit_set[[cs$fit]]
  if (cs$tr == "exp") {
    lfknots(f, tr = exp, what = cs$what, delete.pv = cs$delete_pv)
  } else {
    lfknots(f, what = cs$what, delete.pv = cs$delete_pv)
  }
}
out <- lapply(cases, run_case)
write_r_output(list(cases = out), "lfknots")

primary <- fits$tree
ms <- time_r_ms(function() lfknots(primary, what = c("x", "coef", "h", "nlx")))
write_r_timing("lfknots", ms)
cat("lfknots R reference written; r_ms =", ms, "\n")
