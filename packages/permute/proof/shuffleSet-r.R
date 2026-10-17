.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressPackageStartupMessages(library(permute))
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
source(file.path(dir, 'shuffle-harness-r.R'))
out <- file.path(dir, '..', 'docs', 'output')
cases <- list(
  list(name = 'sset_free_nocheck', seed = 61, f = function() shuffleSet(6, 4, how(within = Within(type = 'free')), check = FALSE)),
  list(name = 'sset_free_check_complete', seed = 62, f = function() shuffleSet(6, 4, how(within = Within(type = 'free')), quietly = TRUE)),
  list(name = 'sset_free_check_small', seed = 60, f = function() shuffleSet(5, 2, how(within = Within(type = 'free')), quietly = TRUE)),
  list(name = 'sset_series_mirror', seed = 63, f = function() shuffleSet(10, 3, how(within = Within(type = 'series', mirror = TRUE)), check = FALSE)),
  list(name = 'sset_grid', seed = 64, f = function() shuffleSet(8, 3, how(within = Within(type = 'grid', nrow = 2, ncol = 4)), check = FALSE)),
  list(name = 'sset_plots_free', seed = 65, f = function() shuffleSet(8, 3, how(plots = Plots(strata = factor(rep(1:4, each = 2)), type = 'free'), within = Within(type = 'none')), check = FALSE)),
  list(name = 'sset_plots_free_within_free', seed = 66, f = function() shuffleSet(8, 3, how(plots = Plots(strata = factor(rep(1:2, each = 4)), type = 'free'), within = Within(type = 'free')), check = FALSE)),
  list(name = 'sset_const_series', seed = 67, f = function() shuffleSet(12, 3, how(plots = Plots(strata = factor(rep(1:3, each = 4)), type = 'free'), within = Within(type = 'series', constant = TRUE, mirror = TRUE)), check = FALSE)),
  list(name = 'sset_const_grid_plots_series', seed = 68, f = function() shuffleSet(16, 2, how(plots = Plots(strata = factor(rep(1:4, each = 4)), type = 'series', mirror = TRUE), within = Within(type = 'grid', nrow = 2, ncol = 2, constant = TRUE, mirror = TRUE)), check = FALSE)),
  list(name = 'sset_const_free', seed = 69, f = function() shuffleSet(12, 3, how(plots = Plots(strata = factor(rep(1:3, each = 4)), type = 'free'), within = Within(type = 'free', constant = TRUE)), check = FALSE)),
  list(name = 'sset_blocks', seed = 70, f = function() shuffleSet(8, 3, how(blocks = factor(rep(c(1, 2), each = 4)), within = Within(type = 'free')), check = FALSE)),
  list(name = 'sset_nperm_missing', seed = 71, f = function() shuffleSet(8, control = how(within = Within(type = 'series'), nperm = 3), check = FALSE)),
  list(name = 'sset_within_none', seed = 72, f = function() shuffleSet(5, 2, how(within = Within(type = 'none')), check = FALSE)),
  list(name = 'sset_check_series', seed = 73, f = function() shuffleSet(4, 3, how(within = Within(type = 'series', mirror = TRUE)), quietly = TRUE))
)
run_proof('shuffleSet', cases, out)
