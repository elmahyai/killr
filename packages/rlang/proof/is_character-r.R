.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(is_character('a'), is_character(c('a','b')), is_character(1))), collapse=','))
