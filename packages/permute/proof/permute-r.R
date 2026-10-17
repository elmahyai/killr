.libPaths(c(Sys.getenv("R_LIBS_USER"), .libPaths()))
library(permute)
dir <- dirname(sub('^--file=', '', commandArgs()[grep('^--file=', commandArgs())]))
out <- file.path(dir, '..', 'docs', 'output')
values <- file.path(out, 'r_values')
dir.create(values, recursive=TRUE, showWarnings=FALSE)
make_control <- function() how(within=Within(type='free'), nperm=5, observed=TRUE)
mat <- allPerms(4, make_control())
write.table(unclass(mat), file=file.path(out, 'permutation_matrix.csv'),
            sep=',', row.names=FALSE, col.names=FALSE)
write_value <- function(name, x) {
  p <- file.path(values, paste0(gsub('[.]', '_', name), '.txt'))
  if (name %in% c('allPerms', 'as.allPerms')) {
    write.table(unclass(x), p, sep=',', row.names=FALSE, col.names=FALSE)
  } else if (name == 'Blocks') {
    writeLines('strata=NULL', p)
  } else if (name == 'check') {
    writeLines(c(paste0('n=', x$n), paste0('within.type=', x$control$within$type),
                 paste0('within.constant=', x$control$within$constant),
                 paste0('within.mirror=', x$control$within$mirror),
                 paste0('plots.type=', x$control$plots$type),
                 paste0('plots.mirror=', x$control$plots$mirror)), p)
  } else if (name == 'getWithin') {
    writeLines(c(paste0('type=', x$type), paste0('constant=', x$constant),
                 paste0('mirror=', x$mirror)), p)
  } else if (name == 'getPlots') {
    writeLines(c(paste0('type=', x$type), paste0('mirror=', x$mirror),
                 paste0('strata=', if (is.null(x$strata)) 'NULL' else paste(x$strata, collapse=','))), p)
  } else {
    writeLines(if (length(x) == 0 || is.null(x)) 'NULL' else as.character(x), p)
  }
}
inputs <- list(
  allPerms=function() allPerms(4, make_control()),
  as.allPerms=function() as.allPerms(mat, make_control()),
  Blocks=function() Blocks(), check=function() check(4, make_control()),
  getBlocks=function() getBlocks(make_control()), getWithin=function() getWithin(make_control()),
  getStrata=function() getStrata(make_control()), getType=function() getType(make_control()),
  getMirror=function() getMirror(make_control()), getConstant=function() getConstant(make_control()),
  getPlots=function() getPlots(make_control())
)
res <- lapply(names(inputs), function(nm) {
  f <- inputs[[nm]]
  write_value(nm, f())
  z <- numeric(20)
  for (i in seq_len(20)) {
    t <- Sys.time(); f()
    z[i] <- as.numeric(difftime(Sys.time(), t, units='secs')) * 1000
  }
  data.frame(name=nm, r_ms=median(z))
})
write.table(do.call(rbind, res), file=file.path(out, 'r_results.csv'),
            sep=',', row.names=FALSE, quote=FALSE)
