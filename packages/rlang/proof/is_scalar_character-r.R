.libPaths(c(path.expand("~/R/library"), .libPaths()))
library(rlang)
cat(paste(as.character(c(is_scalar_character('a'), is_scalar_character(c('a','b')))), collapse=','))
