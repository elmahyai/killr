pkg <- tempfile("labeling")
dir.create(pkg)
untar("cran/contrib/labeling_0.4.3.tar.gz", files="labeling/R/labeling.R",
      exdir=pkg)
source(file.path(pkg, "labeling/R/labeling.R"))
cases <- list(
  heckbert=list(8.1,14.1,4), wilkinson=list(8.1,14.1,4),
  extended=list(8.1,14.1,4), nelder=list(8.1,14.1,4),
  rpretty=list(8.1,14.1,6), matplotlib=list(8.1,14.1,4),
  gnuplot=list(8.1,14.1,4), sparks=list(8.1,14.1,4),
  thayer=list(8.1,14.1,4))
one <- list()
times <- list()
for (nm in names(cases)) {
  args <- cases[[nm]]
  one[[nm]] <- do.call(get(nm), args)
  z <- numeric(20)
  for (i in seq_len(20)) {
    t <- Sys.time(); do.call(get(nm), args); z[i] <- as.numeric(Sys.time()-t)
  }
  times[[nm]] <- median(z) * 1000
}
saveRDS(list(values=one, times=times), "packages/labeling/proof/r-results.rds")
json_num <- function(x) paste(c("[", paste(format(x, digits=17, scientific=FALSE), collapse=","), "]"), collapse="")
lines <- vapply(one, json_num, "")
json <- paste0("{", paste(sprintf('"%s":%s', names(lines), lines), collapse=","), "}")
writeLines(json, "packages/labeling/proof/r-results.json")
cat("R results written\n")
