.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressPackageStartupMessages(library(permute))
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
source(file.path(dir, 'shuffle-harness-r.R'))
out <- file.path(dir, '..', 'docs', 'output')
mat <- allPerms(4, how(within = Within(type = 'free')))
cases <- list(
  list(name = 'perm_free', seed = 81, f = function() permute(1, 6, how(within = Within(type = 'free')))),
  list(name = 'perm_series_mirror', seed = 82, f = function() permute(1, 10, how(within = Within(type = 'series', mirror = TRUE)))),
  list(name = 'perm_grid', seed = 83, f = function() permute(1, 8, how(within = Within(type = 'grid', nrow = 2, ncol = 4)))),
  list(name = 'perm_plots_free', seed = 84, f = function() permute(1, 8, how(plots = Plots(strata = factor(rep(1:4, each = 2)), type = 'free'), within = Within(type = 'none')))),
  list(name = 'perm_blocks_free', seed = 85, f = function() permute(1, 8, how(blocks = factor(rep(c(1, 2), each = 4)), within = Within(type = 'free')))),
  list(name = 'perm_plots_free_within_free', seed = 86, f = function() permute(1, 8, how(plots = Plots(strata = factor(rep(1:2, each = 4)), type = 'free'), within = Within(type = 'free')))),
  list(name = 'perm_complete_row2', seed = 87, f = function() permute(2, 4, how(complete = TRUE, all.perms = mat))),
  list(name = 'perm_within_none', seed = 88, f = function() permute(3, 5, how(within = Within(type = 'none'))))
)
run_proof('permute-rng', cases, out)
