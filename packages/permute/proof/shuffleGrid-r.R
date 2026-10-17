.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
suppressPackageStartupMessages(library(permute))
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
source(file.path(dir, 'shuffle-harness-r.R'))
out <- file.path(dir, '..', 'docs', 'output')
cases <- list(
  list(name = 'sg_plain', seed = 21, f = function() shuffleGrid(3, 4)),
  list(name = 'sg_mirror', seed = 22, f = function() shuffleGrid(3, 4, mirror = TRUE)),
  list(name = 'sg_mirror_2x2', seed = 23, f = function() shuffleGrid(2, 2, mirror = TRUE)),
  list(name = 'sg_start', seed = 24, f = function() shuffleGrid(4, 3, start.row = 2, start.col = 1)),
  list(name = 'sg_flip', seed = 25, f = function() shuffleGrid(3, 3, mirror = TRUE, flip = c(TRUE, FALSE))),
  list(name = 'sg_flip_none', seed = 26, f = function() shuffleGrid(3, 3, mirror = TRUE, flip = c(FALSE, FALSE))),
  list(name = 'sg_flip_2x5', seed = 27, f = function() shuffleGrid(2, 5, mirror = TRUE, flip = c(FALSE, TRUE))),
  list(name = 'sg_mirror_start', seed = 28, f = function() shuffleGrid(3, 5, mirror = TRUE, start.row = 3, start.col = 4))
)
run_proof('shuffleGrid', cases, out)
