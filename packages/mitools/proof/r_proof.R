## Load the pure-R implementation directly so the proof does not require the
## package's optional DBI runtime dependency.
src <- tempfile("mitools-")
dir.create(src)
untar("cran/contrib/mitools_2.7.tar.gz", exdir=src)
source(file.path(src, "mitools", "R", "MI.R"))
source(file.path(src, "mitools", "R", "PV.R"))

cases <- function() {
  datasets <- list(matrix(c(1, 3, 2, 4), 2, 2), matrix(c(2, 4, 3, 5), 2, 2))
  il <- imputationList(datasets)
  combined <- MIcombine(
    list(c(1, 2), c(1.2, 2.4), c(.8, 1.6)),
    list(diag(c(.25, .36)), diag(c(.25, .36)), diag(c(.25, .36)))
  )
  extracted <- MIextract(list(list(x=1), list(x=2), list(x=3)), expr=x)
  d <- data.frame(PV1=c(1, 2), PV2=c(2, 3), z=c(10, 20))
  pv <- withPV(list(x ~ PV1 + PV2), d, function(d) mean(d$x))
  list(imputationList=length(il$imputations),
       MIcombine=c(combined$coefficients, as.vector(combined$variance)),
       MIextract=unlist(extracted), withPV=unlist(pv))
}

values <- cases()
for (name in names(values)) {
  times <- numeric(20)
  for (i in seq_len(20)) {
    start <- Sys.time()
    current <- cases()[[name]]
    times[i] <- as.numeric(difftime(Sys.time(), start, units="secs")) * 1000
  }
  cat(sprintf("%s|%s|%.9f\n", name,
              paste(format(values[[name]], digits=12, scientific=FALSE), collapse=" "),
              median(times)))
}
