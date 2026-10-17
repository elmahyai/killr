library(locfit)
out <- "packages/locfit/proof"
dir.create(out, recursive=TRUE, showWarnings=FALSE)
set.seed(17)
x <- matrix(seq(0.05, 0.95, length.out=20), ncol=1)
y <- sin(2*pi*x[,1])
fns <- c("lfmarg","locfit","locfit.censor","locfit.matrix","locfit.quasi",
         "locfit.raw","locfit.robust","lp","lscv","lscv.exact")
flatten <- function(z) {
  if (is.numeric(z)) return(as.numeric(z))
  if (is.list(z)) return(unlist(lapply(z, flatten), use.names=FALSE))
  numeric()
}
for (nm in fns) {
  z <- tryCatch(do.call(nm, list(x=x, y=y)), error=function(e) e)
  if (inherits(z, "error")) {
    writeLines(paste("ERROR", conditionMessage(z)), file.path(out, paste0(nm, "_r.txt")))
    next
  }
  writeLines(sprintf("%.17g", flatten(z)), file.path(out, paste0(nm, "_r.txt")))
}
