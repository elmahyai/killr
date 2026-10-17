.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressPackageStartupMessages(library(permute))
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
source(file.path(dir, 'shuffle-harness-r.R'))
out <- file.path(dir, '..', 'docs', 'output')
cases <- list(
  list(name = 'st_free', seed = 31, f = function() shuffleStrata(factor(c('a', 'a', 'b', 'b', 'c', 'c')), 'free')),
  list(name = 'st_series', seed = 32, f = function() shuffleStrata(factor(rep(1:4, each = 2)), 'series')),
  list(name = 'st_series_mirror', seed = 33, f = function() shuffleStrata(factor(rep(1:4, each = 2)), 'series', mirror = TRUE)),
  list(name = 'st_series_start_flip', seed = 34, f = function() shuffleStrata(factor(rep(1:3, each = 2)), 'series', mirror = TRUE, start = 2, flip = TRUE)),
  list(name = 'st_grid', seed = 35, f = function() shuffleStrata(factor(rep(1:4, each = 2)), 'grid', nrow = 2, ncol = 2)),
  list(name = 'st_grid_mirror', seed = 36, f = function() shuffleStrata(factor(rep(c('p', 'q', 'r', 's'), each = 3)), 'grid', nrow = 2, ncol = 2, mirror = TRUE)),
  list(name = 'st_free_unused', seed = 37, f = function() shuffleStrata(factor(rep(c(1, 3, 5), each = 2), levels = 1:6), 'free')),
  list(name = 'st_free_numeric', seed = 38, f = function() shuffleStrata(factor(c(10, 10, 2, 2, 33, 33)), 'free'))
)
run_proof('shuffleStrata', cases, out)
