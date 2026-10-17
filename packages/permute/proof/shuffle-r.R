.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressPackageStartupMessages(library(permute))
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
source(file.path(dir, 'shuffle-harness-r.R'))
out <- file.path(dir, '..', 'docs', 'output')
cases <- list(
  list(name = 'sh_free', seed = 41, f = function() shuffle(6, how(within = Within(type = 'free')))),
  list(name = 'sh_series', seed = 42, f = function() shuffle(6, how(within = Within(type = 'series')))),
  list(name = 'sh_series_mirror', seed = 43, f = function() shuffle(6, how(within = Within(type = 'series', mirror = TRUE)))),
  list(name = 'sh_grid', seed = 44, f = function() shuffle(8, how(within = Within(type = 'grid', nrow = 2, ncol = 4)))),
  list(name = 'sh_grid_mirror', seed = 45, f = function() shuffle(8, how(within = Within(type = 'grid', nrow = 2, ncol = 4, mirror = TRUE)))),
  list(name = 'sh_none', seed = 46, f = function() shuffle(6, how(within = Within(type = 'none')))),
  list(name = 'sh_vector_n', seed = 47, f = function() shuffle(c(5, 6, 7, 8, 9, 10), how(within = Within(type = 'free')))),
  list(name = 'sh_plots_free', seed = 48, f = function() shuffle(8, how(plots = Plots(strata = factor(rep(1:4, each = 2)), type = 'free'), within = Within(type = 'none')))),
  list(name = 'sh_plots_free_within', seed = 49, f = function() shuffle(8, how(plots = Plots(strata = factor(rep(1:2, each = 4)), type = 'free'), within = Within(type = 'free')))),
  list(name = 'sh_plots_series_within_const', seed = 50, f = function() shuffle(12, how(plots = Plots(strata = factor(rep(1:4, each = 3)), type = 'series', mirror = TRUE), within = Within(type = 'free', constant = TRUE)))),
  list(name = 'sh_plots_free_within_series_const', seed = 51, f = function() shuffle(12, how(plots = Plots(strata = factor(rep(1:3, each = 4)), type = 'free'), within = Within(type = 'series', constant = TRUE, mirror = TRUE)))),
  list(name = 'sh_plots_free_within_grid_const', seed = 52, f = function() shuffle(16, how(plots = Plots(strata = factor(rep(1:4, each = 4)), type = 'free'), within = Within(type = 'grid', nrow = 2, ncol = 2, constant = TRUE, mirror = TRUE)))),
  list(name = 'sh_plots_series_within_series', seed = 53, f = function() shuffle(12, how(plots = Plots(strata = factor(rep(1:3, each = 4)), type = 'series', mirror = TRUE), within = Within(type = 'series', mirror = TRUE)))),
  list(name = 'sh_blocks', seed = 54, f = function() shuffle(8, how(blocks = factor(rep(c(1, 2), each = 4)), within = Within(type = 'free')))),
  list(name = 'sh_blocks_interleaved', seed = 55, f = function() shuffle(8, how(blocks = factor(c(1, 2, 1, 2, 1, 2, 1, 2)), within = Within(type = 'series', mirror = TRUE)))),
  list(name = 'sh_blocks_plots', seed = 56, f = function() shuffle(12, how(blocks = factor(rep(c('x', 'y'), each = 6)), plots = Plots(strata = factor(rep(rep(1:3, each = 2), 2)), type = 'free'), within = Within(type = 'free')))),
  list(name = 'sh_blocks_zero_levels', seed = 57, f = function() shuffle(8, how(blocks = factor(rep(c(1, 2), each = 4)), plots = Plots(strata = factor(c(1, 1, 2, 2, 3, 3, 4, 4)), type = 'free'), within = Within(type = 'free'))))
)
run_proof('shuffle', cases, out)
